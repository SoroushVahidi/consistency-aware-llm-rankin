#!/usr/bin/env python
"""
run_failure_mining.py
=====================
Failure-mining pipeline: deliberately collect query-level cases where our
repaired graph-ranking methods lose to external baselines, with full forensic
records for later analysis.

Usage
-----
Smoke test::

    python scripts/run_failure_mining.py \\
        --datasets scidocs \\
        --max-queries 3 \\
        --max-candidates 10 \\
        --providers none \\
        --use-cache --resume \\
        --output-dir reports/failure_mining_smoke \\
        --log-file reports/failure_mining_smoke/run.log

Full non-LLM run::

    python scripts/run_failure_mining.py \\
        --datasets scidocs fiqa hotpotqa bright \\
        --max-queries 100 \\
        --max-candidates 20 \\
        --providers none \\
        --use-cache --resume \\
        --output-dir reports/failure_mining \\
        --log-file reports/failure_mining/run.log
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO))

from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.failure_mining.analysis import (
    OUR_REPAIRED_METHOD,
    build_summary_markdown,
    write_aggregate_tables,
)
from consistency_ranker.failure_mining.data_setup import (
    VOTE_REGIMES,
    ensure_dataset_prepared,
    ensure_score_files,
    ensure_vote_file,
    load_documents_map,
    supported_datasets,
    write_query_ids,
)
from consistency_ranker.failure_mining.llm_runner import LLMRunner, detect_llm_providers
from consistency_ranker.failure_mining.query_processor import process_query_record
from consistency_ranker.pairwise_prefs import Preference
from scripts.run_real_experiment import _load_pairwise_preference_file, _load_score_prior_files

log = logging.getLogger(__name__)

CHECKPOINT_FILE = ".resume_checkpoint.jsonl"


class JsonlWriter:
    """Append-only JSONL writer."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, obj: dict) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, default=str) + "\n")


def _load_completed_keys(output_dir: Path, resume: bool) -> set[str]:
    if not resume:
        return set()
    keys: set[str] = set()
    ckpt = output_dir / CHECKPOINT_FILE
    if ckpt.exists():
        with ckpt.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    keys.add(json.loads(line)["key"])
    records = output_dir / "query_level_full_records.jsonl"
    if records.exists():
        with records.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                qm = rec.get("query_metadata", {})
                keys.add(f"{qm.get('dataset')}|{qm.get('vote_regime')}|{qm.get('query_id')}")
    return keys


def _record_key(dataset: str, regime: str, query_id: str) -> str:
    return f"{dataset}|{regime}|{query_id}"


def _load_all_records(output_dir: Path) -> list[dict]:
    path = output_dir / "query_level_full_records.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _setup_logging(log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def _restrict_prefs(prefs: list[Preference], top_k: int) -> list[Preference]:
    nodes: set[str] = set()
    for p in prefs:
        nodes.add(p.winner)
        nodes.add(p.loser)
    if len(nodes) <= top_k:
        return prefs
    # Keep prefs among top-k by score_sum wins
    from consistency_ranker.baseline_ranking import score_sum_scores
    from consistency_ranker.graph_construction import build_graph

    g = build_graph(prefs)
    scores = score_sum_scores(g)
    keep = set(sorted(scores, key=lambda n: (-scores[n], n))[:top_k])
    return [p for p in prefs if p.winner in keep and p.loser in keep]


