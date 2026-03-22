#!/usr/bin/env python
"""Print a markdown table from ``run_publication_vote_suite.py`` outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _mean(rows: list[dict], method: str, col: str = "ndcg_at_k") -> float | None:
    vals = [float(r[col]) for r in rows if r["method"] == method and r.get(col)]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _graph_stats_from_csv(rows: list[dict], ref: str = "hybrid_rrf_repaired_copeland_a03"):
    sub = [r for r in rows if r["method"] == ref]
    if not sub:
        return None
    n = len(sub)
    pct_cyc = sum(str(r.get("is_cyclic", "")).lower() in ("true", "1") for r in sub) / n * 100
    avg_scc = sum(float(r["largest_scc"]) for r in sub) / n
    avg_e = sum(float(r["n_edges"]) for r in sub) / n
    return pct_cyc, avg_scc, avg_e


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("outputs/pub_vote_cmp_v2"))
    args = p.parse_args()

    variants = ("ms2", "ms1", "ms1_drop_mutual")
    methods = {
        "prior": "hybrid_rrf_prior_only",
        "uco": "hybrid_rrf_unrepaired_copeland_a03",
        "rco": "hybrid_rrf_repaired_copeland_a03",
        "uba": "hybrid_rrf_unrepaired_balance_a03",
        "rba": "hybrid_rrf_repaired_balance_a03",
    }

    hdr = (
        "| dataset | variant | pct_cyclic | avg_scc | avg_edges | "
        "ndcg_uco | ndcg_rco | d_copeland | ndcg_uba | ndcg_rba | "
        "d_balance | n_q |"
    )
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [hdr, sep]

    for ds in ("scidocs", "hotpotqa"):
        for var in variants:
            summ_path = args.root / ds / var / ds / "votes_file" / f"{ds}_experiment_summary.json"
            csv_path = args.root / ds / var / ds / "votes_file" / f"{ds}_per_query.csv"
            if not summ_path.exists() or not csv_path.exists():
                lines.append(f"| {ds} | {var} | *missing* | | | | | | | | | |")
                continue
            summ = json.loads(summ_path.read_text(encoding="utf-8"))
            with csv_path.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            g = _graph_stats_from_csv(rows)
            nq = summ.get("n_processed", len({r["query_id"] for r in rows}) // 5)
            pct_c = summ.get("pct_cyclic_graphs", "")
            avs = summ.get("avg_largest_scc", "")
            ave = summ.get("avg_n_edges", "")
            if g is not None:
                pct_c, avs, ave = g[0], round(g[1], 2), round(g[2], 2)
            uco = _mean(rows, methods["uco"])
            rco = _mean(rows, methods["rco"])
            uba = _mean(rows, methods["uba"])
            rba = _mean(rows, methods["rba"])
            dc = (rco - uco) if uco is not None and rco is not None else None
            db = (rba - uba) if uba is not None and rba is not None else None
            lines.append(
                f"| {ds} | {var} | {pct_c} | "
                f"{avs} | {ave} | "
                f"{uco if uco is not None else ''} | {rco if rco is not None else ''} | "
                f"{dc if dc is not None else ''} | "
                f"{uba if uba is not None else ''} | {rba if rba is not None else ''} | "
                f"{db if db is not None else ''} | {nq} |"
            )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
