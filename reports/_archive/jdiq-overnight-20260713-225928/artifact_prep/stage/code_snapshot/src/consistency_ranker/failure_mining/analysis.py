"""Failure labeling, aggregate tables, and summary generation."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

OUR_REPAIRED_METHOD = "markov_graph_repaired"
OUR_UNREPAIRED_METHOD = "markov_graph"

EXTERNAL_BASELINES = frozenset(
    {
        "prior_only",
        "rrf",
        "combsum",
        "borda_fuse",
        "score_sum",
        "borda",
        "pagerank",
        "rank_centrality",
        "bradley_terry",
        "local_kemenization",
        "bm25",
        "tfidf",
        "minilm",
    }
)


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def compute_failure_labels(
    method_metrics: dict[str, dict[str, Any]],
    *,
    our_method: str = OUR_REPAIRED_METHOD,
    our_unrepaired: str = OUR_UNREPAIRED_METHOD,
    primary_metric: str = "ndcg_at_k",
) -> dict[str, Any]:
    """Derive failure labels from per-method metrics for one query."""
    our_ndcg = _safe_float(method_metrics.get(our_method, {}).get(primary_metric))
    unrepaired_ndcg = _safe_float(method_metrics.get(our_unrepaired, {}).get(primary_metric))

    baseline_ndcgs: dict[str, float] = {}
    for name, m in method_metrics.items():
        if name in (our_method, our_unrepaired):
            continue
        val = _safe_float(m.get(primary_metric))
        if val is not None:
            baseline_ndcgs[name] = val

    prior_ndcg = _safe_float(method_metrics.get("prior_only", {}).get(primary_metric))

    def _loses_to(baseline: str) -> bool | None:
        b = baseline_ndcgs.get(baseline)
        if our_ndcg is None or b is None:
            return None
        return our_ndcg < b - 1e-9

    ranked_methods = sorted(
        ((n, v) for n, v in ((our_method, our_ndcg), *baseline_ndcgs.items()) if v is not None),
        key=lambda x: (-x[1], x[0]),
    )
    our_rank_position = next(
        (i + 1 for i, (n, _) in enumerate(ranked_methods) if n == our_method),
        None,
    )
    best_method = ranked_methods[0][0] if ranked_methods else None
    best_external = next(
        (n for n, _ in ranked_methods if n in EXTERNAL_BASELINES),
        None,
    )

    repair_harm = None
    repair_help = None
    repair_inactive = None
    if our_ndcg is not None and unrepaired_ndcg is not None:
        delta = our_ndcg - unrepaired_ndcg
        repair_harm = delta < -1e-9
        repair_help = delta > 1e-9
        repair_inactive = abs(delta) <= 1e-9

    best_baseline_ndcg = max(baseline_ndcgs.values()) if baseline_ndcgs else None
    loss_size = None
    if our_ndcg is not None and best_baseline_ndcg is not None:
        loss_size = best_baseline_ndcg - our_ndcg

    return {
        "loses_to_prior_only": _loses_to("prior_only"),
        "loses_to_score_sum": _loses_to("score_sum"),
        "loses_to_borda": _loses_to("borda"),
        "loses_to_rrf": _loses_to("rrf"),
        "loses_to_combsum": _loses_to("combsum"),
        "loses_to_borda_fuse": _loses_to("borda_fuse"),
        "loses_to_pagerank": _loses_to("pagerank"),
        "loses_to_rank_centrality": _loses_to("rank_centrality"),
        "loses_to_markov_graph": _loses_to("markov_graph"),
        "loses_to_bradley_terry": _loses_to("bradley_terry"),
        "loses_to_local_kemenization": _loses_to("local_kemenization"),
        "repair_harms_vs_unrepaired": repair_harm,
        "repair_helps_vs_unrepaired": repair_help,
        "repair_inactive_vs_unrepaired": repair_inactive,
        "loss_size_vs_best_baseline": loss_size,
        "our_method_rank_position": our_rank_position,
        "best_method": best_method,
        "best_external_baseline": best_external,
        "our_ndcg": our_ndcg,
        "prior_ndcg": prior_ndcg,
        "unrepaired_ndcg": unrepaired_ndcg,
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3 or len(ys) != n:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x <= 0 or den_y <= 0:
        return None
    return num / (den_x * den_y)


def write_aggregate_tables(output_dir: Path, records: list[dict]) -> None:
    """Write summary CSV tables from full query records."""
    if not records:
        return

    # Flat metrics rows
    metrics_rows: list[dict] = []
    for rec in records:
        qmeta = rec.get("query_metadata", {})
        fl = rec.get("failure_labels", {})
        gstats = rec.get("graph_stats", {})
        for method, m in rec.get("method_outputs", {}).items():
            metrics_rows.append(
                {
                    "dataset": qmeta.get("dataset"),
                    "vote_regime": qmeta.get("vote_regime"),
                    "query_id": qmeta.get("query_id"),
                    "method": method,
                    "ndcg_at_k": m.get("ndcg_at_k"),
                    "map_at_k": m.get("map_at_k"),
                    "mrr_at_k": m.get("mrr_at_k"),
                    "pairwise_accuracy": m.get("pairwise_accuracy"),
                    "kendall_tau": m.get("kendall_tau"),
                    "delta_vs_prior": m.get("delta_vs_prior"),
                    "delta_vs_unrepaired": m.get("delta_vs_unrepaired"),
                    "delta_vs_best_external": m.get("delta_vs_best_external"),
                    "largest_scc_size": gstats.get("largest_scc_size"),
                    "is_cyclic": gstats.get("is_cyclic"),
                    "fas_removed_weight": rec.get("repair_info", {}).get("fas_removed_weight"),
                    "loss_size": fl.get("loss_size_vs_best_baseline"),
                }
            )
    _write_csv(
        output_dir / "query_level_metrics.csv",
        metrics_rows,
        list(metrics_rows[0].keys()) if metrics_rows else ["dataset"],
    )

    # Top losses
    losses = [
        {
            "dataset": r["query_metadata"]["dataset"],
            "vote_regime": r["query_metadata"]["vote_regime"],
            "query_id": r["query_metadata"]["query_id"],
            "loss_size": r["failure_labels"].get("loss_size_vs_best_baseline"),
            "best_external_baseline": r["failure_labels"].get("best_external_baseline"),
            "our_ndcg": r["failure_labels"].get("our_ndcg"),
            "largest_scc_size": r["graph_stats"].get("largest_scc_size"),
            "is_cyclic": r["graph_stats"].get("is_cyclic"),
            "fas_removed_weight": r.get("repair_info", {}).get("fas_removed_weight"),
        }
        for r in records
        if r.get("failure_labels", {}).get("loss_size_vs_best_baseline") is not None
    ]
    losses.sort(key=lambda x: (-(x["loss_size"] or 0), x["query_id"]))
    _write_csv(
        output_dir / "table_failure_cases_top_losses.csv",
        losses[:200],
        [
            "dataset",
            "vote_regime",
            "query_id",
            "loss_size",
            "best_external_baseline",
            "our_ndcg",
            "largest_scc_size",
            "is_cyclic",
            "fas_removed_weight",
        ],
    )

    # Baseline win rates
    win_counts: dict[str, int] = defaultdict(int)
    loss_counts: dict[str, int] = defaultdict(int)
    for r in records:
        fl = r.get("failure_labels", {})
        for key, baseline in [
            ("loses_to_prior_only", "prior_only"),
            ("loses_to_score_sum", "score_sum"),
            ("loses_to_borda", "borda"),
            ("loses_to_rrf", "rrf"),
            ("loses_to_combsum", "combsum"),
            ("loses_to_pagerank", "pagerank"),
            ("loses_to_rank_centrality", "rank_centrality"),
            ("loses_to_bradley_terry", "bradley_terry"),
        ]:
            val = fl.get(key)
            if val is True:
                loss_counts[baseline] += 1
            elif val is False:
                win_counts[baseline] += 1
    baseline_rows = [
        {
            "baseline": b,
            "times_beat_our_method": loss_counts[b],
            "times_lost_to_our_method": win_counts[b],
            "win_rate_vs_our_method": (
                loss_counts[b] / (loss_counts[b] + win_counts[b])
                if (loss_counts[b] + win_counts[b]) > 0
                else None
            ),
        }
        for b in sorted(set(loss_counts) | set(win_counts))
    ]
    baseline_rows.sort(key=lambda x: -(x["times_beat_our_method"] or 0))
    _write_csv(
        output_dir / "table_baseline_win_rates.csv",
        baseline_rows,
        [
            "baseline",
            "times_beat_our_method",
            "times_lost_to_our_method",
            "win_rate_vs_our_method",
        ],
    )

    # Leaderboard by dataset
    by_ds_method: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in metrics_rows:
        if row.get("method") == OUR_REPAIRED_METHOD and row.get("ndcg_at_k") is not None:
            by_ds_method[(str(row["dataset"]), str(row["method"]))].append(float(row["ndcg_at_k"]))
        if row.get("ndcg_at_k") is not None:
            by_ds_method[(str(row["dataset"]), str(row["method"]))].append(float(row["ndcg_at_k"]))

    lb_rows: list[dict] = []
    datasets = sorted({str(r["query_metadata"]["dataset"]) for r in records})
    methods = sorted({m for _, m in by_ds_method})
    for ds in datasets:
        for method in methods:
            vals = [
                float(row["ndcg_at_k"])
                for row in metrics_rows
                if row.get("dataset") == ds and row.get("method") == method and row.get("ndcg_at_k") is not None
            ]
            if not vals:
                continue
            lb_rows.append(
                {
                    "dataset": ds,
                    "method": method,
                    "n_queries": len(vals),
                    "mean_ndcg_at_k": sum(vals) / len(vals),
                }
            )
    lb_rows.sort(key=lambda x: (x["dataset"], -x["mean_ndcg_at_k"]))
    _write_csv(
        output_dir / "table_method_leaderboard_by_dataset.csv",
        lb_rows,
        ["dataset", "method", "n_queries", "mean_ndcg_at_k"],
    )

    # Losses by graph regime
    regime_rows: list[dict] = []
    by_regime: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_regime[str(r["query_metadata"]["vote_regime"])].append(r)
    for regime, group in sorted(by_regime.items()):
        n = len(group)
        n_loss = sum(1 for r in group if (r["failure_labels"].get("loss_size_vs_best_baseline") or 0) > 0)
        n_harm = sum(1 for r in group if r["failure_labels"].get("repair_harms_vs_unrepaired") is True)
        n_help = sum(1 for r in group if r["failure_labels"].get("repair_helps_vs_unrepaired") is True)
        n_inactive = sum(1 for r in group if r["failure_labels"].get("repair_inactive_vs_unrepaired") is True)
        regime_rows.append(
            {
                "vote_regime": regime,
                "n_queries": n,
                "frac_queries_our_loses": n_loss / n if n else None,
                "frac_repair_harms": n_harm / n if n else None,
                "frac_repair_helps": n_help / n if n else None,
                "frac_repair_inactive": n_inactive / n if n else None,
            }
        )
    _write_csv(
        output_dir / "table_losses_by_graph_regime.csv",
        regime_rows,
        [
            "vote_regime",
            "n_queries",
            "frac_queries_our_loses",
            "frac_repair_harms",
            "frac_repair_helps",
            "frac_repair_inactive",
        ],
    )

    # Repair harm cases
    harm_rows = [
        {
            "dataset": r["query_metadata"]["dataset"],
            "vote_regime": r["query_metadata"]["vote_regime"],
            "query_id": r["query_metadata"]["query_id"],
            "our_ndcg": r["failure_labels"].get("our_ndcg"),
            "unrepaired_ndcg": r["failure_labels"].get("unrepaired_ndcg"),
            "delta": (r["failure_labels"].get("our_ndcg") or 0)
            - (r["failure_labels"].get("unrepaired_ndcg") or 0),
            "fas_removed_weight": r.get("repair_info", {}).get("fas_removed_weight"),
        }
        for r in records
        if r["failure_labels"].get("repair_harms_vs_unrepaired") is True
    ]
    harm_rows.sort(key=lambda x: x["delta"])
    _write_csv(
        output_dir / "table_repair_harm_cases.csv",
        harm_rows,
        [
            "dataset",
            "vote_regime",
            "query_id",
            "our_ndcg",
            "unrepaired_ndcg",
            "delta",
            "fas_removed_weight",
        ],
    )

    # Failure feature correlations
    loss_sizes = []
    cyclic = []
    scc_sizes = []
    fas_w = []
    prior_dom = []
    for r in records:
        ls = r["failure_labels"].get("loss_size_vs_best_baseline")
        if ls is None:
            continue
        loss_sizes.append(float(ls))
        cyclic.append(1.0 if r["graph_stats"].get("is_cyclic") else 0.0)
        scc_sizes.append(float(r["graph_stats"].get("largest_scc_size") or 0))
        fas_w.append(float(r.get("repair_info", {}).get("fas_removed_weight") or 0))
        prior_dom.append(float(r["graph_stats"].get("prior_top1_margin") or 0))

    feat_rows = [
        {"feature": "is_cyclic", "pearson_with_loss_size": _pearson(cyclic, loss_sizes)},
        {"feature": "largest_scc_size", "pearson_with_loss_size": _pearson(scc_sizes, loss_sizes)},
        {"feature": "fas_removed_weight", "pearson_with_loss_size": _pearson(fas_w, loss_sizes)},
        {"feature": "prior_top1_margin", "pearson_with_loss_size": _pearson(prior_dom, loss_sizes)},
    ]
    _write_csv(
        output_dir / "table_failure_features.csv",
        feat_rows,
        ["feature", "pearson_with_loss_size"],
    )


def build_summary_markdown(output_dir: Path, records: list[dict], run_meta: dict) -> str:
    """Build failure_mining_summary.md content."""
    n = len(records)
    if n == 0:
        body = "# Failure Mining Summary\n\nNo query records processed yet.\n"
        path = output_dir / "failure_mining_summary.md"
        path.write_text(body, encoding="utf-8")
        return body

    # Aggregate answers
    baseline_beats: dict[str, int] = defaultdict(int)
    ds_losses: dict[str, int] = defaultdict(int)
    regime_harm: dict[str, int] = defaultdict(int)
    regime_help: dict[str, int] = defaultdict(int)
    regime_inactive: dict[str, int] = defaultdict(int)

    loss_sizes: list[float] = []
    cyclic_flags: list[float] = []
    scc_sizes: list[float] = []
    fas_weights: list[float] = []
    prior_margins: list[float] = []

    for r in records:
        fl = r["failure_labels"]
        qm = r["query_metadata"]
        gs = r["graph_stats"]
        if (fl.get("loss_size_vs_best_baseline") or 0) > 0:
            ds_losses[qm["dataset"]] += 1
            best_ext = fl.get("best_external_baseline")
            if best_ext:
                baseline_beats[best_ext] += 1
        if fl.get("repair_harms_vs_unrepaired"):
            regime_harm[qm["vote_regime"]] += 1
        if fl.get("repair_helps_vs_unrepaired"):
            regime_help[qm["vote_regime"]] += 1
        if fl.get("repair_inactive_vs_unrepaired"):
            regime_inactive[qm["vote_regime"]] += 1
        ls = fl.get("loss_size_vs_best_baseline")
        if ls is not None:
            loss_sizes.append(float(ls))
            cyclic_flags.append(1.0 if gs.get("is_cyclic") else 0.0)
            scc_sizes.append(float(gs.get("largest_scc_size") or 0))
            fas_weights.append(float(r.get("repair_info", {}).get("fas_removed_weight") or 0))
            prior_margins.append(float(gs.get("prior_top1_margin") or 0))

    top_baselines = sorted(baseline_beats.items(), key=lambda x: -x[1])[:8]
    top_ds = sorted(ds_losses.items(), key=lambda x: -x[1])

    lines = [
        "# Failure Mining Summary",
        "",
        f"- Records processed: **{n}**",
        f"- Run status: **{run_meta.get('status', 'unknown')}**",
        f"- Output directory: `{output_dir}`",
        f"- Our method (repaired): `{OUR_REPAIRED_METHOD}`",
        f"- Our method (unrepaired): `{OUR_UNREPAIRED_METHOD}`",
        "",
        "## Which external baselines most often beat our method?",
        "",
    ]
    if top_baselines:
        for b, c in top_baselines:
            lines.append(f"- **{b}**: {c} query-level wins")
    else:
        lines.append("- No losses recorded yet.")

    lines += ["", "## In which datasets does our method lose most often?", ""]
    if top_ds:
        for ds, c in top_ds:
            lines.append(f"- **{ds}**: {c} queries with positive loss size")
    else:
        lines.append("- No dataset-level losses yet.")

    lines += ["", "## In which vote regimes does repair hurt?", ""]
    for regime in sorted(set(regime_harm) | set(regime_help) | set(regime_inactive)):
        lines.append(
            f"- **{regime}**: harm={regime_harm.get(regime, 0)}, "
            f"help={regime_help.get(regime, 0)}, inactive={regime_inactive.get(regime, 0)}"
        )

    lines += [
        "",
        "## Failure correlations (Pearson with loss size)",
        "",
        f"- Cyclicity: {_pearson(cyclic_flags, loss_sizes)}",
        f"- Largest SCC size: {_pearson(scc_sizes, loss_sizes)}",
        f"- FAS removed weight: {_pearson(fas_weights, loss_sizes)}",
        f"- Prior-score dominance (top1 margin): {_pearson(prior_margins, loss_sizes)}",
        "",
        "## Resume",
        "",
        "Re-run the same command with `--resume` to continue after interruption.",
        "",
        "## Run metadata",
        "",
        "```json",
        json.dumps(run_meta, indent=2),
        "```",
        "",
    ]
    body = "\n".join(lines)
    (output_dir / "failure_mining_summary.md").write_text(body, encoding="utf-8")
    return body