def run_failure_mining(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_root = output_dir / "_work"
    work_root.mkdir(parents=True, exist_ok=True)

    completed = _load_completed_keys(output_dir, args.resume)
    if completed:
        log.info("Resume: skipping %d completed query×regime keys", len(completed))

    writers = {
        "full": JsonlWriter(output_dir / "query_level_full_records.jsonl"),
        "rankings": JsonlWriter(output_dir / "method_rankings_by_query.jsonl"),
        "edges": JsonlWriter(output_dir / "preference_edges_by_query.jsonl"),
        "repair": JsonlWriter(output_dir / "repair_edges_removed.jsonl"),
    }
    ckpt_writer = JsonlWriter(output_dir / CHECKPOINT_FILE)

    active_regimes = tuple(args.vote_regimes) if args.vote_regimes else VOTE_REGIMES
    provider_list = [p.strip() for p in args.providers.split(",") if p.strip()]
    llm_runner = None
    llm_writer = None
    if provider_list and provider_list != ["none"]:
        llm_writer = JsonlWriter(output_dir / "llm_call_records.jsonl")
        # Budget covers the *entire* run: every dataset x every vote regime x
        # up to max_queries queries x every provider. A budget scoped to a
        # single dataset (e.g. max_queries * len(provider_list)) silently
        # exhausts partway through the first dataset and starves every
        # subsequent dataset/regime of real LLM calls with no error raised.
        if args.max_llm_calls is not None:
            max_calls = args.max_llm_calls
        elif args.max_queries:
            max_calls = (
                args.max_queries * len(provider_list) * len(args.datasets) * len(active_regimes)
            )
        else:
            max_calls = None
        llm_runner = LLMRunner(
            output_path=output_dir / "llm_call_records.jsonl",
            cache_dir=output_dir / "llm_cache",
            max_calls=max_calls,
            use_cache=args.use_cache,
        )
        log.info(
            "LLM budget: max_calls=%s (datasets=%d, regimes=%d [%s], providers=%d, max_queries=%s)",
            max_calls, len(args.datasets), len(active_regimes), ",".join(active_regimes),
            len(provider_list), args.max_queries,
        )
        for st in detect_llm_providers(provider_list):
            log.info("LLM provider %s: available=%s (%s)", st.provider, st.available, st.reason)

    n_processed = 0
    n_skipped = 0
    datasets = args.datasets

    for dataset in datasets:
        log.info("=== Dataset: %s ===", dataset)
        try:
            ensure_dataset_prepared(dataset, max_queries=args.max_queries)
        except Exception as exc:
            log.error("Skipping dataset %s: preparation failed: %s", dataset, exc)
            continue
        queries, _, qrels = load_dataset_splits(dataset)
        qrels_by_q: dict[str, list] = defaultdict(list)
        for e in qrels:
            qrels_by_q[e.query_id].append(e)

        ds_work = work_root / dataset
        qfile = ds_work / "query_ids.txt"
        if args.query_id_file:
            query_ids = [
                line.strip() for line in args.query_id_file.read_text().splitlines() if line.strip()
            ]
            qfile.parent.mkdir(parents=True, exist_ok=True)
            qfile.write_text("\n".join(query_ids) + "\n", encoding="utf-8")
            log.info("  using %d targeted query ids from %s", len(query_ids), args.query_id_file)
        else:
            query_ids = write_query_ids(dataset, qfile, args.max_queries)
        score_files = ensure_score_files(
            dataset,
            ds_work,
            query_ids=query_ids,
            top_n=max(args.max_candidates * 2, 30),
        )
        score_prior_sets = _load_score_prior_files(score_files)
        doc_map = load_documents_map(dataset)
        query_text_map = {q.query_id: q.text for q in queries if q.query_id in set(query_ids)}

        for regime in active_regimes:
            vote_path = ensure_vote_file(
                dataset,
                ds_work,
                regime,
                score_files,
                top_k=args.max_candidates,
                query_id_file=qfile,
            )
            pairwise_index = _load_pairwise_preference_file(vote_path)
            log.info("  regime=%s votes for %d queries", regime, len(pairwise_index))

            for qid in query_ids:
                key = _record_key(dataset, regime, qid)
                if key in completed:
                    n_skipped += 1
                    continue

                qrels_for_query = qrels_by_q.get(qid, [])
                prefs = _restrict_prefs(pairwise_index.get(qid, []), args.max_candidates)
                if not prefs:
                    log.debug("Skip %s: no preferences", key)
                    continue

                snippets = {
                    d: doc_map[d]
                    for d in {p.winner for p in prefs} | {p.loser for p in prefs}
                    if d in doc_map
                }

                record = process_query_record(
                    dataset=dataset,
                    vote_regime=regime,
                    query_id=qid,
                    query_text=query_text_map.get(qid),
                    split="test",
                    qrels_for_query=qrels_for_query,
                    prefs=prefs,
                    score_prior_sets=score_prior_sets,
                    top_k=args.max_candidates,
                    doc_snippets=snippets,
                )
                if record is None:
                    continue

                # Optional LLM baselines
                if llm_runner and provider_list != ["none"]:
                    cand_ids = record["query_metadata"]["candidate_doc_ids"][: args.max_candidates]
                    doc_texts = {
                        d: f"{snippets.get(d, {}).get('title', '')}\n{snippets.get(d, {}).get('text_snippet', '')}"
                        for d in cand_ids
                    }
                    for prov in provider_list:
                        if prov == "none":
                            continue
                        llm_out = llm_runner.run_pairwise_rerank(
                            provider=prov,
                            query_id=qid,
                            query_text=query_text_map.get(qid, ""),
                            doc_texts=doc_texts,
                            candidate_ids=cand_ids,
                        )
                        if llm_out:
                            method_name = f"llm_{prov}_pairwise"
                            record["method_outputs"][method_name] = {
                                "ranking": llm_out["ranking"],
                                "scores": llm_out["scores"],
                                "llm_record_ref": llm_out.get("llm_record"),
                            }

                writers["full"].write(record)
                writers["rankings"].write(
                    {
                        "dataset": dataset,
                        "vote_regime": regime,
                        "query_id": qid,
                        "rankings": {
                            m: o.get("ranking") for m, o in record["method_outputs"].items()
                        },
                    }
                )
                writers["edges"].write(
                    {
                        "dataset": dataset,
                        "vote_regime": regime,
                        "query_id": qid,
                        "edges": record["graph_stats"].get("preference_edges", []),
                    }
                )
                writers["repair"].write(
                    {
                        "dataset": dataset,
                        "vote_regime": regime,
                        "query_id": qid,
                        **record["repair_info"],
                    }
                )
                ckpt_writer.write({"key": key})
                completed.add(key)
                n_processed += 1

                if n_processed % 10 == 0:
                    log.info("  processed %d records (skipped %d)", n_processed, n_skipped)

    records = _load_all_records(output_dir)
    write_aggregate_tables(output_dir, records)
    run_meta = {
        "status": "complete" if n_processed >= 0 else "partial",
        "n_records_total": len(records),
        "n_new_this_run": n_processed,
        "n_skipped_resume": n_skipped,
        "datasets": datasets,
        "max_queries": args.max_queries,
        "max_candidates": args.max_candidates,
        "providers": provider_list,
        "our_method": OUR_REPAIRED_METHOD,
    }
    build_summary_markdown(output_dir, records, run_meta)
    log.info(
        "Done. %d new records, %d total, output=%s",
        n_processed,
        len(records),
        output_dir,
    )
    return run_meta


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--datasets",
        nargs="+",
        default=["scidocs"],
        choices=list(supported_datasets()),
    )
    p.add_argument("--max-queries", type=int, default=50)
    p.add_argument("--max-candidates", type=int, default=20)
    p.add_argument(
        "--vote-regimes",
        nargs="+",
        default=None,
        choices=list(VOTE_REGIMES),
        help=(
            "If given, restrict the run to exactly these vote regimes instead "
            "of all of VOTE_REGIMES (ms1, ms2, ms1_drop_mutual). Also scopes "
            "the auto-computed LLM call budget accordingly."
        ),
    )
    p.add_argument(
        "--query-id-file",
        type=Path,
        default=None,
        help=(
            "If given, use exactly these query ids (one per line) instead of "
            "the first --max-queries ids in processed-file order. Intended for "
            "targeted coverage of specific, pre-selected queries (e.g. a "
            "disagreement-ranked subset). Only meaningful with a single "
            "--datasets value; applied verbatim to every requested dataset."
        ),
    )
    p.add_argument(
        "--providers",
        type=str,
        default="none",
        help=(
            "Comma-separated (no spaces) LLM providers, e.g. "
            "'cohere,gemini,azure' or 'none'. Choices: "
            "cohere,gemini,cloudrift,azure,openai,none"
        ),
    )
    p.add_argument(
        "--max-llm-calls",
        type=int,
        default=None,
        help=(
            "Hard cap on total successful LLM pairwise-rerank calls across the "
            "whole run (all datasets x regimes x providers). Defaults to "
            "max_queries * len(providers) * len(datasets) * len(vote_regimes), "
            "i.e. enough to cover every requested query. Set explicitly for a "
            "tighter cost/time ceiling."
        ),
    )
    p.add_argument("--use-cache", action="store_true", default=True)
    p.add_argument("--no-cache", action="store_false", dest="use_cache")
    p.add_argument("--resume", action="store_true", help="Skip completed query×regime keys")
    p.add_argument("--output-dir", type=Path, default=Path("reports/failure_mining"))
    p.add_argument("--log-file", type=Path, default=Path("reports/failure_mining/run.log"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    _setup_logging(args.log_file)
    run_failure_mining(args)


if __name__ == "__main__":
    main()
