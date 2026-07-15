"""Final report generation for repair selector overnight mining."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

THRESHOLDS = (0.0025, 0.005, 0.01)


def _count_positives(records: list[dict], threshold: float) -> int:
    keys: set[tuple[str, str]] = set()
    for rec in records:
        for pr in rec.get("repair_pair_results", []):
            if pr.get("repaired_method") != "markov_graph_repaired":
                continue
            gain = pr.get("repair_gain")
            if gain is not None and float(gain) >= threshold:
                keys.add((str(pr["dataset"]), str(pr["query_id"])))
    return len(keys)


def _split_records(records: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        split = rec.get("split_assignment") or rec.get("query_metadata", {}).get("split", "unknown")
        out[split].append(rec)
    return out


def _provider_from_record(rec: dict) -> str | None:
    for name in rec.get("method_outputs", {}):
        if name.startswith("llm_"):
            return name.replace("llm_", "").replace("_pairwise", "")
    return None


def classify_sufficiency(
    *,
    test_pos: dict[float, int],
    selector_results: dict[str, Any] | None,
    n_datasets: int,
    provider_concentration: float,
) -> str:
    targets_test = {0.0025: 15, 0.005: 10, 0.01: 5}
    if all(test_pos.get(t, 0) >= targets_test[t] for t in THRESHOLDS):
        if selector_results and n_datasets >= 3 and provider_concentration <= 0.6:
            best = selector_results.get("thresholds", {}).get("delta_ge_0.0100", {})
            models = best.get("models", [])
            never = next((m for m in models if m.get("model_name") == "never_repair"), None)
            always = next((m for m in models if m.get("model_name") == "always_repair"), None)
            learned = next(
                (m for m in models if m.get("model_name") not in ("never_repair", "always_repair", "heuristic_cyclic_scc")),
                None,
            )
            if never and learned and learned.get("mean_ndcg_at_10", 0) > never.get("mean_ndcg_at_10", 0):
                if learned.get("mean_ndcg_at_10", 0) >= always.get("mean_ndcg_at_10", 0):
                    return "SUFFICIENT_FOR_REPAIR_SELECTOR_CLAIM"
        return "PROMISING_BUT_NOT_YET_SUFFICIENT"
    if sum(test_pos.values()) == 0:
        return "INSUFFICIENT_REPAIR_OPPORTUNITY"
    return "PROMISING_BUT_NOT_YET_SUFFICIENT"


def write_all_reports(
    output_dir: Path,
    *,
    records: list[dict],
    run_meta: dict[str, Any],
    selector_results: dict[str, Any] | None,
    provider_statuses: list[dict],
    timed_out: bool = False,
) -> None:
    by_split = _split_records(records)
    train_val = by_split.get("train", []) + by_split.get("validation", [])
    test_recs = by_split.get("test", [])

    pos_all = {t: _count_positives(records, t) for t in THRESHOLDS}
    pos_train_val = {t: _count_positives(train_val, t) for t in THRESHOLDS}
    pos_test = {t: _count_positives(test_recs, t) for t in THRESHOLDS}

    ds_counts = Counter(r["query_metadata"]["dataset"] for r in records)
    provider_pos: Counter[str] = Counter()
    pair_pos: Counter[str] = Counter()
    for rec in records:
        prov = _provider_from_record(rec) or "non_llm"
        for pr in rec.get("repair_pair_results", []):
            gain = pr.get("repair_gain")
            if gain is not None and float(gain) >= 0.0025:
                provider_pos[prov] += 1
                pair_pos[f"{pr['repaired_method']} vs {pr['unrepaired_method']}"] += 1

    total_pos = sum(provider_pos.values()) or 1
    max_provider_frac = max(provider_pos.values()) / total_pos if provider_pos else 0.0

    if timed_out and sum(pos_test.values()) == 0:
        classification = "INCONCLUSIVE_DUE_TO_RUNTIME_OR_PROVIDER_FAILURE"
    else:
        classification = classify_sufficiency(
            test_pos=pos_test,
            selector_results=selector_results,
            n_datasets=len(ds_counts),
            provider_concentration=max_provider_frac,
        )

    # REPAIR_MINING_REPORT.md
    mining_lines = [
        "# Repair Mining Report",
        "",
        f"- Output: `{output_dir}`",
        f"- Status: {run_meta.get('status', 'unknown')}",
        f"- Total records: {len(records)}",
        f"- Unique queries: {len({(r['query_metadata']['dataset'], r['query_metadata']['query_id']) for r in records})}",
        "",
        "## Repair-positive counts (primary pair: markov_graph_repaired vs markov_graph)",
        "",
        "| Threshold | All | Train+Val | Locked Test |",
        "|-----------|-----|-----------|-------------|",
    ]
    for t in THRESHOLDS:
        mining_lines.append(f"| ΔNDCG@10 ≥ {t} | {pos_all[t]} | {pos_train_val[t]} | {pos_test[t]} |")
    mining_lines.extend(
        [
            "",
            "## Datasets",
            "",
            *[f"- {ds}: {n} records" for ds, n in sorted(ds_counts.items())],
            "",
            "## Provider availability",
            "",
            *[f"- {s['provider']}: available={s['available']} ({s.get('reason', '')})" for s in provider_statuses],
            "",
        ]
    )
    (output_dir / "REPAIR_MINING_REPORT.md").write_text("\n".join(mining_lines), encoding="utf-8")

    # REPAIR_SELECTOR_REPORT.md
    sel_lines = [
        "# Repair Selector Report",
        "",
        "Primary label: `repair_gain = NDCG@10(repaired) - NDCG@10(unrepaired)` for matched pairs.",
        "",
    ]
    if selector_results:
        for tkey, block in selector_results.get("thresholds", {}).items():
            sel_lines.append(f"## {tkey}")
            sel_lines.append("")
            sel_lines.append(
                f"- Positives train/val/eval: {block.get('positive_train')} / "
                f"{block.get('positive_val')} / {block.get('positive_eval')}"
            )
            sel_lines.append(f"- Best model: `{block.get('best_model')}`")
            sel_lines.append("")
            for m in block.get("models", [])[:6]:
                sel_lines.append(
                    f"- {m.get('model_name')}: mean NDCG@10={m.get('mean_ndcg_at_10')}, "
                    f"F1={m.get('f1')}, override_rate={m.get('override_rate')}"
                )
            sel_lines.append("")
    else:
        sel_lines.append("Selector training not yet run or insufficient data.")
    (output_dir / "REPAIR_SELECTOR_REPORT.md").write_text("\n".join(sel_lines), encoding="utf-8")

    # DATA_SUFFICIENCY_REPORT.md
    suff_lines = [
        "# Data Sufficiency Report",
        "",
        f"**Classification: {classification}**",
        "",
        "## Counts",
        "",
        f"- Unique queries added this run: {run_meta.get('n_new_queries', 'unknown')}",
        f"- Meaningful repair-positive (Δ≥0.0025) train+val: {pos_train_val[0.0025]}",
        f"- Meaningful repair-positive (Δ≥0.005) train+val: {pos_train_val[0.005]}",
        f"- Meaningful repair-positive (Δ≥0.01) train+val: {pos_train_val[0.01]}",
        f"- Locked test positives Δ≥0.0025/0.005/0.01: {pos_test[0.0025]}/{pos_test[0.005]}/{pos_test[0.01]}",
        f"- Datasets represented: {len(ds_counts)} ({', '.join(sorted(ds_counts))})",
        f"- Providers with positives: {len(provider_pos)}",
        f"- Max provider share of positives: {max_provider_frac:.1%}",
        "",
        "## Repair pairs generating positives (Δ≥0.0025)",
        "",
        *[f"- {pair}: {cnt}" for pair, cnt in pair_pos.most_common()],
        "",
        "## Key questions",
        "",
    ]
    if selector_results:
        block = selector_results.get("thresholds", {}).get("delta_ge_0.0100", {})
        models = {m["model_name"]: m for m in block.get("models", [])}
        never = models.get("never_repair", {})
        always = models.get("always_repair", {})
        heur = models.get("heuristic_cyclic_scc", {})
        learned = next((m for n, m in models.items() if n not in ("never_repair", "always_repair", "heuristic_cyclic_scc")), {})
        suff_lines.extend(
            [
                f"- Does learned selector beat never-repair? "
                f"{'Yes' if learned.get('mean_ndcg_at_10', 0) > never.get('mean_ndcg_at_10', 0) else 'No'}",
                f"- Does learned selector beat always-repair? "
                f"{'Yes' if learned.get('mean_ndcg_at_10', 0) > always.get('mean_ndcg_at_10', 0) else 'No'}",
                f"- Does learned selector beat best fixed heuristic? "
                f"{'Yes' if learned.get('mean_ndcg_at_10', 0) > heur.get('mean_ndcg_at_10', 0) else 'No'}",
                f"- Statistical CI (best learned): [{learned.get('ndcg_ci_95_lo')}, {learned.get('ndcg_ci_95_hi')}]",
            ]
        )
    else:
        suff_lines.append("- Selector evaluation pending.")
    suff_lines.extend(
        [
            "",
            f"- Is dataset sufficient for manuscript claim? **{classification}**",
            "",
            "## Targets (aspirational)",
            "",
            "- Train+val: 50/35/20 positives at 0.0025/0.005/0.01",
            "- Locked test: 15/10/5 positives at same thresholds",
            "",
        ]
    )
    (output_dir / "DATA_SUFFICIENCY_REPORT.md").write_text("\n".join(suff_lines), encoding="utf-8")

    # FAILURE_AND_LIMITATIONS.md
    fail_lines = [
        "# Failure and Limitations",
        "",
        f"- Timed out: {timed_out}",
        f"- Exact ILP solver available: {run_meta.get('ilp_available', False)}",
        "",
        "## Provider failures",
        "",
        *[f"- {s['provider']}: {s.get('reason', '')}" for s in provider_statuses if not s.get("available")],
        "",
        "## Known limitations",
        "",
        "- Primary repair pair uses greedy MWFAS; exact repair only on small graphs.",
        "- Metric-aware repair stored separately; not mixed into primary label.",
        "- Test split locked before outcome inspection; no test-driven mining.",
        "- Sufficiency requires held-out positives, selector utility, and transfer — not count alone.",
        "",
    ]
    (output_dir / "FAILURE_AND_LIMITATIONS.md").write_text("\n".join(fail_lines), encoding="utf-8")

    # NEXT_STEPS.md
    next_lines = [
        "# Next Steps",
        "",
    ]
    if classification != "SUFFICIENT_FOR_REPAIR_SELECTOR_CLAIM":
        next_lines.extend(
            [
                "1. Continue active mining on high-cycle / high-disagreement queries.",
                "2. Expand provider diversity (ensure no single provider >60% of positives).",
                "3. Target additional datasets and vote regimes (ms2, ms1_drop_mutual).",
                "4. Collect more locked-test repair positives before claiming sufficiency.",
                "5. Run leave-one-dataset-out evaluation once per-dataset N≥15.",
            ]
        )
    else:
        next_lines.append("1. Proceed to manuscript-grade selector evaluation and ablations.")
    (output_dir / "NEXT_STEPS.md").write_text("\n".join(next_lines), encoding="utf-8")

    run_meta["sufficiency_classification"] = classification
    run_meta["positive_counts"] = {"all": pos_all, "train_val": pos_train_val, "test": pos_test}
    (output_dir / "run_manifest.json").write_text(json.dumps(run_meta, indent=2, default=str), encoding="utf-8")
