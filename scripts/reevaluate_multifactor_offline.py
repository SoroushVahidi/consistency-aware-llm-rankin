#!/usr/bin/env python3
"""Offline multifactor reevaluation from cached judgments (zero paid API calls).

Replays acquisition policies and the production UHT safety floor using only
PARSED_JUDGMENTS.jsonl + QUERY_SAMPLE.csv from an existing multifactor report.
Writes a new timestamped report directory; never overwrites the invalid source.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from consistency_ranker.adaptive_acquisition import synthetic_roster  # noqa: E402
from consistency_ranker.multifactor_acquisition.analyze import (  # noqa: E402
    DEFAULT_CONTRACT,
    analyze_cell_summaries,
    build_policy_comparison_table,
    eval_ranking,
    load_qrels,
    ranking_from_evidence,
    ranking_from_prior,
    render_verdict,
    write_final_report,
)
from consistency_ranker.multifactor_acquisition.cache_only_judge import (  # noqa: E402
    CacheOnlyJudge,
)
from consistency_ranker.multifactor_acquisition.sampling import (  # noqa: E402
    SEED,
    TOP_K,
    load_samples_from_csv,
)
from consistency_ranker.policy_selection.diagnostic_probes import (  # noqa: E402
    ProbeConfig,
    run_diagnostic_probes,
)
from consistency_ranker.policy_selection.policy_runner import (  # noqa: E402
    _build_cfg,
    policy_to_engine_kwargs,
)
from consistency_ranker.policy_selection.production_runner import (  # noqa: E402
    run_production_uht,
)
from consistency_ranker.prior_robust import (  # noqa: E402
    make_initial_robust_state,
    run_robust_acquisition,
)

POLICIES = ("UHT", "CHALLENGER", "HYBRID", "ROBUST_COMBINED")
BUDGETS = (3, 5, 8)
PROMPTS = ("legacy_v1", "concise_v1")
ORIENTATIONS = ("ab", "ba")
CODE_VERSION = "multifactor_acquisition_eval_fix_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            flat = dict(r)
            if isinstance(flat.get("extra"), (dict, list)):
                flat["extra"] = json.dumps(flat["extra"], ensure_ascii=False, default=str)
            w.writerow(flat)


def _state_ranking(state) -> list[str]:
    r = getattr(state, "ranking", None)
    if r:
        return list(r)
    pr = getattr(state, "prior_ranking", None)
    if callable(pr):
        return list(pr())
    return []


def _load_parsed(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_factor_cells(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _run_policy(*, policy: str, state, profiles, judge, budget: int, top_k: int, seed: int):
    mapping = policy_to_engine_kwargs(policy)  # type: ignore[arg-type]
    cfg = _build_cfg(mapping["cfg"], budget=budget, seed=seed, top_k=top_k)
    return run_robust_acquisition(
        state,
        profiles,
        judge,
        cfg=cfg,
        alt_priors=None,
        true_ranking=None,
        policy_name=mapping["policy_name"],
    )


def _row_from_eval(
    *,
    cell_id: str,
    sample,
    provider: str,
    model: str,
    prompt_version: str,
    orientation: str,
    policy: str,
    budget: int,
    oc,
    utility,
    judge: CacheOnlyJudge,
    status: str,
    extra: dict | None = None,
) -> dict[str, Any]:
    extra_oc = None if oc is None else (oc.extra or {})
    return {
        "cell_id": cell_id,
        "dataset": sample.dataset,
        "query_id": sample.query_id,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "orientation": orientation,
        "policy": policy,
        "budget": budget,
        "utility": utility,
        "ndcg_at_k": None if oc is None else extra_oc.get("ndcg_at_k"),
        "mrr_at_k": None if oc is None else extra_oc.get("mrr_at_k"),
        "recall_at_k": None if oc is None else extra_oc.get("recall_at_k"),
        "prior_topk_jaccard": None if oc is None else extra_oc.get("prior_topk_jaccard"),
        "prior_kendall_tau": None if oc is None else extra_oc.get("prior_kendall_tau"),
        "prior_topk_jaccard_informative": (
            None if oc is None else extra_oc.get("prior_topk_jaccard_informative")
        ),
        "agreement_metric_informative": (
            None if oc is None else extra_oc.get("agreement_metric_informative")
        ),
        "topk_jaccard": None if oc is None else oc.topk_jaccard,
        "n_calls": None if oc is None else oc.n_calls,
        "catastrophic": None if oc is None else oc.catastrophic,
        "buried_recovered": None if oc is None else oc.buried_recovered,
        "has_qrels": None if oc is None else extra_oc.get("has_qrels"),
        "missing_qrels_reason": None if oc is None else extra_oc.get("missing_qrels_reason"),
        "status": status,
        "unique_calls_cell": judge.n_unique_served,
        "cache_hits_cell": judge.n_hits,
        "cache_misses_cell": judge.n_misses,
        "paid_api_calls": judge.paid_api_calls,
        "effective_depth": getattr(sample, "effective_depth", None),
        "extra": extra or {},
        "ts": _utc(),
    }


def _load_policy_traces(path: Path) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Map (cell_id, policy, budget) → trace row with ranking."""
    out: dict[tuple[str, str, int], dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            try:
                key = (str(row["cell_id"]), str(row["policy"]), int(row["budget"]))
            except Exception:  # noqa: BLE001
                continue
            if row.get("ranking"):
                out[key] = row
    return out


def process_cell_offline(
    *,
    sample,
    provider: str,
    model: str,
    prompt_version: str,
    orientation: str,
    parsed_rows: list[dict[str, Any]],
    qrels: dict[str, int],
    policy_traces: dict[tuple[str, str, int], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    cell_id = f"{sample.dataset}|{sample.query_id}|{provider}|{prompt_version}|{orientation}"
    candidates = list(sample.doc_ids)
    prior = dict(sample.prior_scores)
    prior_ranking = ranking_from_prior(prior)
    depth = int(getattr(sample, "effective_depth", len(candidates)))
    top_k_eff = min(TOP_K, depth, len(candidates))
    judge = CacheOnlyJudge.from_parsed_rows(
        parsed_rows,
        query_id=sample.query_id,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        orientation=orientation,
    )
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    rows: list[dict[str, Any]] = []
    traces = policy_traces or {}

    oc, u = eval_ranking(
        prior_ranking,
        qrels,
        k=top_k_eff,
        n_calls=0,
        policy="always_unrepaired",
        prior_ranking=prior_ranking,
        candidate_pool=candidates,
    )
    rows.append(
        _row_from_eval(
            cell_id=cell_id,
            sample=sample,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            orientation=orientation,
            policy="always_unrepaired",
            budget=0,
            oc=oc,
            utility=u,
            judge=judge,
            status="complete",
        )
    )

    for policy in POLICIES:
        for budget in BUDGETS:
            trace = traces.get((cell_id, policy, int(budget)))
            if trace is not None:
                ranking = list(trace["ranking"])
                n_calls = int(trace.get("n_calls") or 0)
                source = "policy_traces_live"
            else:
                base_state = make_initial_robust_state(
                    query_id=sample.query_id,
                    candidate_ids=candidates,
                    prior_scores=prior,
                    budget=max(BUDGETS),
                    top_k=top_k_eff,
                    seed=SEED,
                )
                probe_state = copy.deepcopy(base_state)
                probe_res = run_diagnostic_probes(
                    probe_state,
                    profiles,
                    judge,
                    cfg=ProbeConfig(design="mixed_diagnostic", max_budget=3, profile_index=0),
                    alt_priors=None,
                    seed=SEED,
                )
                probe_calls = int(probe_res.n_executed)
                st = copy.deepcopy(probe_state)
                remaining = max(0, int(budget) - probe_calls)
                st.remaining_budget = remaining
                st.budget = budget
                before_hits = judge.n_hits
                result = _run_policy(
                    policy=policy,
                    state=st,
                    profiles=profiles,
                    judge=judge,
                    budget=remaining,
                    top_k=top_k_eff,
                    seed=SEED,
                )
                ranking = _state_ranking(result.state)
                n_calls = min(budget, probe_calls + max(0, judge.n_hits - before_hits))
                source = "cache_only_replay"
            oc, u = eval_ranking(
                ranking,
                qrels,
                k=top_k_eff,
                n_calls=n_calls,
                policy=policy,
                prior_ranking=prior_ranking,
                candidate_pool=candidates,
            )
            rows.append(
                _row_from_eval(
                    cell_id=cell_id,
                    sample=sample,
                    provider=provider,
                    model=model,
                    prompt_version=prompt_version,
                    orientation=orientation,
                    policy=policy,
                    budget=budget,
                    oc=oc,
                    utility=u,
                    judge=judge,
                    status="complete",
                    extra={"ranking_source": source},
                )
            )

    cell_evidence = [
        r
        for r in parsed_rows
        if sample.query_id in str(r.get("identity") or r.get("query_id") or "")
        and provider in str(r.get("identity") or r.get("provider") or "")
        and prompt_version in str(r.get("identity") or r.get("prompt_version") or "")
        and orientation in str(r.get("identity") or r.get("displayed_orientation") or "")
    ]
    rep_rank = ranking_from_evidence(cell_evidence, candidates, repair=True)
    unrepaired_rank = ranking_from_evidence(cell_evidence, candidates, repair=False)
    for name, ranking in (("always_repair", rep_rank), ("graph_unrepaired", unrepaired_rank)):
        oc, u = eval_ranking(
            ranking,
            qrels,
            k=top_k_eff,
            n_calls=judge.n_unique_served,
            policy=name,
            prior_ranking=prior_ranking,
            candidate_pool=candidates,
        )
        rows.append(
            _row_from_eval(
                cell_id=cell_id,
                sample=sample,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                orientation=orientation,
                policy=name,
                budget=judge.n_unique_served,
                oc=oc,
                utility=u,
                judge=judge,
                status="complete",
            )
        )

    # Dedicated judges per safeguard budget so production is not starved by
    # earlier policy consumption — cache hits are reusable offline.
    for budget in BUDGETS:
        plain_judge = CacheOnlyJudge.from_parsed_rows(
            parsed_rows,
            query_id=sample.query_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            orientation=orientation,
        )
        st = make_initial_robust_state(
            query_id=sample.query_id,
            candidate_ids=candidates,
            prior_scores=prior,
            budget=budget,
            top_k=top_k_eff,
            seed=SEED,
        )
        before = plain_judge.n_hits
        plain = _run_policy(
            policy="UHT",
            state=st,
            profiles=profiles,
            judge=plain_judge,
            budget=budget,
            top_k=top_k_eff,
            seed=SEED,
        )
        plain_calls = max(0, plain_judge.n_hits - before)
        plain_rank = _state_ranking(plain.state)
        oc_p, u_p = eval_ranking(
            plain_rank,
            qrels,
            k=top_k_eff,
            n_calls=plain_calls,
            policy="plain_uht",
            prior_ranking=prior_ranking,
            candidate_pool=candidates,
        )
        rows.append(
            _row_from_eval(
                cell_id=cell_id,
                sample=sample,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                orientation=orientation,
                policy="plain_uht",
                budget=budget,
                oc=oc_p,
                utility=u_p,
                judge=plain_judge,
                status="complete",
            )
        )

        prod_judge = CacheOnlyJudge.from_parsed_rows(
            parsed_rows,
            query_id=sample.query_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            orientation=orientation,
        )
        prod = run_production_uht(
            world={
                "candidate_ids": candidates,
                "prior_scores": prior,
                "judge": prod_judge,
            },
            budget=budget,
            top_k=top_k_eff,
            seed=SEED,
            query_id=sample.query_id,
        )
        prod_rank = list(prod.ranking)
        oc_r, u_r = eval_ranking(
            prod_rank,
            qrels,
            k=top_k_eff,
            n_calls=int(prod.n_calls),
            policy="production_uht",
            prior_ranking=prior_ranking,
            candidate_pool=candidates,
        )
        rows.append(
            _row_from_eval(
                cell_id=cell_id,
                sample=sample,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                orientation=orientation,
                policy="production_uht",
                budget=budget,
                oc=oc_r,
                utility=u_r,
                judge=prod_judge,
                status="complete",
                extra={
                    "safeguards": prod.safeguards.to_dict(),
                    "execution_mode": prod.execution_mode.value,
                    "executed_policy": prod.executed_policy,
                    "experimental_escalation_disabled": True,
                    "paid_api_calls": 0,
                    "ranking_source": "production_runner_cache_only",
                },
            )
        )

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Invalid/original multifactor report directory (cached judgments).",
    )
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--max-cells", type=int, default=None)
    args = ap.parse_args()

    source: Path = args.source_dir
    output_dir: Path = args.output_dir
    if output_dir.resolve() == source.resolve():
        raise SystemExit("Refusing to overwrite the source report directory.")
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    commit = os.popen("git rev-parse HEAD").read().strip()
    samples = load_samples_from_csv(REPO, source / "QUERY_SAMPLE.csv")
    by_qid = {s.query_id: s for s in samples}
    parsed = _load_parsed(source / "PARSED_JUDGMENTS.jsonl")
    policy_traces = _load_policy_traces(source / "POLICY_TRACES.jsonl")
    factor_cells = _load_factor_cells(source / "FACTOR_CELLS.csv")
    if args.max_cells is not None:
        factor_cells = factor_cells[: args.max_cells]

    qrels_map = {
        ds: load_qrels(REPO, ds) for ds in sorted({s.dataset for s in samples})
    }
    # Resolve model per provider from MANIFEST when present.
    models: dict[str, str] = {}
    if (source / "MANIFEST.json").exists():
        man = json.loads((source / "MANIFEST.json").read_text(encoding="utf-8"))
        for p in man.get("providers") or []:
            if p.get("provider") and p.get("model"):
                models[str(p["provider"])] = str(p["model"])
    # Fallback: inspect parsed identities.
    if not models:
        for row in parsed[:50]:
            ident = str(row.get("identity") or "")
            parts = ident.split("|")
            if len(parts) >= 5:
                models.setdefault(parts[-4], parts[-3])

    all_rows: list[dict[str, Any]] = []
    n_missing_qrels = 0
    for i, cell in enumerate(factor_cells):
        qid = cell["query_id"]
        sample = by_qid.get(qid)
        if sample is None:
            continue
        provider = cell["provider"]
        prompt_version = cell["prompt_version"]
        orientation = cell["orientation"]
        model = models.get(provider) or cell.get("model") or "unknown"
        qrels = qrels_map.get(sample.dataset, {}).get(qid, {})
        if not any(int(v) > 0 for v in qrels.values() if str(v)):
            # Still evaluate; contract records missing.
            n_missing_qrels += 1
        cell_rows = process_cell_offline(
            sample=sample,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            orientation=orientation,
            parsed_rows=parsed,
            qrels=qrels,
            policy_traces=policy_traces,
        )
        all_rows.extend(cell_rows)
        if (i + 1) % 20 == 0:
            print(f"processed {i + 1}/{len(factor_cells)} cells", flush=True)

    _write_csv(output_dir / "CELL_SUMMARY.csv", all_rows)
    with (output_dir / "CELL_SUMMARY.jsonl").open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    policy_rows = [
        r
        for r in all_rows
        if r.get("policy") in POLICIES and r.get("utility") not in (None, "")
    ]
    for r in policy_rows:
        r["utility"] = float(r["utility"])
        r["budget"] = int(r["budget"])
    analysis = analyze_cell_summaries(policy_rows) if policy_rows else {"policy_summaries": []}
    comparison_table = build_policy_comparison_table(
        all_rows,
        baseline_policy="production_uht",
        policies=(
            "production_uht",
            "plain_uht",
            "UHT",
            "CHALLENGER",
            "HYBRID",
            "ROBUST_COMBINED",
            "always_unrepaired",
        ),
        budgets=BUDGETS,
    )
    verdict_detail = render_verdict(comparison_table)
    verdict = str(verdict_detail.get("verdict"))

    # Safeguard summary
    sg_rows = [r for r in all_rows if r.get("policy") == "production_uht"]
    sg_stats: dict[str, Any] = {
        "n_production_uht_rows": len(sg_rows),
        "outsider_probe_executed_rate": None,
        "final_challenger_executed_rate": None,
        "production_safeguards_complete_rate": None,
        "outsider_skip_reasons": {},
        "final_skip_reasons": {},
        "mean_safeguard_calls": None,
    }
    if sg_rows:
        outs = finals = complete = 0
        sg_calls = []
        out_skips: dict[str, int] = defaultdict(int)
        fin_skips: dict[str, int] = defaultdict(int)
        for r in sg_rows:
            sg = (r.get("extra") or {}).get("safeguards") or {}
            outs += int(bool(sg.get("outsider_probe_executed")))
            finals += int(bool(sg.get("final_challenger_executed")))
            complete += int(bool(sg.get("production_safeguards_complete")))
            sg_calls.append(float(sg.get("safeguard_calls") or 0))
            if not sg.get("outsider_probe_executed"):
                out_skips[str(sg.get("outsider_probe_skip_reason") or "unknown")] += 1
            if not sg.get("final_challenger_executed"):
                fin_skips[str(sg.get("final_challenger_skip_reason") or "unknown")] += 1
        n = len(sg_rows)
        sg_stats.update(
            {
                "outsider_probe_executed_rate": outs / n,
                "final_challenger_executed_rate": finals / n,
                "production_safeguards_complete_rate": complete / n,
                "outsider_skip_reasons": dict(out_skips),
                "final_skip_reasons": dict(fin_skips),
                "mean_safeguard_calls": sum(sg_calls) / n,
            }
        )

    source_hashes = {
        "QUERY_SAMPLE.csv": _sha256_file(source / "QUERY_SAMPLE.csv"),
        "PARSED_JUDGMENTS.jsonl": _sha256_file(source / "PARSED_JUDGMENTS.jsonl"),
        "FACTOR_CELLS.csv": _sha256_file(source / "FACTOR_CELLS.csv"),
        "POLICY_TRACES.jsonl": (
            _sha256_file(source / "POLICY_TRACES.jsonl")
            if (source / "POLICY_TRACES.jsonl").exists()
            else None
        ),
    }
    qrels_hashes = {}
    for ds, qmap in qrels_map.items():
        # Hash the underlying file when present.
        if ds == "hotpotqa":
            qp = REPO / "data/processed/hotpotqa/qrels.jsonl"
        else:
            qp = REPO / f"data/processed/beir/{ds}/qrels.jsonl"
        if qp.exists():
            qrels_hashes[ds] = _sha256_file(qp)

    prod_ndcg = [
        float(r["ndcg_at_k"])
        for r in sg_rows
        if r.get("ndcg_at_k") not in (None, "")
    ]
    prod_prior = [
        float(r["prior_topk_jaccard"])
        for r in sg_rows
        if r.get("prior_topk_jaccard") not in (None, "")
    ]

    manifest = {
        "experiment": "real_query_multifactor_acquisition_corrected",
        "code_version": CODE_VERSION,
        "source_commit": commit,
        "source_report": str(source),
        "generated_utc": _utc(),
        "paid_api_calls": 0,
        "api_calls_statement": (
            "No paid API calls were made. All judgments were served from "
            "cached PARSED_JUDGMENTS.jsonl via CacheOnlyJudge."
        ),
        "evaluation_contract": DEFAULT_CONTRACT.to_dict(),
        "candidate_pool_specification": (
            "Per QUERY_SAMPLE.csv doc_ids; effective_depth = min(12, usable texts); "
            "identical pool for every policy within a factor cell."
        ),
        "evaluation_cutoff": "min(TOP_K=12, effective_depth, len(candidates))",
        "utility_coefficients": {
            "lambda_c": DEFAULT_CONTRACT.lambda_c,
            "lambda_r": DEFAULT_CONTRACT.lambda_r,
            "formula": DEFAULT_CONTRACT.utility_formula,
        },
        "input_artifact_hashes": source_hashes,
        "qrels_hashes": qrels_hashes,
        "n_factor_cells": len(factor_cells),
        "n_rows": len(all_rows),
        "n_queries": len(samples),
        "n_missing_qrels_cells": n_missing_qrels,
        "production_uht_n_ndcg_valid": len(prod_ndcg),
        "production_uht_mean_ndcg": (sum(prod_ndcg) / len(prod_ndcg)) if prod_ndcg else None,
        "production_uht_mean_prior_topk_jaccard": (
            (sum(prod_prior) / len(prod_prior)) if prod_prior else None
        ),
        "safeguard_summary": sg_stats,
        "verdict": verdict,
        "elapsed_s": time.time() - t0,
    }
    _write_json(output_dir / "MANIFEST.json", manifest)
    _write_json(
        output_dir / "ANALYSIS.json",
        {
            **analysis,
            "comparison_table": comparison_table,
            "verdict_detail": verdict_detail,
            "safeguard_summary": sg_stats,
        },
    )
    _write_json(output_dir / "COMPARISON_TABLE.json", comparison_table)
    _write_csv(output_dir / "COMPARISON_TABLE.csv", comparison_table)

    limitations = (
        "Acquisition policies UHT/CHALLENGER/HYBRID/ROBUST_COMBINED reuse rankings "
        "from the source POLICY_TRACES.jsonl when present (live acquisition, zero new "
        "API calls) and are re-scored under the shared qrels contract. "
        "plain_uht and production_uht are re-executed via CacheOnlyJudge. "
        "Call counts are modeled/replayed acquisition calls, not new paid charges. "
        "On this sample every query has eval_k == pool_size, so prior_topk_jaccard "
        "is structurally uninformative full-pool membership (always 1.0); use "
        "prior_kendall_tau for ranking agreement. With top_k == pool size, "
        "outsider/final-challenger probes are not eligible "
        "(skip_reason=not_eligible:no_insider_outsider_pairs); this run therefore "
        "does not empirically validate outsider/final-challenger execution on "
        "applicable real-query cells. production_safeguards_complete means every "
        "applicable safeguard reached a documented terminal state, not that every "
        "safeguard executed."
    )
    (output_dir / "KNOWN_LIMITATIONS.md").write_text(limitations + "\n", encoding="utf-8")

    write_final_report(
        output_dir / "FINAL_REPORT.md",
        {
            "verdict": verdict,
            "verdict_detail": verdict_detail,
            "comparison_table": comparison_table,
            "evaluation_contract": DEFAULT_CONTRACT.to_dict(),
            "coverage": {
                "planned_cells": len(factor_cells),
                "completed_cells": len(factor_cells),
                "queries": len(samples),
                "budgets": list(BUDGETS),
                "prompts": list(PROMPTS),
                "orientations": list(ORIENTATIONS),
                "source_report": str(source),
            },
            "cost": {
                "paid_api_calls": 0,
                "elapsed_s": time.time() - t0,
                "note": "Offline cache replay; no provider spend.",
            },
            "policy_results": analysis,
            "safeguards": sg_stats,
            "limitations": limitations,
            "api_calls_statement": manifest["api_calls_statement"],
        },
    )

    # Compact tracked-friendly summary (small).
    summary = {
        "verdict": verdict,
        "source_commit": commit,
        "source_report": str(source),
        "output_dir": str(output_dir),
        "paid_api_calls": 0,
        "production_uht_mean_ndcg": manifest["production_uht_mean_ndcg"],
        "production_uht_mean_prior_topk_jaccard": manifest[
            "production_uht_mean_prior_topk_jaccard"
        ],
        "safeguard_summary": sg_stats,
        "comparison_table": comparison_table,
        "input_artifact_hashes": source_hashes,
        "qrels_hashes": qrels_hashes,
    }
    _write_json(output_dir / "CORRECTED_SUMMARY.json", summary)

    print(json.dumps({"output_dir": str(output_dir), "verdict": verdict, **sg_stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
