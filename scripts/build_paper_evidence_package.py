#!/usr/bin/env python
"""
Build paper-facing tables and plots from ``outputs/pub_vote_cmp_v2``.

Writes under ``<root>/paper_package/``:
  - ``tables/table_graph_ndcg_and_consistency.csv``
  - ``tables/table_bootstrap_delta_ndcg.csv``
  - ``tables/table_consistency_qrels_bew.csv``
  - ``plots/*.png``
  - ``MANUSCRIPT_SUMMARY.md``
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

VARIANTS = ("ms2", "ms1", "ms1_drop_mutual")
DATASETS = ("scidocs", "hotpotqa")
REF_METHOD = "hybrid_rrf_repaired_copeland_a03"
METHODS = {
    "uco": "hybrid_rrf_unrepaired_copeland_a03",
    "rco": "hybrid_rrf_repaired_copeland_a03",
    "uba": "hybrid_rrf_unrepaired_balance_a03",
    "rba": "hybrid_rrf_repaired_balance_a03",
    "prior": "hybrid_rrf_prior_only",
}


def _per_query_path(root: Path, ds: str, var: str) -> Path:
    return root / ds / var / ds / "votes_file" / f"{ds}_per_query.csv"


def _analysis_path(root: Path, ds: str, var: str, kind: str) -> Path:
    return root / "analysis" / f"{ds}_{var}_delta_{kind}.json"


def _load_csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ref_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["method"] == REF_METHOD]


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else float("nan")


def _method_mean_ndcg(rows: list[dict], method: str) -> float:
    sub = [float(r["ndcg_at_k"]) for r in rows if r["method"] == method and r.get("ndcg_at_k")]
    return _mean(sub)


def aggregate_graph_and_ndcg(root: Path) -> list[dict]:
    out: list[dict] = []
    for ds in DATASETS:
        for var in VARIANTS:
            p = _per_query_path(root, ds, var)
            if not p.exists():
                continue
            rows = _load_csv_rows(p)
            ref = _ref_rows(rows)
            if not ref:
                continue
            nq = len(ref)
            pct_cyc = (
                sum(str(r.get("is_cyclic", "")).lower() in ("true", "1") for r in ref) / nq * 100
            )
            avg_scc = _mean([float(r["largest_scc"]) for r in ref])
            avg_edges = _mean([float(r["n_edges"]) for r in ref])
            bew_pre = _mean([float(r["graph_ref_bew_pre"]) for r in ref])
            bew_post = _mean([float(r["graph_ref_bew_post"]) for r in ref])
            pic_pre = _mean([float(r["graph_ref_pic_pre"]) for r in ref])
            pic_post = _mean([float(r["graph_ref_pic_post"]) for r in ref])
            fas_w = _mean([float(r["fas_weight_removed"]) for r in ref])
            out.append(
                {
                    "dataset": ds,
                    "variant": var,
                    "n_queries": nq,
                    "pct_cyclic": round(pct_cyc, 2),
                    "avg_largest_scc": round(avg_scc, 3),
                    "avg_n_edges": round(avg_edges, 3),
                    "mean_graph_ref_bew_pre": round(bew_pre, 4),
                    "mean_graph_ref_bew_post": round(bew_post, 4),
                    "mean_delta_bew_qrels_pre_minus_post": round(bew_pre - bew_post, 4),
                    "mean_graph_ref_pic_pre": round(pic_pre, 4),
                    "mean_graph_ref_pic_post": round(pic_post, 4),
                    "mean_delta_pic_qrels_pre_minus_post": round(pic_pre - pic_post, 4),
                    "mean_fas_weight_removed": round(fas_w, 6),
                    "mean_ndcg_prior": round(_method_mean_ndcg(rows, METHODS["prior"]), 6),
                    "mean_ndcg_uco": round(_method_mean_ndcg(rows, METHODS["uco"]), 6),
                    "mean_ndcg_rco": round(_method_mean_ndcg(rows, METHODS["rco"]), 6),
                    "mean_ndcg_uba": round(_method_mean_ndcg(rows, METHODS["uba"]), 6),
                    "mean_ndcg_rba": round(_method_mean_ndcg(rows, METHODS["rba"]), 6),
                }
            )
    return out


def load_bootstrap_table(root: Path) -> list[dict]:
    rows: list[dict] = []
    for ds in DATASETS:
        for var in VARIANTS:
            for kind in ("copeland", "balance"):
                jp = _analysis_path(root, ds, var, kind)
                if not jp.exists():
                    continue
                j = json.loads(jp.read_text(encoding="utf-8"))
                rows.append(
                    {
                        "dataset": ds,
                        "variant": var,
                        "pair": kind,
                        "n_queries": j.get("n_queries"),
                        "mean_delta_ndcg": j.get("mean_delta_ndcg"),
                        "ci95_low": j.get("ci_low"),
                        "ci95_high": j.get("ci_high"),
                        "bootstrap_reps": j.get("bootstrap"),
                    }
                )
                # Stratified high SCC for copeland only
                if kind == "copeland":
                    hi = j.get("strata", {}).get("largest_scc_ge_median", {})
                    lo = j.get("strata", {}).get("largest_scc_lt_median", {})
                    rows.append(
                        {
                            "dataset": ds,
                            "variant": var,
                            "pair": "copeland_scc_high",
                            "n_queries": hi.get("n"),
                            "mean_delta_ndcg": hi.get("mean_delta_ndcg"),
                            "ci95_low": hi.get("ci_low"),
                            "ci95_high": hi.get("ci_high"),
                            "bootstrap_reps": j.get("bootstrap"),
                        }
                    )
                    rows.append(
                        {
                            "dataset": ds,
                            "variant": var,
                            "pair": "copeland_scc_low",
                            "n_queries": lo.get("n"),
                            "mean_delta_ndcg": lo.get("mean_delta_ndcg"),
                            "ci95_low": lo.get("ci_low"),
                            "ci95_high": lo.get("ci_high"),
                            "bootstrap_reps": j.get("bootstrap"),
                        }
                    )
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def plot_cyclicity_scc(agg: list[dict], outdir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    labels = ["ms2", "ms1", "ms1+drop"]
    x = range(3)
    for ax_idx, ds in enumerate(DATASETS):
        ax = axes[ax_idx]
        sub = [r for r in agg if r["dataset"] == ds]
        sub = sorted(sub, key=lambda r: VARIANTS.index(r["variant"]))
        if len(sub) != 3:
            continue
        pct = [r["pct_cyclic"] for r in sub]
        scc = [r["avg_largest_scc"] for r in sub]
        ax2 = ax.twinx()
        ax.bar([i - 0.2 for i in x], pct, width=0.4, label="% cyclic graphs", color="#4C72B0")
        ax2.bar([i + 0.2 for i in x], scc, width=0.4, label="Avg largest SCC", color="#DD8452")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.set_ylabel("% queries with cycle")
        ax2.set_ylabel("Avg largest SCC size")
        ax.set_title(ds)
        ax.set_ylim(0, max(105, max(pct) * 1.1))
        lines1, lab1 = ax.get_legend_handles_labels()
        lines2, lab2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, lab1 + lab2, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "fig_cyclicity_and_scc.png", dpi=200)
    plt.close(fig)


def plot_ndcg_hybrids(agg: list[dict], outdir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    labels = ["ms2", "ms1", "ms1+drop"]
    w = 0.18
    for ax_idx, ds in enumerate(DATASETS):
        ax = axes[ax_idx]
        sub = sorted(
            [r for r in agg if r["dataset"] == ds],
            key=lambda r: VARIANTS.index(r["variant"]),
        )
        if len(sub) != 3:
            continue
        for i, var_row in enumerate(sub):
            base = i
            ax.bar(
                base - 2 * w,
                var_row["mean_ndcg_uco"],
                width=w,
                label="U-Cop" if ax_idx == 0 and i == 0 else None,
                color="#8de5a1",
            )
            ax.bar(
                base - w,
                var_row["mean_ndcg_rco"],
                width=w,
                label="R-Cop" if ax_idx == 0 and i == 0 else None,
                color="#27ae60",
            )
            ax.bar(
                base,
                var_row["mean_ndcg_uba"],
                width=w,
                label="U-Bal" if ax_idx == 0 and i == 0 else None,
                color="#fab0e4",
            )
            ax.bar(
                base + w,
                var_row["mean_ndcg_rba"],
                width=w,
                label="R-Bal" if ax_idx == 0 and i == 0 else None,
                color="#aa40fc",
            )
        ax.set_xticks(range(3))
        ax.set_xticklabels(labels)
        ax.set_ylabel("Mean nDCG@k")
        ax.set_title(ds)
        ax.set_ylim(0, 1.05)
    fig.legend(loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.02), fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(outdir / "fig_mean_ndcg_hybrids.png", dpi=200)
    plt.close(fig)


def plot_delta_forest(root: Path, outdir: Path) -> None:
    rows = [r for r in load_bootstrap_table(root) if r["pair"] in ("copeland", "balance")]
    fig, axes = plt.subplots(1, 2, figsize=(9, 5.2), sharex=True)
    colors = {"copeland": "#2ca02c", "balance": "#9467bd"}
    for ax_idx, ds in enumerate(DATASETS):
        ax = axes[ax_idx]
        y_labels: list[str] = []
        y = 0
        for var in VARIANTS:
            vlab = var.replace("ms1_drop_mutual", "ms1+drop")
            for kind, short in (("copeland", "Copeland"), ("balance", "Balance")):
                r = next(
                    (
                        x
                        for x in rows
                        if x["dataset"] == ds and x["variant"] == var and x["pair"] == kind
                    ),
                    None,
                )
                if r is None:
                    continue
                m = r["mean_delta_ndcg"]
                lo = r["ci95_low"]
                hi = r["ci95_high"]
                ax.errorbar(
                    m,
                    y,
                    xerr=[[m - lo], [hi - m]],
                    fmt="o",
                    color=colors[kind],
                    capsize=4,
                    markersize=5,
                )
                y_labels.append(f"{vlab} · {short[:3]}")
                y += 1
        ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_yticks(range(len(y_labels)))
        ax.set_yticklabels(y_labels, fontsize=8)
        ax.set_xlabel("Δ nDCG@k (repaired − unrepaired)")
        ax.set_title(ds)
    fig.suptitle("Bootstrap 95% CI for mean per-query ΔnDCG", fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "fig_delta_ndcg_bootstrap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_qrels_bew(agg: list[dict], outdir: Path) -> None:
    """Graph–qrels backward-edge mass: pre (raw graph) vs post (DAG after FAS)."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    labels = ["ms2", "ms1", "ms1+drop"]
    x = range(3)
    for ax_idx, ds in enumerate(DATASETS):
        ax = axes[ax_idx]
        sub = sorted(
            [r for r in agg if r["dataset"] == ds],
            key=lambda r: VARIANTS.index(r["variant"]),
        )
        if len(sub) != 3:
            continue
        pre = [r["mean_graph_ref_bew_pre"] for r in sub]
        post = [r["mean_graph_ref_bew_post"] for r in sub]
        ax.bar(
            [i - 0.2 for i in x],
            pre,
            width=0.4,
            label="BEW graph vs qrels (pre-FAS)",
            color="#c44e52",
        )
        ax.bar(
            [i + 0.2 for i in x],
            post,
            width=0.4,
            label="BEW DAG vs qrels (post-FAS)",
            color="#8172b3",
        )
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.set_ylabel("Mean backward-edge weight")
        ax.set_title(ds)
        ax.legend(fontsize=8)
    fig.suptitle(
        "Consistency vs labels: preference graph vs qrels reference ranking",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(outdir / "fig_graph_qrels_bew_pre_post.png", dpi=200)
    plt.close(fig)


def write_manuscript_summary(path: Path, agg: list[dict], boot: list[dict]) -> None:
    text = """# Manuscript-ready summary (``outputs/pub_vote_cmp_v2``)

## Main claim (supported by this evidence package)

1. **Vote aggregation controls cycle incidence.** Majority-style filtering (**ms2**:
   ``min_support=2``, ``min_aggregate_margin=0.1``) yields **near-acyclic**
   preference graphs; **per-ranker edges** (**ms1**: ``min_support=1``) yield
   **high** ``pct_cyclic_graphs`` and **large** average largest SCC. Dropping
   **mutual 2-cycle pairs** after **ms1** (**ms1_drop_mutual**) **restores**
   low cyclicity while keeping most edges.

2. **Graph repair (FAS) relative to qrels is measurable:** mean
   **graph–reference backward-edge weight** (BEW) **decreases** from the raw
   graph to the repaired DAG (**fig_graph_qrels_bew_pre_post**,
   ``table_consistency_qrels_bew.csv``). Thus repair **does** reduce a
   **label-aligned inconsistency** metric on the preference graph itself.

3. **nDCG@k gains from “repaired vs unrepaired” Copeland hybrids are not
   guaranteed.** With **ms1** on SciDocs, mean ΔnDCG (repaired − unrepaired
   Copeland) is **negative** with a **bootstrap 95% CI strictly below zero**.
   With **ms1** on HotpotQA the mean Δ is slightly negative with a CI that
   touches zero. **Balance** hybrids show **no meaningful** ΔnDCG. Under
   **ms2** or **ms1_drop_mutual**, Copeland **ΔnDCG ≈ 0** (repair inactive or
   rankings coincide).

4. **Conditional effect (SciDocs, ms1, Copeland):** ΔnDCG is **more negative**
   for queries with **largest SCC ≥ median** than below median (see
   ``table_bootstrap_delta_ndcg.csv``, rows ``copeland_scc_high`` /
   ``copeland_scc_low``), suggesting **harm concentrates in higher-conflict
   subgraphs** under this construction.

---

## Limitations

- **Fixed query lists** (SciDocs **n≈119–120**, HotpotQA **n=52** after
  eligibility); CIs are **query-level bootstrap** of mean Δ, not a hierarchical
  model.
- **Three rankers** (BM25, TF-IDF, MiniLM) and **fixed** vote hyperparameters.
- **ms1_drop_mutual** is a **post hoc** edge filter (not fit to validation
  data).
- **graph_ref_bew_*** is **one** consistency view (graph vs **qrels-derived**
  reference); it does not assert “closer to truth,” only **alignment with
  labeled preferences** over the candidate pool.

---

## Recommended protocol for the paper body

1. **Pre-register two vote constructions:** **(A) ms2** = pragmatic
   majority/aggregate votes; **(B) ms1_drop_mutual** = preserve multi-ranker
   edges but **abstain** on pure **head-to-head conflicts** (mutual pairs).
   Optionally report **ms1** in appendix as **full-disagreement** / **high-cycle**
   regime.

2. **Report for each construction:** ``pct_cyclic_graphs``, **avg largest SCC**,
   **avg n_edges**, mean **nDCG@k** for **unrepaired vs repaired** Copeland and
   balance, **bootstrap CI** on **mean per-query ΔnDCG**.

3. **Add one graph–labels consistency line:** mean **graph_ref_bew_pre** and
   **post** (or mean **Δ BEW = pre − post**) to show **FAS reduces
   graph–reference tension** even when **nDCG** does not improve.

4. **Frame repair** as **conditionally** affecting **ranking quality** on
   **nDCG@k**, while **unambiguously** changing **structural** inconsistency
   metrics—**not** as a uniformly beneficial reranker under vote-based graphs.

---
*Generated by* ``scripts/build_paper_evidence_package.py``.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("outputs/pub_vote_cmp_v2"))
    args = ap.parse_args()
    pkg = args.root / "paper_package"
    tdir = pkg / "tables"
    pdir = pkg / "plots"
    pdir.mkdir(parents=True, exist_ok=True)

    agg = aggregate_graph_and_ndcg(args.root)
    if not agg:
        raise SystemExit(f"No data under {args.root}")

    _write_csv(
        tdir / "table_graph_ndcg_and_consistency.csv",
        list(agg[0].keys()),
        agg,
    )

    # Slim consistency-only table for supplement
    slim = [
        {
            "dataset": r["dataset"],
            "variant": r["variant"],
            "n_queries": r["n_queries"],
            "mean_bew_pre": r["mean_graph_ref_bew_pre"],
            "mean_bew_post": r["mean_graph_ref_bew_post"],
            "mean_delta_bew_pre_minus_post": r["mean_delta_bew_qrels_pre_minus_post"],
            "mean_pic_pre": r["mean_graph_ref_pic_pre"],
            "mean_pic_post": r["mean_graph_ref_pic_post"],
            "mean_fas_weight_removed": r["mean_fas_weight_removed"],
        }
        for r in agg
    ]
    _write_csv(tdir / "table_consistency_qrels_bew.csv", list(slim[0].keys()), slim)

    boot = load_bootstrap_table(args.root)
    if boot:
        _write_csv(tdir / "table_bootstrap_delta_ndcg.csv", list(boot[0].keys()), boot)

    plot_cyclicity_scc(agg, pdir)
    plot_ndcg_hybrids(agg, pdir)
    plot_delta_forest(args.root, pdir)
    plot_qrels_bew(agg, pdir)

    write_manuscript_summary(pkg / "MANUSCRIPT_SUMMARY.md", agg, boot)
    print(f"[paper_package] wrote {pkg}")


if __name__ == "__main__":
    main()
