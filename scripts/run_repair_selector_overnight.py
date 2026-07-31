#!/usr/bin/env python
"""
Overnight repair-directed active mining for repair-specific selector training.

Mines queries where matched repaired/unrepaired ranking methods show material
NDCG@10 gains, with leakage-safe splits, multi-provider LLM judgments, and
continuous checkpointing.
"""
# ruff: noqa: E402, E501, I001

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_CAAR = Path(os.environ.get("CAAR_REPO", _REPO.parent / f"{_REPO.name}-caar")).expanduser()
# Main repo must precede CAAR so failure_mining and core modules resolve correctly.
for _path in (_CAAR, _CAAR / "src", _REPO, _REPO / "src"):
    _s = str(_path)
    if _s not in sys.path:
        sys.path.append(_s)
# Ensure main-repo src wins over CAAR's overlapping consistency_ranker package.
sys.path.insert(0, str(_REPO / "src"))

from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.failure_mining.data_setup import (
    VOTE_REGIMES,
    ensure_dataset_prepared,
    ensure_score_files,
    ensure_vote_file,
    load_documents_map,
    supported_datasets,
    write_query_ids,
)
from consistency_ranker.failure_mining.llm_runner import (
    LLMRunner,
    PERSISTENT_FAILURE_CATEGORIES,
    PROMPT_VERSION,
    detect_llm_providers,
    health_check_provider,
)
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.repair_selector_mining.candidate_selection import (
    diversify_batch,
    pre_outcome_features,
    rank_candidates,
)
from consistency_ranker.repair_selector_mining.checkpoint import CheckpointManager
from consistency_ranker.repair_selector_mining.processor import process_repair_query
from consistency_ranker.repair_selector_mining.reports import write_all_reports
from consistency_ranker.repair_selector_mining.selector_training import train_repair_selectors
from consistency_ranker.repair_selector_mining.splits import assign_splits, split_rows
from scripts.run_real_experiment import _load_pairwise_preference_file, _load_score_prior_files, _rrf_prior_scores_for_query, _score_sum_prior_scores

log = logging.getLogger(__name__)

_SHUTDOWN = False
_WALL_DEADLINE: float | None = None
_COLLECTION_DEADLINE: float | None = None

# Mid-run circuit breaker: after this many consecutive persistent-category
# failures (see PERSISTENT_FAILURE_CATEGORIES), a provider is dropped from
# active_providers for the remainder of the run instead of being retried
# forever. Kept low: a health-checked-good provider going bad mid-run (e.g.
# CloudRift's backend disappearing) should be caught within a batch or two,
# not after burning the whole budget.
CIRCUIT_BREAKER_THRESHOLD = 3


def _handle_sigterm(signum, frame) -> None:
    global _SHUTDOWN
    log.warning("Received signal %s — stopping new work and flushing checkpoints", signum)
    _SHUTDOWN = True


def _git_info(repo: Path) -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
        return {"commit": commit, "dirty": bool(dirty), "dirty_files": len(dirty.splitlines()) if dirty else 0}
    except Exception as exc:
        return {"error": str(exc)}


def _restrict_prefs(prefs: list[Preference], top_k: int) -> list[Preference]:
    from consistency_ranker.baseline_ranking import score_sum_scores
    from consistency_ranker.graph_construction import build_graph

    nodes: set[str] = set()
    for p in prefs:
        nodes.add(p.winner)
        nodes.add(p.loser)
    if len(nodes) <= top_k:
        return prefs
    g = build_graph(prefs)
    scores = score_sum_scores(g)
    keep = set(sorted(scores, key=lambda n: (-scores[n], n))[:top_k])
    return [p for p in prefs if p.winner in keep and p.loser in keep]


def _interleave_by_split(*groups: list[dict]) -> list[dict]:
    """Merge candidate groups (e.g. train+val, test) by fractional progress
    through each group, so every split's proportional share of processing
    happens throughout the run instead of front-loading larger splits and
    starving smaller ones under a time budget. Preserves each group's
    internal (priority-ranked) order.
    """
    tagged: list[tuple[float, dict]] = []
    for g in groups:
        n = len(g)
        if n == 0:
            continue
        for i, item in enumerate(g):
            tagged.append(((i + 1) / n, item))
    tagged.sort(key=lambda t: t[0])
    return [item for _, item in tagged]


