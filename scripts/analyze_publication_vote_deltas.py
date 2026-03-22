#!/usr/bin/env python
"""
Bootstrap mean ΔnDCG@k (method_b - method_a) from ``*_per_query.csv``.

Optional stratification by ``largest_scc`` (median split) or ``is_cyclic``.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def _read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ndcg_by_method(rows: list[dict], method: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in rows:
        if r["method"] != method:
            continue
        qid = r["query_id"]
        v = r.get("ndcg_at_k")
        if v is None or v == "":
            continue
        out[qid] = float(v)
    return out


def _graph_by_query(rows: list[dict], ref_method: str) -> dict[str, dict]:
    g: dict[str, dict] = {}
    for r in rows:
        if r["method"] != ref_method:
            continue
        qid = r["query_id"]
        g[qid] = {
            "is_cyclic": str(r.get("is_cyclic", "")).lower() in ("true", "1", "yes"),
            "largest_scc": int(float(r["largest_scc"])),
            "n_edges": int(float(r["n_edges"])),
        }
    return g


def _bootstrap_mean(
    deltas: list[float],
    *,
    n_boot: int,
    seed: int,
    alpha: float,
) -> tuple[float, float, float]:
    if not deltas:
        return (float("nan"), float("nan"), float("nan"))
    n = len(deltas)
    mean = sum(deltas) / n
    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(n_boot):
        s = sum(deltas[rng.randrange(n)] for _ in range(n)) / n
        boots.append(s)
    boots.sort()
    lo_i = max(0, int((alpha / 2) * n_boot))
    hi_i = min(n_boot - 1, int((1 - alpha / 2) * n_boot) - 1)
    return mean, boots[lo_i], boots[hi_i]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--per-query-csv", type=Path, required=True)
    p.add_argument("--method-a", type=str, required=True, help="e.g. unrepaired baseline")
    p.add_argument("--method-b", type=str, required=True, help="e.g. repaired variant")
    p.add_argument("--ref-method", type=str, default="hybrid_rrf_repaired_copeland_a03")
    p.add_argument("--bootstrap", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args()

    rows = _read_rows(args.per_query_csv)
    a_map = _ndcg_by_method(rows, args.method_a)
    b_map = _ndcg_by_method(rows, args.method_b)
    common = sorted(set(a_map) & set(b_map))
    deltas = [b_map[q] - a_map[q] for q in common]
    mean_d, lo, hi = _bootstrap_mean(
        deltas, n_boot=args.bootstrap, seed=args.seed, alpha=args.alpha
    )

    gstats = _graph_by_query(rows, args.ref_method)
    scc_vals = [gstats[q]["largest_scc"] for q in common if q in gstats]
    med_scc = sorted(scc_vals)[len(scc_vals) // 2] if scc_vals else 0

    strata: dict[str, list[float]] = {"all": deltas}
    high_scc: list[float] = []
    low_scc: list[float] = []
    cyc: list[float] = []
    acyc: list[float] = []
    for q in common:
        d = b_map[q] - a_map[q]
        gs = gstats.get(q)
        if gs:
            if gs["largest_scc"] >= med_scc:
                high_scc.append(d)
            else:
                low_scc.append(d)
            if gs["is_cyclic"]:
                cyc.append(d)
            else:
                acyc.append(d)
    strata["largest_scc_ge_median"] = high_scc
    strata["largest_scc_lt_median"] = low_scc
    strata["is_cyclic"] = cyc
    strata["acyclic"] = acyc

    out: dict = {
        "n_queries": len(common),
        "method_a": args.method_a,
        "method_b": args.method_b,
        "mean_delta_ndcg": mean_d,
        "ci_low": lo,
        "ci_high": hi,
        "bootstrap": args.bootstrap,
        "median_largest_scc": med_scc,
        "strata": {},
    }
    for name, vals in strata.items():
        subseed = args.seed + sum(ord(c) for c in name) % 10_000
        m, lo_s, hi_s = _bootstrap_mean(
            vals, n_boot=args.bootstrap, seed=subseed, alpha=args.alpha
        )
        out["strata"][name] = {
            "n": len(vals),
            "mean_delta_ndcg": m if m == m else None,
            "ci_low": lo_s if lo_s == lo_s else None,
            "ci_high": hi_s if hi_s == hi_s else None,
        }

    print(json.dumps(out, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
