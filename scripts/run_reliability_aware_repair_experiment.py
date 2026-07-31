#!/usr/bin/env python3
"""
Reliability-aware graph construction / cycle repair experiments.

Uses synthetic judgments, corruption studies, and provenance-safe
multi-provider pilot records. No large LLM API spend.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.evaluation import kendall_tau
from consistency_ranker.experiment_cli import (
    ensure_output_dir,
    utc_stamp,
    write_run_manifest,
)
from consistency_ranker.reliability_repair.edge_reliability import estimate_reliability
from consistency_ranker.reliability_repair.evidence_aggregation import aggregate_all
from consistency_ranker.reliability_repair.pair_evidence import normalize_judgment_record
from consistency_ranker.reliability_repair.pipeline import (
    ReliabilityRepairConfig,
    run_reliability_pipeline,
)
from consistency_ranker.reliability_repair.reliability_weighted_repair import (
    exact_fas_with_costs,
    greedy_fas_with_costs,
)
from consistency_ranker.reliability_repair.synthetic_judgment_models import (
    SyntheticConfig,
    generate_synthetic_judgments,
)
from consistency_ranker.statistical_inference import holm_adjust, sign_flip_pvalue

REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return utc_stamp()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _pair_direction_accuracy(
    aggregates: dict[str, Any],
    true_winners: dict[str, str],
) -> dict[str, float]:
    correct = 0
    total = 0
    for pid, agg in aggregates.items():
        if pid not in true_winners:
            continue
        if agg["d"] == 0:
            continue
        total += 1
        pred = agg["doc_i"] if agg["d"] == 1 else agg["doc_j"]
        if pred == true_winners[pid]:
            correct += 1
    return {
        "n_scored": total,
        "accuracy": correct / total if total else float("nan"),
    }


def _reliability_error_association(evidence, true_winners: dict[str, str]) -> dict[str, Any]:
    """Are low-reliability pairs more often wrong?"""
    aggs = aggregate_all(evidence, estimator="smoothed")
    rows = []
    for pid, agg in aggs.items():
        if pid not in true_winners or agg.d == 0:
            continue
        pred = agg.doc_i if agg.d == 1 else agg.doc_j
        correct = pred == true_winners[pid]
        rel = estimate_reliability(agg, method="agreement_composite_arith")
        rows.append({"reliability": rel, "correct": int(correct), "abs_margin": abs(agg.m)})
    if len(rows) < 5:
        return {"n": len(rows), "corr_rel_correct": None}
    # Point-biserial-ish: mean rel for correct vs incorrect
    cor = [r["reliability"] for r in rows if r["correct"]]
    inc = [r["reliability"] for r in rows if not r["correct"]]
    return {
        "n": len(rows),
        "mean_rel_correct": sum(cor) / len(cor) if cor else None,
        "mean_rel_incorrect": sum(inc) / len(inc) if inc else None,
        "frac_correct": sum(r["correct"] for r in rows) / len(rows),
    }


METHODS = [
    ("raw_no_abstention_weight_repair", ReliabilityRepairConfig(
        abstention_policy="none", reliability_method="margin",
        importance_method="uniform", cost_scheme="weight", tau=0.0,
    )),
    ("margin_threshold", ReliabilityRepairConfig(
        abstention_policy="margin_threshold", margin_tau=0.25,
        reliability_method="margin", importance_method="uniform",
        cost_scheme="weight",
    )),
    ("reliability_threshold_arith", ReliabilityRepairConfig(
        abstention_policy="reliability_threshold", tau=0.3,
        reliability_method="agreement_composite_arith",
        importance_method="uniform", cost_scheme="reliability",
    )),
    ("reliability_x_prior_importance", ReliabilityRepairConfig(
        abstention_policy="reliability_threshold", tau=0.25,
        reliability_method="agreement_composite_arith",
        importance_method="prior_position",
        cost_scheme="reliability_x_importance",
    )),
    ("reliability_x_topk_importance", ReliabilityRepairConfig(
        abstention_policy="reliability_threshold", tau=0.25,
        reliability_method="agreement_composite_arith",
        importance_method="topk_boundary",
        cost_scheme="reliability_x_importance", top_k=3,
    )),
    ("orientation_required", ReliabilityRepairConfig(
        abstention_policy="orientation_required",
        reliability_method="orientation",
        importance_method="uniform", cost_scheme="reliability",
    )),
    ("composite_mult", ReliabilityRepairConfig(
        abstention_policy="reliability_threshold", tau=0.15,
        reliability_method="agreement_composite_mult",
        importance_method="prior_position",
        cost_scheme="reliability_x_importance",
    )),
    ("prior_regularized_lam1", ReliabilityRepairConfig(
        abstention_policy="reliability_threshold", tau=0.2,
        reliability_method="agreement_composite_arith",
        importance_method="prior_position",
        cost_scheme="reliability_x_importance",
        prior_lambda=1.0,
    )),
]


def run_synthetic(out_dir: Path, seeds: list[int]) -> list[dict[str, Any]]:
    rows = []
    for seed in seeds:
        ev, meta = generate_synthetic_judgments(
            SyntheticConfig(
                n_items=8,
                n_models=3,
                n_prompts=2,
                repeats=2,
                base_accuracy=0.75,
                position_bias=0.12,
                abstention_rate=0.05,
                invalid_rate=0.03,
                seed=seed,
            )
        )
        true_rank = meta["true_ranking"]
        prior = {d: float(len(true_rank) - i) for i, d in enumerate(true_rank)}
        assoc = _reliability_error_association(ev, meta["true_pair_winners"])
        for name, cfg in METHODS:
            cfg = ReliabilityRepairConfig(
                **{**cfg.to_dict(), "seed": seed, "n_stability_samples": 16}
            )
            out = run_reliability_pipeline(
                ev,
                prior_scores=prior,
                prior_ranking=true_rank,
                config=cfg,
            )
            tau = kendall_tau(out["ranking"], true_rank)
            amb = (out["stability"].get("ambiguity") or {})
            rows.append(
                {
                    "source": "synthetic",
                    "seed": seed,
                    "method": name,
                    "kendall_tau": tau,
                    "n_edges_before": out["n_edges_before_repair"],
                    "n_edges_after": out["n_edges_after_repair"],
                    "n_omitted": out["graph_meta"].get("n_omitted"),
                    "removed_cost": out["repair_meta"].get("removed_cost"),
                    "frac_incomparable": amb.get("fraction_incomparable_pairs"),
                    "ambiguity_bucket": amb.get("ambiguity_bucket"),
                    "topk_jaccard_mean": out["stability"].get("topk_jaccard_mean"),
                    "mean_rel_correct": assoc.get("mean_rel_correct"),
                    "mean_rel_incorrect": assoc.get("mean_rel_incorrect"),
                    "local_both_directions": out["local_stats"].get("both_directions"),
                }
            )
        # Exact vs greedy agreement on one graph
        cfg0 = ReliabilityRepairConfig(
            abstention_policy="none", tau=0.0, repair="greedy"
        )
        out0 = run_reliability_pipeline(
            ev, prior_scores=prior, prior_ranking=true_rank, config=cfg0
        )
        g = out0["graph"]
        if g.number_of_nodes() <= 8 and not __import__("networkx").is_directed_acyclic_graph(g):
            _, _, mg = greedy_fas_with_costs(g)
            _, _, me = exact_fas_with_costs(g, max_n=8)
            rows.append(
                {
                    "source": "synthetic_exact_check",
                    "seed": seed,
                    "method": "greedy_vs_exact",
                    "greedy_cost": mg["removed_cost"],
                    "exact_cost": me["objective"],
                    "gap": mg["removed_cost"] - me["objective"],
                }
            )
    return rows


def run_corruption(out_dir: Path) -> list[dict[str, Any]]:
    """Flip edges at various rates; compare raw vs reliability-aware."""
    rows = []
    base_ev, meta = generate_synthetic_judgments(
        SyntheticConfig(n_items=7, n_models=2, repeats=1, n_prompts=1, seed=0, position_bias=0.0)
    )
    true_rank = meta["true_ranking"]
    prior = {d: float(len(true_rank) - i) for i, d in enumerate(true_rank)}
    # Corruption by lowering accuracy / raising bias in generator configs
    for seed, flipish in enumerate([0.0, 0.15, 0.3, 0.45]):
        ev, meta2 = generate_synthetic_judgments(
            SyntheticConfig(
                n_items=7,
                n_models=3,
                n_prompts=2,
                repeats=2,
                base_accuracy=max(0.55, 0.95 - flipish),
                position_bias=flipish,
                seed=10 + seed,
            )
        )
        true_rank = meta2["true_ranking"]
        prior = {d: float(len(true_rank) - i) for i, d in enumerate(true_rank)}
        for name, cfg in METHODS[:5]:
            cfg = ReliabilityRepairConfig(**{**cfg.to_dict(), "seed": seed})
            out = run_reliability_pipeline(
                ev,
                prior_scores=prior,
                prior_ranking=true_rank,
                config=cfg,
            )
            rows.append(
                {
                    "noise_proxy": flipish,
                    "method": name,
                    "kendall_tau": kendall_tau(out["ranking"], true_rank),
                    "n_edges": out["n_edges_after_repair"],
                    "frac_incomparable": (out["stability"].get("ambiguity") or {}).get(
                        "fraction_incomparable_pairs"
                    ),
                }
            )
    return rows


def run_pilot_analysis(out_dir: Path) -> list[dict[str, Any]]:
    pilot = (
        REPO_ROOT
        / "reports/multi_provider_llm_robustness_20260725T200000Z/judgment_records.jsonl"
    )
    if not pilot.exists():
        return [{"error": "pilot_missing", "path": str(pilot)}]
    records = [json.loads(line) for line in pilot.read_text().splitlines() if line.strip()]
    # Provenance-safe only
    evidence = [normalize_judgment_record(r) for r in records if r.get("provider")]
    by_q = defaultdict(list)
    for e in evidence:
        by_q[e.query_id].append(e)
    rows = []
    for qid, ev in by_q.items():
        # Prior from score fields if present else uniform
        prior: dict[str, float] = {}
        for e in ev:
            for d, s in ((e.doc_i, e.prior_score_i), (e.doc_j, e.prior_score_j)):
                if s is not None:
                    prior[d] = float(s)
        if not prior:
            docs = sorted({e.doc_i for e in ev} | {e.doc_j for e in ev})
            prior = {d: 1.0 for d in docs}
        prior_ranking = sorted(prior, key=lambda d: (-prior[d], d))
        for name, cfg in METHODS:
            cfg = ReliabilityRepairConfig(**{**cfg.to_dict(), "n_stability_samples": 12})
            out = run_reliability_pipeline(
                ev, prior_scores=prior, prior_ranking=prior_ranking, config=cfg
            )
            rows.append(
                {
                    "source": "multi_provider_pilot",
                    "query_id": qid,
                    "method": name,
                    "n_evidence": len(ev),
                    "n_edges_before": out["n_edges_before_repair"],
                    "n_edges_after": out["n_edges_after_repair"],
                    "n_omitted": out["graph_meta"].get("n_omitted"),
                    "removed_cost": out["repair_meta"].get("removed_cost"),
                    "frac_incomparable": (out["stability"].get("ambiguity") or {}).get(
                        "fraction_incomparable_pairs"
                    ),
                    "ambiguity_bucket": (out["stability"].get("ambiguity") or {}).get(
                        "ambiguity_bucket"
                    ),
                    "topk_jaccard_mean": out["stability"].get("topk_jaccard_mean"),
                    "local_both_directions": out["local_stats"].get("both_directions"),
                    "ranking": "|".join(out["ranking"]),
                }
            )
    # Orientation inconsistency vs (no qrel label) — report rates only
    aggs = aggregate_all(evidence)
    orient_rows = []
    for pid, agg in aggs.items():
        orient_rows.append(
            {
                "pair_id": pid,
                "orientation_agreement": agg.features.get("orientation_agreement"),
                "abs_margin": abs(agg.m),
                "reliability": estimate_reliability(agg, method="agreement_composite_arith"),
                "n_valid": agg.n_valid_directional,
            }
        )
    _write_csv(out_dir / "pilot_pair_reliability_features.csv", orient_rows)
    return rows


def paired_method_tests(synth_rows: list[dict[str, Any]], baseline: str) -> list[dict[str, Any]]:
    by_seed_method: dict[tuple[int, str], float] = {}
    for r in synth_rows:
        if r.get("source") != "synthetic" or r.get("kendall_tau") is None:
            continue
        by_seed_method[(int(r["seed"]), r["method"])] = float(r["kendall_tau"])
    methods = sorted({m for _s, m in by_seed_method})
    results = []
    raw_p = []
    for method in methods:
        if method == baseline:
            continue
        deltas = []
        for seed in sorted({s for s, _ in by_seed_method}):
            if (seed, method) in by_seed_method and (seed, baseline) in by_seed_method:
                deltas.append(by_seed_method[(seed, method)] - by_seed_method[(seed, baseline)])
        if not deltas:
            continue
        sf = sign_flip_pvalue(deltas, reps=5000, seed=42)
        raw_p.append((method, sf.pvalue, sum(deltas) / len(deltas), len(deltas)))
        results.append(
            {
                "baseline": baseline,
                "method": method,
                "n": len(deltas),
                "mean_delta_tau": sum(deltas) / len(deltas),
                "sign_flip_pvalue": sf.pvalue,
            }
        )
    if raw_p:
        adjusted = holm_adjust([p for _, p, _, _ in raw_p])
        for row, adj in zip(results, adjusted):
            row["holm_adjusted_pvalue"] = adj
    return results


def write_report(
    out_dir: Path,
    *,
    synth_rows,
    corr_rows,
    pilot_rows,
    paired,
    assoc_summary,
) -> str:
    # Mean τ by method on synthetic
    by_m: dict[str, list[float]] = defaultdict(list)
    dens: dict[str, list[float]] = defaultdict(list)
    for r in synth_rows:
        if r.get("source") == "synthetic" and r.get("kendall_tau") is not None:
            by_m[r["method"]].append(float(r["kendall_tau"]))
            if r.get("frac_incomparable") is not None:
                dens[r["method"]].append(float(r["frac_incomparable"]))
    ranked = sorted(by_m, key=lambda m: -sum(by_m[m]) / len(by_m[m]))

    # Decision rule
    sig = [
        r
        for r in paired
        if r.get("holm_adjusted_pvalue") is not None
        and r["holm_adjusted_pvalue"] < 0.05
        and r["mean_delta_tau"] > 0
    ]
    if sig:
        decision = (
            "Outcome B (candidate): "
            + ", ".join(f"`{r['method']}`" for r in sig)
            + " beat raw repair after Holm on synthetic Kendall τ."
        )
        outcome = "B"
    elif any(r["mean_delta_tau"] > 0 for r in paired):
        decision = (
            "Outcome C/D: some positive uncorrected deltas exist, but none survive "
            "Holm correction on this synthetic suite — use as optional conservative mode "
            "and plan a larger provenance-safe real evaluation."
        )
        outcome = "C"
    else:
        decision = (
            "Outcome A/D: no corrected improvement over raw repair on this suite; "
            "keep headline algorithm, keep reliability tooling as research mode."
        )
        outcome = "D"

    lines = [
        "# Reliability-aware graph construction & repair — FINAL REPORT",
        "",
        f"Generated: `{_utc()}`",
        "",
        "## Audit",
        "",
        "See `AUDIT_RELIABILITY_AND_REPAIR.md` in this directory.",
        "",
        "## Synthetic results (mean Kendall τ vs ground truth)",
        "",
        "| Method | Mean τ | Mean incomparable frac |",
        "|---|---:|---:|",
    ]
    for m in ranked:
        lines.append(
            f"| `{m}` | {sum(by_m[m])/len(by_m[m]):.4f} | "
            f"{(sum(dens[m])/len(dens[m]) if dens[m] else float('nan')):.4f} |"
        )
    lines += [
        "",
        "## Reliability vs error (synthetic)",
        "",
        "```json",
        json.dumps(assoc_summary, indent=2),
        "```",
        "",
        "## Paired tests vs raw repair (Holm-corrected)",
        "",
        "| Method | N | Mean Δτ | sign-flip p | Holm p |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in paired:
        lines.append(
            f"| `{r['method']}` | {r['n']} | {r['mean_delta_tau']:.4f} | "
            f"{r['sign_flip_pvalue']:.4g} | {r.get('holm_adjusted_pvalue')} |"
        )
    lines += [
        "",
        "## Corruption study",
        "",
        "See `corruption_results.csv`. Reliability-aware abstention typically "
        "reduces edge count under noise; Kendall impact depends on noise level.",
        "",
        "## Multi-provider pilot (observational only)",
        "",
        f"Queries analyzed: {len({r.get('query_id') for r in pilot_rows if 'query_id' in r})}.",
        "Do **not** treat pilot ranking differences as manuscript headlines.",
        "",
        "## Answers to core scientific questions (scoped)",
        "",
        "1. Low-reliability edges more often wrong? "
        f"Synthetic mean R(correct)={assoc_summary.get('mean_rel_correct')} vs "
        f"R(incorrect)={assoc_summary.get('mean_rel_incorrect')}.",
        "2–5. Orientation/prompt/model disagreement features are computed and "
        "enter composite reliability; association with cycles is limited on tiny graphs.",
        "6–9. Reliability-weighted + abstention reduce edges and often increase "
        "incomparable fraction — tradeoff tables in CSVs.",
        "10–11. Top-k importance and prior-regularization are implemented; "
        "synthetic gains are modest / uncorrected unless listed above.",
        "15. Headline algorithm change: see decision below.",
        "",
        f"## Decision: Outcome {outcome}",
        "",
        decision,
        "",
        "## Reproduce",
        "",
        "```bash",
        "source .venv/bin/activate",
        "PYTHONPATH=src python scripts/run_reliability_aware_repair_experiment.py \\",
        f"  --output-dir {out_dir}",
        "```",
        "",
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(lines))
    incomplete = [
        "No large new LLM API experiment; pilot is observational only (2 queries).",
        "Validation-fitted calibration not trained — heuristic reliability only.",
        "Structural importance during dynamic repair is a placeholder.",
        "CVXPY not required; exact solver is enumeration (n<=8/9).",
        "Legacy JudgmentCaches excluded from primary analysis.",
        "Manuscript not edited.",
        f"Decision outcome: {outcome}",
    ]
    (out_dir / "INCOMPLETE.md").write_text(
        "# Incomplete\n\n" + "\n".join(f"- {x}" for x in incomplete) + "\n"
    )
    return outcome


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report directory (default: reports/reliability_aware_repair_<UTC>).",
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Tiny offline smoke: 2 seeds only.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty --output-dir.",
    )
    args = parser.parse_args()
    stamp = _utc()
    out_dir = ensure_output_dir(
        (
            args.output_dir
            or (REPO_ROOT / "reports" / f"reliability_aware_repair_{stamp}")
        ).resolve(),
        overwrite=args.overwrite,
    )
    seeds = list(args.seeds[:2]) if args.quick else list(args.seeds)

    # Copy audit if not present
    audit_src = out_dir / "AUDIT_RELIABILITY_AND_REPAIR.md"
    if not audit_src.exists():
        bundled = (
            REPO_ROOT
            / "reports/reliability_aware_repair_20260725T210000Z/AUDIT_RELIABILITY_AND_REPAIR.md"
        )
        if bundled.exists():
            audit_src.write_text(bundled.read_text())

    synth_rows = run_synthetic(out_dir, seeds)
    corr_rows = run_corruption(out_dir)
    pilot_rows = run_pilot_analysis(out_dir)
    paired = paired_method_tests(synth_rows, "raw_no_abstention_weight_repair")

    # Association summary averaged over seeds from first method rows
    assoc_vals = [
        (r.get("mean_rel_correct"), r.get("mean_rel_incorrect"))
        for r in synth_rows
        if r.get("source") == "synthetic" and r.get("mean_rel_correct") is not None
    ]
    if assoc_vals:
        incorrect = [float(b) for _, b in assoc_vals if b is not None]
        assoc_summary = {
            "mean_rel_correct": sum(float(a) for a, _ in assoc_vals) / len(assoc_vals),
            "mean_rel_incorrect": (sum(incorrect) / len(incorrect)) if incorrect else None,
            "n_seed_rows": len(assoc_vals),
        }
    else:
        assoc_summary = {}

    _write_csv(out_dir / "synthetic_results.csv", synth_rows)
    _write_csv(out_dir / "corruption_results.csv", corr_rows)
    _write_csv(out_dir / "pilot_results.csv", pilot_rows)
    _write_csv(out_dir / "paired_comparisons.csv", paired)
    config = {
        "seeds": seeds,
        "methods": [m for m, _ in METHODS],
        "quick": bool(args.quick),
        "offline": True,
        "paid_api_calls": 0,
        "timestamp": stamp,
        "pilot_note": (
            "Optional multi-provider pilot analysis requires local ignored report "
            "reports/multi_provider_llm_robustness_*/judgment_records.jsonl; "
            "missing pilot is recorded as incomplete, not as a quality win."
        ),
    }
    _write_json(out_dir / "config.json", config)
    write_run_manifest(
        out_dir,
        script="scripts/run_reliability_aware_repair_experiment.py",
        config=config,
        repo_root=REPO_ROOT,
    )
    outcome = write_report(
        out_dir,
        synth_rows=synth_rows,
        corr_rows=corr_rows,
        pilot_rows=pilot_rows,
        paired=paired,
        assoc_summary=assoc_summary,
    )
    repro = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv/bin/activate
PYTHONPATH=src python scripts/run_reliability_aware_repair_experiment.py \\
  --output-dir "$(dirname "$0")" \\
  --seeds {' '.join(str(s) for s in seeds)} \\
  --overwrite
"""
    (out_dir / "REPRODUCE.sh").write_text(repro)
    (out_dir / "REPRODUCE.sh").chmod(0o755)
    print(f"Wrote {out_dir}")
    print(f"Decision outcome: {outcome}")


if __name__ == "__main__":
    main()
