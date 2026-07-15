#!/usr/bin/env python3
"""Phase 3 validation: cross-check the SCIP exact ILP solver's objective value
against the existing brute-force exact_fas.py (independent exact method) on
(a) random synthetic weighted digraphs with cycles, n in {4..10}, and
(b) real hotpotqa n=10 preference graphs from the canonical calibrated_all4
primary-protocol package (small enough for brute force: 10! = 3,628,800).

Both methods solve the same problem (minimum weight feedback arc set); if
they disagree on the optimal objective value, something is wrong with one
of the implementations (most likely the new SCIP port) and the study must
not proceed until reconciled.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import networkx as nx

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SRC_ROOT = REPO_ROOT / "src"
for p in (REPO_ROOT, SRC_ROOT, SCRIPT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from consistency_ranker.exact_fas import exact_fas  # noqa: E402
from exact_ilp_scip import solve_ilp_scip  # noqa: E402


def random_cyclic_digraph(n: int, p_edge: float, seed: int) -> nx.DiGraph:
    rng = random.Random(seed)
    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    for u in range(n):
        for v in range(n):
            if u == v:
                continue
            if rng.random() < p_edge:
                g.add_edge(u, v, weight=round(rng.uniform(0.1, 3.0), 4))
    return g


def compare_one(graph: nx.DiGraph, label: str) -> dict:
    _dag_bf, _removed_bf, obj_bf = exact_fas(graph, max_n=12)
    _dag_scip, removed_scip, status = solve_ilp_scip(graph, time_limit_s=60.0, mip_gap=0.0)
    obj_scip = sum(w for _u, _v, w in removed_scip)
    ok = status.proven_optimal and abs(obj_bf - obj_scip) < 1e-6
    return {
        "label": label,
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "bruteforce_objective": obj_bf,
        "scip_objective": obj_scip,
        "scip_status": status.status,
        "scip_proven_optimal": status.proven_optimal,
        "scip_gap": status.gap,
        "scip_time_s": status.time_s,
        "match": ok,
    }


def main() -> int:
    out_dir = SCRIPT_DIR.parent / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    # (a) synthetic random cyclic graphs
    for n in (4, 6, 8, 10):
        for p_edge in (0.3, 0.5, 0.8):
            for seed in range(3):
                g = random_cyclic_digraph(n, p_edge, seed=seed * 100 + n)
                if nx.is_directed_acyclic_graph(g):
                    continue
                rows.append(compare_one(g, f"synthetic_n{n}_p{p_edge}_seed{seed}"))

    # (b) real hotpotqa n=10 preference graphs (primary protocol, ms1)
    qr_path = (
        REPO_ROOT
        / "reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/"
        "primary_minmax_retention_matched/hotpotqa/ms1/query_records.jsonl"
    )
    n_real_checked = 0
    with qr_path.open() as fh:
        for i, line in enumerate(fh):
            if n_real_checked >= 15:
                break
            rec = json.loads(line)
            gs = rec["graph_stats"]
            if not gs.get("is_cyclic"):
                continue
            g = nx.DiGraph()
            g.add_nodes_from(range(gs["n_nodes"]))
            node_ids = {}

            def _idx(name: str) -> int:
                if name not in node_ids:
                    node_ids[name] = len(node_ids)
                return node_ids[name]

            for e in gs["preference_edges"]:
                g.add_edge(_idx(e["source"]), _idx(e["target"]), weight=float(e["weight"]))
            if g.number_of_nodes() < 2 or nx.is_directed_acyclic_graph(g):
                continue
            rows.append(compare_one(g, f"hotpotqa_ms1_query{i}_qid{rec['query_id']}"))
            n_real_checked += 1

    all_match = all(r["match"] for r in rows)
    all_proven = all(r["scip_proven_optimal"] for r in rows)

    with (out_dir / "scip_vs_bruteforce_validation.json").open("w") as fh:
        json.dump(
            {
                "n_cases": len(rows),
                "all_objectives_match": all_match,
                "all_scip_proven_optimal": all_proven,
                "cases": rows,
            },
            fh,
            indent=2,
        )

    print(f"n_cases={len(rows)} all_match={all_match} all_proven_optimal={all_proven}")
    for r in rows:
        flag = "OK" if r["match"] else "MISMATCH"
        print(
            f"  [{flag}] {r['label']}: n={r['n_nodes']} bf={r['bruteforce_objective']:.6f} "
            f"scip={r['scip_objective']:.6f} status={r['scip_status']} time={r['scip_time_s']:.3f}s"
        )

    if not all_match or not all_proven:
        print("VALIDATION FAILED", file=sys.stderr)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
