#!/usr/bin/env python
"""
First metric-aware FAS experiment (SciDocs, ms1 votes only).

Compares plain vs metric-aware **repaired Copeland** hybrids against unrepaired
Copeland and prior-only, using existing ``votes_file`` + score priors from a
publication-style tree (e.g. ``outputs/pub_vote_cmp_all4/scidocs``).

Edge reweighting (training-free) follows ``metric_aware_repair.py``::

    w_new = w_conf * (1 + beta * u)

with ``u ≈ |gain_i - gain_j| · |d(pos_i) - d(pos_j)|``, ``d(pos)=1/log2(pos+1)``
(1-based ranks from the prior), optional tail down-weighting via
``--metric-aware-top-k``.

Does not modify the publication suite; writes under ``outputs/metric_aware_first/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

DEFAULT_OUTPUT_ROOT = _REPO / "outputs" / "metric_aware_first" / "scidocs_ms1"
INPUT_CANDIDATES = [
    _REPO / "outputs" / "pub_vote_cmp_all4" / "scidocs",
    _REPO / "outputs" / "pub_vote_cmp_v2" / "scidocs",
]

METHODS_COP = [
    "hybrid_rrf_prior_only",
    "hybrid_rrf_unrepaired_copeland_a03",
    "hybrid_rrf_repaired_copeland_a03",
]

METHOD_PRIOR = "hybrid_rrf_prior_only"
METHOD_UNREPAIRED = "hybrid_rrf_unrepaired_copeland_a03"
METHOD_REPAIRED = "hybrid_rrf_repaired_copeland_a03"

BETAS = (0.25, 0.5, 1.0, 2.0)
FOCUS_TOP_KS = (10, 20)

# Publication trees usually ship BM25 + TF-IDF + MiniLM; MiniLM may be absent on some clusters.
SCORE_PRIOR_FILENAMES = (
    "scores_bm25.jsonl",
    "scores_tfidf.jsonl",
    "scores_minilm.jsonl",
)


def _score_prior_paths(root: Path) -> list[Path]:
    return [root / name for name in SCORE_PRIOR_FILENAMES if (root / name).exists()]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for this experiment (sweep subdirs + reports).",
    )
    p.add_argument(
        "--inputs-root",
        type=Path,
        default=None,
        help=(
            "Directory with query_ids.txt, votes_ms1.jsonl, and at least one of "
            "scores_bm25.jsonl / scores_tfidf.jsonl / scores_minilm.jsonl (all three preferred). "
            "If omitted, picks the best match under pub_vote_cmp_all4/v2 scidocs."
        ),
    )
    p.add_argument(
        "--graph-top-k",
        type=int,
        default=20,
        help="Candidate / preference graph top-k (match publication SciDocs default).",
    )
    p.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Cap queries (default: all ids in query_ids.txt).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed passed to run_real_experiment.",
    )
    p.add_argument(
        "--include-balance",
        action="store_true",
        help="Also run hybrid balance ablations (wider method list).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only; do not execute run_real_experiment.",
    )
    return p.parse_args(argv)


def _discover_inputs(explicit: Path | None) -> Path:
    """Resolve SciDocs ms1 directory; prefers a tree with all three score priors when available."""
    if explicit is not None:
        root = explicit.resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"--inputs-root is not a directory: {root}")
    else:
        ranked: list[tuple[tuple[int, int, int], Path]] = []
        for i, c in enumerate(INPUT_CANDIDATES):
            if not (c / "votes_ms1.jsonl").exists():
                continue
            n = len(_score_prior_paths(c))
            if n == 0:
                continue
            # Prefer full BM25+TF-IDF+MiniLM, then more files, then earlier candidate.
            key = (-(n == len(SCORE_PRIOR_FILENAMES)), -n, i)
            ranked.append((key, c.resolve()))
        if not ranked:
            searched = ", ".join(str(c) for c in INPUT_CANDIDATES)
            raise FileNotFoundError(
                "Could not find SciDocs ms1 inputs. Expected votes_ms1.jsonl and at least one "
                f"of {list(SCORE_PRIOR_FILENAMES)} under one of:\n"
                f"  {searched}\n"
                "Run scripts/run_publication_vote_suite.py for scidocs, or pass --inputs-root."
            )
        ranked.sort(key=lambda t: t[0])
        root = ranked[0][1]

    core = [root / "query_ids.txt", root / "votes_ms1.jsonl"]
    missing_core = [p for p in core if not p.exists()]
    if missing_core:
        raise FileNotFoundError(
            "Missing required input files:\n  "
            + "\n  ".join(str(m) for m in missing_core)
            + f"\n\nUnder inputs root: {root}"
        )
    scores = _score_prior_paths(root)
    if not scores:
        raise FileNotFoundError(
            f"No score prior JSONL found under {root}. Expected at least one of: "
            f"{list(SCORE_PRIOR_FILENAMES)}"
        )
    return root


def _count_query_ids(path: Path) -> int:
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(_REPO), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _run_real_cmd(
    *,
    output_subdir: Path,
    repair_weighting: str,
    metric_aware_beta: float,
    metric_aware_top_k: int | None,
    inputs_root: Path,
    max_queries: int,
    graph_top_k: int,
    seed: int,
    methods: list[str],
    score_prior_files: list[Path],
    dry_run: bool,
) -> None:
    py = sys.executable
    cmd = [
        py,
        str(_REPO / "scripts" / "run_real_experiment.py"),
        "--dataset",
        "scidocs",
        "--preference-source",
        "votes_file",
        "--pairwise-file",
        str(inputs_root / "votes_ms1.jsonl"),
        "--query-id-file",
        str(inputs_root / "query_ids.txt"),
        "--score-prior-files",
        *[str(p) for p in score_prior_files],
        "--max-queries",
        str(max_queries),
        "--top-k",
        str(graph_top_k),
        "--include-hybrid-ablation",
        "--methods",
        *methods,
        "--repair-weighting",
        repair_weighting,
        "--metric-aware-beta",
        str(metric_aware_beta),
        "--metric-aware-gain-source",
        "prior_score",
        "--save-timings",
        "--no-plots",
        "--overwrite-existing",
        "--output-dir",
        str(output_subdir),
        "--seed",
        str(seed),
    ]
    if metric_aware_top_k is not None:
        cmd.extend(["--metric-aware-top-k", str(metric_aware_top_k)])
    print(">>", " ".join(cmd), flush=True)
    if dry_run:
        return
    r = subprocess.run(cmd, cwd=_REPO)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def _per_query_path(run_dir: Path) -> Path:
    return run_dir / "scidocs" / "votes_file" / "scidocs_per_query.csv"


def _read_per_query(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _float_or_none(x: str) -> float | None:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _aggregate_and_report(
    *,
    output_root: Path,
    rows: list[dict],
    dry_run: bool,
    inputs_note: str = "",
) -> None:
    if dry_run or not rows:
        return

    # Combined per-query (all runs)
    comb_path = output_root / "all_per_query.csv"
    comb_path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    with comb_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    # Summary: mean nDCG by (sweep_name, method)
    stats: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        ndcg = _float_or_none(r.get("ndcg_at_k", ""))
        if ndcg is None:
            continue
        stats[(r["sweep_name"], r["method"])].append(ndcg)

    summary_rows: list[dict] = []
    for (sweep_name, method), vals in sorted(stats.items()):
        exemplar = next(
            x for x in rows if x["sweep_name"] == sweep_name and x["method"] == method
        )
        if sweep_name == "plain_baseline":
            beta_disp = ""
            focus_disp = ""
        else:
            beta_disp = exemplar.get("metric_aware_beta", "")
            focus_disp = exemplar.get("metric_aware_focus_top_k", "")
        summary_rows.append(
            {
                "sweep_name": sweep_name,
                "repair_weighting": exemplar.get("repair_weighting", ""),
                "metric_aware_beta": beta_disp,
                "metric_aware_focus_top_k": focus_disp,
                "method": method,
                "n_queries": len(vals),
                "mean_ndcg_at_k": sum(vals) / len(vals),
            }
        )
    summary_path = output_root / "summary_by_setting.csv"
    cmp_path = output_root / "comparison_key_metrics.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as fh:
        cols = [
            "sweep_name",
            "repair_weighting",
            "metric_aware_beta",
            "metric_aware_focus_top_k",
            "method",
            "n_queries",
            "mean_ndcg_at_k",
        ]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(summary_rows)

    # --- Markdown report ---
    def _mean_for(sweep: str, method: str) -> float | None:
        for s in summary_rows:
            if s["sweep_name"] == sweep and s["method"] == method:
                return float(s["mean_ndcg_at_k"])
        return None

    plain_prior = _mean_for("plain_baseline", METHOD_PRIOR)
    plain_unrep = _mean_for("plain_baseline", METHOD_UNREPAIRED)
    plain_rep = _mean_for("plain_baseline", METHOD_REPAIRED)

    ma_repaired = [
        s
        for s in summary_rows
        if s["method"] == METHOD_REPAIRED and s["sweep_name"] != "plain_baseline"
    ]
    if not ma_repaired:
        raise RuntimeError("No metric_aware sweep summaries; check runs failed.")

    best_ma_row = max(ma_repaired, key=lambda s: float(s["mean_ndcg_at_k"]))
    best_mean = float(best_ma_row["mean_ndcg_at_k"])
    best_sweep = best_ma_row["sweep_name"]
    best_line = (
        f"{best_sweep} "
        f"(β={best_ma_row['metric_aware_beta']}, "
        f"focus_top_k={best_ma_row['metric_aware_focus_top_k']})"
    )

    improved_over_plain = plain_rep is not None and best_mean > plain_rep
    improved_over_unrep = plain_unrep is not None and best_mean > plain_unrep

    # Per-query deltas: best MA sweep vs plain repaired
    plain_by_q: dict[str, float] = {}
    for r in rows:
        if r["sweep_name"] != "plain_baseline" or r["method"] != METHOD_REPAIRED:
            continue
        q = r["query_id"]
        v = _float_or_none(r.get("ndcg_at_k", ""))
        if v is not None:
            plain_by_q[q] = v

    ma_by_q: dict[str, float] = {}
    for r in rows:
        if r["sweep_name"] != best_sweep or r["method"] != METHOD_REPAIRED:
            continue
        q = r["query_id"]
        v = _float_or_none(r.get("ndcg_at_k", ""))
        if v is not None:
            ma_by_q[q] = v

    deltas: list[tuple[str, float]] = []
    for q in plain_by_q:
        if q in ma_by_q:
            deltas.append((q, ma_by_q[q] - plain_by_q[q]))
    deltas.sort(key=lambda x: x[1], reverse=True)
    top_pos = deltas[:10]
    top_neg = sorted(deltas, key=lambda x: x[1])[:10]

    lines = [
        "# Metric-aware FAS — first experiment (SciDocs, ms1)",
        "",
        "## Baseline means (plain repair sweep)",
        "",
        f"- Output root: `{output_root}`",
    ]
    if inputs_note:
        lines.append(inputs_note)
    if plain_rep is not None:
        lines.append(f"- Plain repaired Copeland mean nDCG@k: **{plain_rep:.6f}**")
    else:
        lines.append("- Plain repaired Copeland: *(missing)*")
    if plain_unrep is not None:
        lines.append(f"- Unrepaired Copeland mean nDCG@k: **{plain_unrep:.6f}**")
    if plain_prior is not None:
        lines.append(f"- Prior-only mean nDCG@k: **{plain_prior:.6f}**")
    lines.extend(
        [
            "",
            "## Best metric-aware repaired Copeland (max mean nDCG@k)",
            "",
            f"- **metric_aware_beta:** `{best_ma_row['metric_aware_beta']}`",
            f"- **metric_aware_top_k (focus):** `{best_ma_row['metric_aware_focus_top_k']}`",
            f"- **Sweep id:** `{best_sweep}`",
            f"- **Mean nDCG@k:** **{best_mean:.6f}** (`{best_line}`)",
            "",
            "### vs baselines",
            "",
        ]
    )
    if plain_rep is not None:
        lines.append(f"- Δ vs plain repaired: **{best_mean - plain_rep:+.6f}**")
    if plain_unrep is not None:
        lines.append(f"- Best MA vs unrepaired Copeland: **{best_mean - plain_unrep:+.6f}**")
    if plain_prior is not None:
        lines.append(f"- Best MA vs prior-only: **{best_mean - plain_prior:+.6f}**")
    lines.extend(
        [
            "",
            "## Verdict (quick read)",
            "",
            f"- Best MA **{'beats' if improved_over_plain else 'does not beat'}** "
            "plain repaired Copeland on mean nDCG@k.",
            f"- Best MA **{'beats' if improved_over_unrep else 'does not beat'}** "
            "unrepaired Copeland on mean nDCG@k.",
            "",
            "## Top 10 queries: largest gain (best MA − plain repaired, nDCG@k)",
            "",
        ]
    )
    for q, d in top_pos:
        lines.append(f"- `{q}`: **{d:+.6f}**")
    lines.extend(["", "## Top 10 queries: largest drop", ""])
    for q, d in top_neg:
        lines.append(f"- `{q}`: **{d:+.6f}**")
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Combined per-query rows: `{comb_path.relative_to(_REPO)}`",
            f"- Summary CSV: `{summary_path.relative_to(_REPO)}`",
            f"- Key comparison CSV: `{cmp_path.relative_to(_REPO)}`",
            "",
        ]
    )

    report_path = output_root / "REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    with cmp_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "metric",
                "plain_repaired_copeland",
                "best_metric_aware_repaired_copeland",
                "unrepaired_copeland",
                "prior_only",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "metric": "mean_ndcg_at_k",
                "plain_repaired_copeland": plain_rep if plain_rep is not None else "",
                "best_metric_aware_repaired_copeland": best_mean,
                "unrepaired_copeland": plain_unrep if plain_unrep is not None else "",
                "prior_only": plain_prior if plain_prior is not None else "",
            }
        )

    print(f"[done] Wrote {comb_path}", flush=True)
    print(f"[done] Wrote {summary_path}", flush=True)
    print(f"[done] Wrote {cmp_path}", flush=True)
    print(f"[done] Wrote {report_path}", flush=True)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    inputs_root = _discover_inputs(
        args.inputs_root.resolve() if args.inputs_root else None
    )
    score_prior_files = _score_prior_paths(inputs_root)
    if len(score_prior_files) < len(SCORE_PRIOR_FILENAMES):
        miss = [n for n in SCORE_PRIOR_FILENAMES if not (inputs_root / n).exists()]
        print(
            f"[warn] Using {len(score_prior_files)}/{len(SCORE_PRIOR_FILENAMES)} score priors "
            f"(missing: {miss}). RRF prior will differ from full three-scorer setup.",
            flush=True,
        )
    nq_file = _count_query_ids(inputs_root / "query_ids.txt")
    max_q = args.max_queries if args.max_queries is not None else nq_file

    methods = list(METHODS_COP)
    if args.include_balance:
        methods.extend(
            [
                "hybrid_rrf_unrepaired_balance_a03",
                "hybrid_rrf_repaired_balance_a03",
            ]
        )

    meta = {
        "command": " ".join(sys.argv),
        "git_commit": _git_head(),
        "inputs_root": str(inputs_root),
        "score_prior_files": [str(p) for p in score_prior_files],
        "output_root": str(output_root),
        "graph_top_k": args.graph_top_k,
        "max_queries": max_q,
        "seed": args.seed,
        "methods": methods,
        "grid": {
            "repair_weighting": ["plain", "metric_aware"],
            "metric_aware_beta": list(BETAS),
            "metric_aware_top_k": list(FOCUS_TOP_KS),
            "metric_aware_gain_source": "prior_score",
        },
    }
    (output_root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("=" * 72)
    print("Metric-aware first experiment — SciDocs ms1")
    print("=" * 72)
    print(f"  inputs_root   : {inputs_root}")
    print(f"  score_priors  : {', '.join(p.name for p in score_prior_files)}")
    print(f"  output_root   : {output_root}")
    print(f"  query ids file: {nq_file} lines (using max_queries={max_q})")
    print(f"  graph_top_k   : {args.graph_top_k}")
    print(f"  git commit    : {meta['git_commit']}")
    print(f"  method list   : {methods}")
    print(f"  grid: plain baseline + metric_aware × beta ∈ {BETAS} × focus_top_k ∈ {FOCUS_TOP_KS}")
    print("=" * 72)

    sweep_root = output_root / "sweep"
    all_rows: list[dict] = []

    # Plain baseline (metric-aware params ignored; store for traceability)
    plain_dir = sweep_root / "plain_baseline"
    _run_real_cmd(
        output_subdir=plain_dir,
        repair_weighting="plain",
        metric_aware_beta=1.0,
        metric_aware_top_k=None,
        inputs_root=inputs_root,
        score_prior_files=score_prior_files,
        max_queries=max_q,
        graph_top_k=args.graph_top_k,
        seed=args.seed,
        methods=methods,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        pq = _per_query_path(plain_dir)
        if not pq.exists():
            raise FileNotFoundError(f"Expected output missing: {pq}")
        for row in _read_per_query(pq):
            row = dict(row)
            row["sweep_name"] = "plain_baseline"
            all_rows.append(row)

    for beta in BETAS:
        for focus in FOCUS_TOP_KS:
            tag = f"ma_beta_{str(beta).replace('.', 'p')}_focus_{focus}"
            run_dir = sweep_root / tag
            _run_real_cmd(
                output_subdir=run_dir,
                repair_weighting="metric_aware",
                metric_aware_beta=beta,
                metric_aware_top_k=focus,
                inputs_root=inputs_root,
                score_prior_files=score_prior_files,
                max_queries=max_q,
                graph_top_k=args.graph_top_k,
                seed=args.seed,
                methods=methods,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                pq = _per_query_path(run_dir)
                if not pq.exists():
                    raise FileNotFoundError(f"Expected output missing: {pq}")
                for row in _read_per_query(pq):
                    row = dict(row)
                    row["sweep_name"] = tag
                    all_rows.append(row)

    note = ""
    if len(score_prior_files) < len(SCORE_PRIOR_FILENAMES):
        note = (
            "- **Score priors:** "
            + ", ".join(f"`{p.name}`" for p in score_prior_files)
            + " — *subset of BM25+TF-IDF+MiniLM; "
            "not directly comparable to full three-scorer runs.*"
        )
    _aggregate_and_report(
        output_root=output_root, rows=all_rows, dry_run=args.dry_run, inputs_note=note
    )
    print("[done] Experiment finished.", flush=True)


if __name__ == "__main__":
    main()
