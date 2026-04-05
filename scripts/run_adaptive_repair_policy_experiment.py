#!/usr/bin/env python
"""
Lightweight adaptive-repair policy analysis on canonical all4 publication artifacts.

Policy (Copeland):
  - if acyclic: use unrepaired Copeland
  - else: use repaired Copeland

This script reuses committed aggregate outputs under ``outputs/pub_vote_cmp_all4``.
It does not rerun heavy real-data experiments.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PUB_ROOT = REPO_ROOT / "outputs" / "pub_vote_cmp_all4"
DEFAULT_OUT_DIR = REPO_ROOT / "outputs" / "adaptive_repair_policy" / "all4_ms1"


@dataclass(frozen=True)
class AdaptiveRow:
    dataset: str
    variant: str
    n_queries: int
    n_cyclic: int
    n_acyclic: int
    trigger_rate_repair: float
    skip_rate_repair: float
    mean_ndcg_prior: float
    mean_ndcg_unrepaired_copeland: float
    mean_ndcg_repaired_copeland: float
    mean_ndcg_adaptive_copeland: float
    mean_delta_adaptive_minus_repaired: float
    mean_delta_adaptive_minus_unrepaired: float
    mean_delta_unrepaired_minus_repaired_acyclic: float
    mean_ndcg_unrepaired_balance: float | None = None
    mean_ndcg_repaired_balance: float | None = None
    mean_ndcg_adaptive_balance: float | None = None
    mean_delta_adaptive_minus_repaired_balance: float | None = None


def _load_graph_table(pub_root: Path) -> dict[tuple[str, str], dict[str, str]]:
    path = pub_root / "paper_package" / "tables" / "table_graph_ndcg_and_consistency.csv"
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {(r["dataset"], r["variant"]): r for r in rows}


def _load_delta_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_row(
    dataset: str,
    variant: str,
    graph_row: dict[str, str],
    delta_copeland: dict,
    delta_balance: dict | None,
) -> AdaptiveRow:
    strata = delta_copeland.get("strata", {})
    s_all = strata.get("all", {})
    s_cyc = strata.get("is_cyclic", {})
    s_acy = strata.get("acyclic", {})

    n_all = int(s_all.get("n", graph_row["n_queries"]))
    n_cyclic = int(s_cyc.get("n", 0))
    n_acyclic = int(s_acy.get("n", n_all - n_cyclic))
    trigger_rate = (n_cyclic / n_all) if n_all > 0 else 0.0
    skip_rate = (n_acyclic / n_all) if n_all > 0 else 0.0

    mean_prior = float(graph_row["mean_ndcg_prior"])
    mean_uco = float(graph_row["mean_ndcg_uco"])
    mean_rco = float(graph_row["mean_ndcg_rco"])
    delta_u_minus_r_acy = float(s_acy.get("mean_delta_ndcg", 0.0))

    # Adaptive minus repaired = skip_rate * (unrepaired - repaired on skipped queries).
    # With this policy skipped queries are acyclic.
    delta_adaptive_minus_repaired = skip_rate * delta_u_minus_r_acy
    mean_adaptive = mean_rco + delta_adaptive_minus_repaired

    mean_uba = float(graph_row["mean_ndcg_uba"]) if graph_row.get("mean_ndcg_uba") else None
    mean_rba = float(graph_row["mean_ndcg_rba"]) if graph_row.get("mean_ndcg_rba") else None
    mean_adaptive_balance = None
    delta_adaptive_minus_repaired_balance = None
    if delta_balance is not None and mean_uba is not None and mean_rba is not None:
        s_acy_bal = delta_balance.get("strata", {}).get("acyclic", {})
        delta_u_minus_r_acy_bal = float(s_acy_bal.get("mean_delta_ndcg", 0.0))
        delta_adaptive_minus_repaired_balance = skip_rate * delta_u_minus_r_acy_bal
        mean_adaptive_balance = mean_rba + delta_adaptive_minus_repaired_balance

    return AdaptiveRow(
        dataset=dataset,
        variant=variant,
        n_queries=n_all,
        n_cyclic=n_cyclic,
        n_acyclic=n_acyclic,
        trigger_rate_repair=trigger_rate,
        skip_rate_repair=skip_rate,
        mean_ndcg_prior=mean_prior,
        mean_ndcg_unrepaired_copeland=mean_uco,
        mean_ndcg_repaired_copeland=mean_rco,
        mean_ndcg_adaptive_copeland=mean_adaptive,
        mean_delta_adaptive_minus_repaired=delta_adaptive_minus_repaired,
        mean_delta_adaptive_minus_unrepaired=mean_adaptive - mean_uco,
        mean_delta_unrepaired_minus_repaired_acyclic=delta_u_minus_r_acy,
        mean_ndcg_unrepaired_balance=mean_uba,
        mean_ndcg_repaired_balance=mean_rba,
        mean_ndcg_adaptive_balance=mean_adaptive_balance,
        mean_delta_adaptive_minus_repaired_balance=delta_adaptive_minus_repaired_balance,
    )


def run(pub_root: Path, out_dir: Path, variant: str, include_balance: bool) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    graph = _load_graph_table(pub_root)
    datasets = ["scidocs", "fiqa", "hotpotqa", "bright"]
    rows: list[AdaptiveRow] = []
    for ds in datasets:
        key = (ds, variant)
        if key not in graph:
            raise FileNotFoundError(f"Missing row in graph table for {ds}/{variant}")
        copeland_json = pub_root / "analysis" / f"{ds}_{variant}_delta_copeland.json"
        if not copeland_json.exists():
            raise FileNotFoundError(f"Missing analysis file: {copeland_json}")
        balance_json = pub_root / "analysis" / f"{ds}_{variant}_delta_balance.json"
        delta_bal = _load_delta_json(balance_json) if include_balance and balance_json.exists() else None
        rows.append(
            _build_row(
                ds,
                variant,
                graph[key],
                _load_delta_json(copeland_json),
                delta_bal,
            )
        )

    csv_path = out_dir / "adaptive_repair_summary.csv"
    fieldnames = list(AdaptiveRow.__dataclass_fields__.keys())
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.__dict__)

    report_lines = [
        "# Adaptive repair policy (lightweight)",
        "",
        f"- Source root: `{pub_root}`",
        f"- Variant: `{variant}`",
        "- Policy: **skip repair when acyclic**, otherwise use repaired method.",
        "",
        "## Copeland summary",
        "",
        "| Dataset | Trigger repair % | Prior | Unrepaired Copeland | Repaired Copeland | Adaptive Copeland | Δ(adaptive-repaired) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        report_lines.append(
            "| "
            f"{r.dataset} | "
            f"{100.0*r.trigger_rate_repair:.2f}% | "
            f"{r.mean_ndcg_prior:.6f} | "
            f"{r.mean_ndcg_unrepaired_copeland:.6f} | "
            f"{r.mean_ndcg_repaired_copeland:.6f} | "
            f"{r.mean_ndcg_adaptive_copeland:.6f} | "
            f"{r.mean_delta_adaptive_minus_repaired:+.6f} |"
        )
    report_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Paired deltas are derived from the committed bootstrap analysis strata.",
            "- For this strict policy, skipped queries are the acyclic stratum.",
            "- If acyclic unrepaired-vs-repaired delta is zero, adaptive equals always-repair.",
            "",
        ]
    )
    if include_balance:
        report_lines.extend(
            [
                "## Balance (optional)",
                "",
                "| Dataset | Unrepaired Balance | Repaired Balance | Adaptive Balance | Δ(adaptive-repaired) |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for r in rows:
            if r.mean_ndcg_unrepaired_balance is None:
                continue
            report_lines.append(
                "| "
                f"{r.dataset} | "
                f"{r.mean_ndcg_unrepaired_balance:.6f} | "
                f"{r.mean_ndcg_repaired_balance:.6f} | "
                f"{r.mean_ndcg_adaptive_balance:.6f} | "
                f"{(r.mean_delta_adaptive_minus_repaired_balance or 0.0):+.6f} |"
            )
        report_lines.append("")

    md_path = out_dir / "REPORT.md"
    md_path.write_text("\n".join(report_lines), encoding="utf-8")
    return csv_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pub-root", type=Path, default=DEFAULT_PUB_ROOT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--variant", type=str, default="ms1", choices=["ms1", "ms2", "ms1_drop_mutual"])
    p.add_argument("--include-balance", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    csv_path, md_path = run(
        pub_root=args.pub_root.resolve(),
        out_dir=args.output_dir.resolve(),
        variant=args.variant,
        include_balance=args.include_balance,
    )
    print(f"[done] {csv_path}")
    print(f"[done] {md_path}")


if __name__ == "__main__":
    main()