def _record_key(dataset: str, regime: str, query_id: str) -> str:
    return f"{dataset}|{regime}|{query_id}"


def _load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _build_candidate_pool(
    datasets: list[str],
    regimes: tuple[str, ...],
    *,
    max_queries_per_dataset: int,
    work_root: Path,
    seed: int,
) -> list[dict]:
    candidates: list[dict] = []
    for dataset in datasets:
        ensure_dataset_prepared(dataset, max_queries=max_queries_per_dataset)
        queries, _, qrels = load_dataset_splits(dataset)
        qrels_by_q: dict[str, list] = defaultdict(list)
        for e in qrels:
            qrels_by_q[e.query_id].append(e)
        ds_work = work_root / dataset
        qfile = ds_work / "pool_query_ids.txt"
        query_ids = write_query_ids(dataset, qfile, max_queries_per_dataset * 3)
        score_files = ensure_score_files(dataset, ds_work, query_ids=query_ids, top_n=40)
        score_prior_sets = _load_score_prior_files(score_files)
        query_text_map = {q.query_id: q.text for q in queries}

        for regime in regimes:
            vote_path = ensure_vote_file(
                dataset, ds_work, regime, score_files, top_k=20, query_id_file=qfile
            )
            pairwise_index = _load_pairwise_preference_file(vote_path)
            for qid in query_ids:
                prefs = _restrict_prefs(pairwise_index.get(qid, []), 20)
                if not prefs:
                    continue
                from consistency_ranker.graph_construction import build_graph

                graph = build_graph(prefs)
                prior_scores = _rrf_prior_scores_for_query(
                    query_id=qid,
                    candidate_nodes=set(graph.nodes()),
                    score_prior_sets=score_prior_sets,
                    fallback_scores=_score_sum_prior_scores(graph),
                )
                ranker_maps = []
                for smap in score_prior_sets:
                    ranker_maps.append(dict(smap.get(qid, [])))
                feats = pre_outcome_features(
                    prefs, prior_scores=prior_scores, ranker_score_maps=ranker_maps
                )
                candidates.append(
                    {
                        "dataset": dataset,
                        "query_id": qid,
                        "vote_regime": regime,
                        "query_text": query_text_map.get(qid),
                        "pre_features": feats,
                    }
                )
    return candidates


def _selector_dataset_row(record: dict, features: dict) -> dict:
    primary_gain = None
    for pr in record.get("repair_pair_results", []):
        if pr.get("repaired_method") == "markov_graph_repaired":
            primary_gain = pr.get("repair_gain")
            break
    return {
        "dataset": record["query_metadata"]["dataset"],
        "query_id": record["query_metadata"]["query_id"],
        "vote_regime": record["query_metadata"]["vote_regime"],
        "split": record.get("split_assignment"),
        "repair_gain_primary": primary_gain,
        "features": features,
        "metric_aware_ndcg": record.get("metric_aware_repair", {}).get("ndcg_at_k"),
    }


def run_overnight(args: argparse.Namespace) -> dict:
    global _WALL_DEADLINE, _COLLECTION_DEADLINE
    _start_mono = time.time()
    _WALL_DEADLINE = _start_mono + args.wall_seconds
    # New-query collection stops earlier than the overall wall deadline so the
    # final locked-test selector evaluation and report writing (which run
    # after the mining loop breaks) have guaranteed time left instead of
    # racing the same deadline the collection loop just exhausted.
    collection_stop_seconds = args.collection_stop_seconds or args.wall_seconds
    _COLLECTION_DEADLINE = _start_mono + collection_stop_seconds

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else (
        _CAAR / "reports" / f"repair_selector_overnight_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "run.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(file_handler)

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    ckpt = CheckpointManager(output_dir)
    work_root = output_dir / "_work"
    work_root.mkdir(parents=True, exist_ok=True)

    regimes = tuple(args.vote_regimes) if args.vote_regimes else VOTE_REGIMES
    provider_list = [p.strip() for p in args.providers.split(",") if p.strip() and p.strip() != "none"]
    provider_statuses = [
        {"provider": s.provider, "available": s.available, "reason": s.reason, "mode": s.mode}
        for s in detect_llm_providers(provider_list or ["none"])
    ]
    active_providers = [s["provider"] for s in provider_statuses if s["available"]]

    health_check_results = []
    for prov in list(active_providers):
        result = health_check_provider(prov)
        health_check_results.append(result)
        if not result["ok"] and result["category"] in PERSISTENT_FAILURE_CATEGORIES:
            log.warning(
                "Startup health check failed for provider=%s model=%s category=%s — "
                "disabling for this run: %s",
                prov, result.get("model"), result["category"], result["message"],
            )
            active_providers.remove(prov)
        else:
            log.info(
                "Startup health check ok=%s for provider=%s model=%s",
                result["ok"], prov, result.get("model"),
            )

    try:
        from consistency_ranker.mwfas_solver import available_methods

        ilp_available = "ilp" in available_methods()
    except Exception:
        ilp_available = False

    import importlib.util

    caar_features_path = _CAAR / "src" / "consistency_ranker" / "adaptive_reranking" / "features.py"
    spec = importlib.util.spec_from_file_location("caar_features", caar_features_path)
    caar_features = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(caar_features)
    LEGAL_FEATURES = caar_features.LEGAL_FEATURES
    extract_features = caar_features.extract_features

    run_meta = {
        "_start_mono": _start_mono,
        "start_timestamp": datetime.now(timezone.utc).isoformat(),
        "main_repo": _git_info(_REPO),
        "caar_repo": _git_info(_CAAR),
        "command": " ".join(sys.argv),
        "seed": args.seed,
        "datasets": args.datasets,
        "vote_regimes": list(regimes),
        "providers_requested": provider_list,
        "providers_active": active_providers,
        "provider_statuses": provider_statuses,
        "provider_health_checks": health_check_results,
        "circuit_breaker_trips": [],
        "prompt_version": PROMPT_VERSION,
        "feature_names": list(LEGAL_FEATURES),
        "wall_seconds": args.wall_seconds,
        "collection_stop_seconds": args.collection_stop_seconds,
        "reused_from": args.reused_from,
        "max_candidates": args.max_candidates,
        "split_policy": "dataset_stratified_60_20_20_with_fingerprint_dedup",
        "ilp_available": ilp_available,
        "output_dir": str(output_dir),
        "status": "running",
    }
    ckpt.write_json("run_manifest.json", run_meta)

    log.info("Building candidate pool from %s", args.datasets)
    candidates = _build_candidate_pool(
        args.datasets,
        regimes,
        max_queries_per_dataset=args.max_queries_per_dataset,
        work_root=work_root,
        seed=args.seed,
    )
    split_map = assign_splits(candidates, seed=args.seed)
    for cand in candidates:
        key = (cand["dataset"], cand["query_id"])
        cand["split_assignment"] = split_map.get(key, "train")
        ckpt.csv_writers["query_candidates"].write(
            {
                "dataset": cand["dataset"],
                "query_id": cand["query_id"],
                "vote_regime": cand["vote_regime"],
                "mining_priority": 0.0,
                "split_assignment": cand["split_assignment"],
                "is_cyclic": cand.get("pre_features", {}).get("is_cyclic"),
                "largest_scc_frac": cand.get("pre_features", {}).get("largest_scc_frac"),
                "ranker_disagreement": cand.get("pre_features", {}).get("ranker_disagreement"),
            }
        )
        import hashlib

        fp = hashlib.sha256((cand.get("query_text") or "").strip().lower().encode()).hexdigest()[:16]
        ckpt.csv_writers["split_assignments"].write(
            {"dataset": cand["dataset"], "query_id": cand["query_id"], "split": cand["split_assignment"], "text_fingerprint": fp}
        )

    ranked = rank_candidates(candidates)
    # Test is split off before mining priority ranking (leakage-safe: split
    # assignment doesn't look at outcomes), then interleaved back in
    # proportionally rather than appended after all train/val -- appending it
    # meant a time-limited run that didn't reach the end of the list left the
    # locked-test split completely empty, which crashed the final evaluation
    # (see selector_training._safe_classification_metrics' docstring) and,
    # even once that no longer crashes, silently produces a locked-test
    # report with zero examples instead of a partial one.
    train_val_ranked = [c for c in ranked if c["split_assignment"] in ("train", "validation")]
    test_ranked = [c for c in ranked if c["split_assignment"] == "test"]
    processing_order = _interleave_by_split(train_val_ranked, test_ranked)

    llm_runner = None
    if active_providers:
        max_calls = args.max_llm_calls or (
            len(processing_order) * len(active_providers) * len(regimes)
        )
        llm_runner = LLMRunner(
            output_path=output_dir / "llm_call_records.jsonl",
            cache_dir=output_dir / "llm_cache",
            max_calls=max_calls,
            use_cache=args.use_cache,
        )

    records = _load_records(output_dir / "query_level_full_records.jsonl")
    n_new = 0
    n_processed = len(records)
    selector_results = None
    last_selector_train = 0
    batch_size = args.batch_size
    consecutive_failures: dict[str, int] = defaultdict(int)

    for batch_start in range(0, len(processing_order), batch_size):
        if _SHUTDOWN or time.time() >= _COLLECTION_DEADLINE:
            log.warning("Collection deadline or shutdown — stopping mining loop")
            break

        batch = diversify_batch(processing_order[batch_start : batch_start + batch_size], batch_size)
        for cand in batch:
            if _SHUTDOWN or time.time() >= _COLLECTION_DEADLINE:
                break
            dataset = cand["dataset"]
            regime = cand["vote_regime"]
            qid = cand["query_id"]
            key = _record_key(dataset, regime, qid)
            if ckpt.is_completed(key):
                continue

            ds_work = work_root / dataset
            qfile = ds_work / "pool_query_ids.txt"
            score_files = ensure_score_files(dataset, ds_work, query_ids=[qid], top_n=40)
            score_prior_sets = _load_score_prior_files(score_files)
            vote_path = ensure_vote_file(dataset, ds_work, regime, score_files, top_k=args.max_candidates, query_id_file=qfile)
            pairwise_index = _load_pairwise_preference_file(vote_path)
            prefs = _restrict_prefs(pairwise_index.get(qid, []), args.max_candidates)
            if not prefs:
                continue

            queries, _, qrels = load_dataset_splits(dataset)
            qrels_by_q: dict[str, list] = defaultdict(list)
            for e in qrels:
                qrels_by_q[e.query_id].append(e)
            doc_map = load_documents_map(dataset)
            query_text_map = {q.query_id: q.text for q in queries}
            snippets = {
                d: doc_map[d]
                for d in {p.winner for p in prefs} | {p.loser for p in prefs}
                if d in doc_map
            }

            record = process_repair_query(
                dataset=dataset,
                vote_regime=regime,
                query_id=qid,
                query_text=query_text_map.get(qid),
                split=cand["split_assignment"],
                qrels_for_query=qrels_by_q.get(qid, []),
                prefs=prefs,
                score_prior_sets=score_prior_sets,
                top_k=args.max_candidates,
                doc_snippets=snippets,
            )
            if record is None:
                continue

            # Multi-provider LLM judgments
            if llm_runner and active_providers:
                cand_ids = record["query_metadata"]["candidate_doc_ids"][: args.max_candidates]
                doc_texts = {
                    d: f"{snippets.get(d, {}).get('title', '')}\n{snippets.get(d, {}).get('text_snippet', '')}"
                    for d in cand_ids
                }
                for prov in list(active_providers):
                    if _SHUTDOWN:
                        break
                    llm_out = llm_runner.run_pairwise_rerank(
                        provider=prov,
                        query_id=qid,
                        query_text=query_text_map.get(qid, ""),
                        doc_texts=doc_texts,
                        candidate_ids=cand_ids,
                    )
                    ts = time.time()
                    if llm_out:
                        consecutive_failures[prov] = 0
                        method_name = f"llm_{prov}_pairwise"
                        from scripts.run_real_experiment import _ndcg_at_k, _reference_ranking_for_candidates

                        ref_ranking, rel_map = _reference_ranking_for_candidates(
                            qrels_for_query=qrels_by_q.get(qid, []),
                            candidates=cand_ids,
                        )
                        aligned = [d for d in llm_out["ranking"] if d in set(ref_ranking)]
                        ndcg = _ndcg_at_k(aligned, rel_map, k=args.max_candidates)
                        record["method_outputs"][method_name] = {
                            "ranking": llm_out["ranking"],
                            "scores": llm_out["scores"],
                            "ndcg_at_k": ndcg,
                            "llm_record_ref": llm_out.get("llm_record"),
                        }
                        llm_rec = llm_out.get("llm_record", {})
                        ckpt.writers["pairwise_judgments"].write(llm_rec)
                        ckpt.csv_writers["provider_usage"].write(
                            {
                                "timestamp": ts,
                                "provider": prov,
                                "model": llm_rec.get("model", ""),
                                "query_id": qid,
                                "dataset": dataset,
                                "status": "ok",
                                "from_cache": llm_rec.get("from_cache", False),
                                "latency_s": llm_rec.get("latency_s"),
                            }
                        )
                    else:
                        # Report the real classified failure cause (auth,
                        # model-not-found, model-unavailable/503, rate-limit,
                        # budget, timeout, ...) instead of a single generic
                        # "unavailable_or_budget" label that conflates all of
                        # them -- see llm_runner.classify_llm_error().
                        last_err = llm_runner.last_error or {}
                        error_category = last_err.get("category", "unknown_error")
                        ckpt.csv_writers["api_failures"].write(
                            {
                                "timestamp": ts,
                                "provider": prov,
                                "model": last_err.get("model") or "",
                                "query_id": qid,
                                "dataset": dataset,
                                "error": error_category,
                                "error_message": last_err.get("message", ""),
                                "http_status": last_err.get("http_status"),
                                "retry_count": 0,
                            }
                        )
                        if error_category in PERSISTENT_FAILURE_CATEGORIES:
                            consecutive_failures[prov] += 1
                            if consecutive_failures[prov] >= CIRCUIT_BREAKER_THRESHOLD and prov in active_providers:
                                log.warning(
                                    "Circuit breaker tripped for provider=%s after %d consecutive "
                                    "%s failures — disabling for the rest of this run",
                                    prov, consecutive_failures[prov], error_category,
                                )
                                active_providers.remove(prov)
                                run_meta["circuit_breaker_trips"].append(
                                    {
                                        "provider": prov,
                                        "category": error_category,
                                        "consecutive_failures": consecutive_failures[prov],
                                        "query_id": qid,
                                        "timestamp": ts,
                                    }
                                )
                        else:
                            consecutive_failures[prov] = 0

            features = extract_features(record)
            ckpt.writers["full_records"].write(record)
            ckpt.writers["repair_selector_dataset"].write(_selector_dataset_row(record, features))
            for method, out in record.get("method_outputs", {}).items():
                ckpt.csv_writers["per_query_method_results"].write(
                    {
                        "dataset": dataset,
                        "query_id": qid,
                        "vote_regime": regime,
                        "method": method,
                        "ndcg_at_k": out.get("ndcg_at_k"),
                        "split": cand["split_assignment"],
                    }
                )
            for pr in record.get("repair_pair_results", []):
                ckpt.csv_writers["repair_pair_results"].write(pr)
                if pr.get("repair_gain") is not None and float(pr["repair_gain"]) >= 0.0025:
                    ckpt.csv_writers["positive_case_inventory"].write(
                        {
                            "dataset": dataset,
                            "query_id": qid,
                            "vote_regime": regime,
                            "threshold": 0.0025,
                            "repair_gain": pr["repair_gain"],
                            "repaired_method": pr["repaired_method"],
                            "primary_provider": active_providers[0] if active_providers else "non_llm",
                            "split": cand["split_assignment"],
                        }
                    )

            ckpt.mark_completed(key)
            records.append(record)
            n_new += 1
            n_processed += 1

            progress = {
                "n_processed": n_processed,
                "n_new_this_run": n_new,
                "elapsed_s": time.time() - (run_meta.get("_start_mono") or time.time()),
                "shutdown": _SHUTDOWN,
            }
            ckpt.write_json("progress.json", progress)
            ckpt.save_checkpoint({"n_processed": n_processed, "n_new": n_new})

        # Periodic selector training on train/val only
        if n_processed - last_selector_train >= args.selector_train_every and len(records) >= 10:
            train, val, test = split_rows(records)
            if len(train) + len(val) >= 8:
                log.info("Running interim selector training on %d train + %d val", len(train), len(val))
                selector_results = train_repair_selectors(
                    train, val, test,
                    extract_features=extract_features,
                    feature_names=list(LEGAL_FEATURES),
                    out_dir=output_dir / "interim_selector",
                    final_eval=False,
                )
                last_selector_train = n_processed

    timed_out = time.time() >= _COLLECTION_DEADLINE or _SHUTDOWN
    train, val, test = split_rows(records)
    run_meta.update(
        {
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "timeout" if timed_out else "complete",
            "n_records_total": len(records),
            "n_new_queries": len({(r["query_metadata"]["dataset"], r["query_metadata"]["query_id"]) for r in records}),
            "n_new_this_run": n_new,
            "timed_out": timed_out,
        }
    )
    try:
        if len(records) >= 5:
            log.info("Final locked-test selector evaluation")
            selector_results = train_repair_selectors(
                train, val, test,
                extract_features=extract_features,
                feature_names=list(LEGAL_FEATURES),
                out_dir=output_dir / "final_selector",
                final_eval=True,
            )
    except Exception:
        log.exception("Final selector training crashed -- reports will be written with selector_results=None")
        run_meta["final_selector_training_error"] = traceback.format_exc()[-4000:]
    finally:
        # Reports and checkpoint state must be written no matter what
        # happened above: an unhandled exception here previously killed the
        # process before write_all_reports()/ckpt.close() ever ran, leaving
        # an 11+ hour mining run with no final reports at all.
        try:
            write_all_reports(
                output_dir,
                records=records,
                run_meta=run_meta,
                selector_results=selector_results,
                provider_statuses=provider_statuses,
                timed_out=timed_out,
            )
        except Exception:
            log.exception("write_all_reports crashed -- writing raw run_manifest.json as a fallback")
            run_meta["status"] = "error_during_report_writing"
            run_meta["report_writing_error"] = traceback.format_exc()[-4000:]
            ckpt.write_json("run_manifest.json", run_meta)
        ckpt.save_checkpoint(run_meta)
        ckpt.close()

    log.info("Overnight run finished: %d records, status=%s", len(records), run_meta["status"])
    return run_meta


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datasets", nargs="+", default=["scidocs", "fiqa", "hotpotqa", "bright"], choices=list(supported_datasets()))
    p.add_argument("--max-queries-per-dataset", type=int, default=80)
    p.add_argument("--max-candidates", type=int, default=15)
    p.add_argument("--vote-regimes", nargs="+", default=None, choices=list(VOTE_REGIMES))
    p.add_argument("--providers", type=str, default="cohere,gemini,azure,cloudrift,fireworks")
    p.add_argument("--max-llm-calls", type=int, default=2500)
    p.add_argument("--use-cache", action="store_true", default=True)
    p.add_argument("--no-cache", action="store_false", dest="use_cache")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--wall-seconds", type=int, default=8 * 3600 + 30 * 60)
    p.add_argument(
        "--collection-stop-seconds",
        type=int,
        default=None,
        help="Stop collecting new queries by this many seconds after start, "
        "reserving (wall_seconds - collection_stop_seconds) for the final "
        "locked-test selector evaluation and report writing. Defaults to "
        "wall_seconds (no reserved tail) if unset.",
    )
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--selector-train-every", type=int, default=25)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument(
        "--reused-from",
        type=str,
        default=None,
        help="Path to a prior run's output dir whose checkpoint_state.json / "
        "query_level_full_records.jsonl / CSVs / llm_cache were copied into "
        "this run's --output-dir before launch, for provenance in run_manifest.json.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    run_overnight(args)


if __name__ == "__main__":
    main()
