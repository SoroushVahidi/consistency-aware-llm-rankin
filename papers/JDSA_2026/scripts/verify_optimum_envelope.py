#!/usr/bin/env python3
"""Independently verify the saved six-graph diagnostic; standard library only.

Positive-weight eight-node inputs only. Enumerates all 8! total orders, obtains
all distinct minimum-weight backward-edge sets, applies fixed unweighted
Copeland with rank-preserving integer ties, and recomputes full-query nDCG@10.
No solver, model, source repository, network or third-party implementation is
used. Reference results are opened only after independent output is written.
"""

import argparse
import hashlib
import itertools
import json
import math
import statistics
import time
from fractions import Fraction
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ranking(n, edges, removed):
    scores = [0] * n
    for i, (u, v, _) in enumerate(edges):
        if i not in removed:
            scores[u] += 1
            scores[v] -= 1
    return sorted(range(n), key=lambda u: (-scores[u], u))


def acyclic(n, edges, removed):
    indegrees = [0] * n
    adjacency = [[] for _ in range(n)]
    for i, (u, v, _) in enumerate(edges):
        if i not in removed:
            adjacency[u].append(v)
            indegrees[v] += 1
    queue = [u for u in range(n) if indegrees[u] == 0]
    visited = 0
    while queue:
        u = queue.pop()
        visited += 1
        for v in adjacency[u]:
            indegrees[v] -= 1
            if indegrees[v] == 0:
                queue.append(v)
    return visited == n


def ndcg(order, gains, ideal):
    dcg = math.fsum(gains[u] / math.log2(i + 2) for i, u in enumerate(order[:10]))
    idcg = math.fsum(g / math.log2(i + 2) for i, g in enumerate(ideal[:10]))
    return dcg / idcg if idcg > 0 else 0.0


def verify_graph(graph):
    n = graph["nodes"]
    assert n == 8
    edges = [(u, v, Fraction(w)) for u, v, w in graph["edges"]]
    assert all(u != v and 0 <= u < n and 0 <= v < n and w > 0 for u, v, w in edges)
    assert len({(u, v) for u, v, _ in edges}) == len(edges)
    scale = math.lcm(*(w.denominator for _, _, w in edges))
    integer_edges = [(u, v, int(w * scale)) for u, v, w in edges]
    assert len(graph["candidate_gains"]) == n
    assert len(graph["ideal_gains"]) <= 10
    best_cost = None
    repairs = set()
    visited = 0
    for order in itertools.permutations(range(n)):
        positions = [0] * n
        for pos, u in enumerate(order):
            positions[u] = pos
        backward = tuple(
            i for i, (u, v, _) in enumerate(integer_edges) if positions[u] > positions[v]
        )
        cost = sum(integer_edges[i][2] for i in backward)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            repairs = {backward}
        elif cost == best_cost:
            repairs.add(backward)
        visited += 1
    assert visited == math.factorial(n)
    # Strict positivity is essential: any optimum deletion set equals the
    # backward set of a retained-DAG topological order. Zero-cost supersets
    # would require additional enumeration and are deliberately rejected.
    rows = []
    for removed in sorted(repairs):
        assert acyclic(n, integer_edges, removed)
        order = ranking(n, integer_edges, removed)
        rows.append(
            {
                "removed_indices": list(removed),
                "ranking": order,
                "ndcg10": ndcg(order, graph["candidate_gains"], graph["ideal_gains"]),
            }
        )
    historical = tuple(sorted(graph["historical_removed_indices"]))
    assert historical in repairs
    baseline_order = ranking(n, integer_edges, ())
    base = ndcg(baseline_order, graph["candidate_gains"], graph["ideal_gains"])
    hist = next(row["ndcg10"] for row in rows if row["removed_indices"] == list(historical))
    values = [row["ndcg10"] for row in rows]
    return {
        "graph_id": graph["graph_id"],
        "orders_visited": visited,
        "optimum_weight": best_cost / scale,
        "optimum_scaled_integer": best_cost,
        "weight_scale": scale,
        "distinct_optima": len(rows),
        "distinct_rankings": len({tuple(row["ranking"]) for row in rows}),
        "distinct_utilities": len(set(values)),
        "minimum": min(values),
        "maximum": max(values),
        "width": max(values) - min(values),
        "unrepaired": base,
        "historical": hist,
        "historical_is_utility_best": hist == max(values),
        "repairs": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    input_path = args.input.resolve()
    root = input_path.parent
    reference_path = args.reference.resolve() if args.reference else root / "reference_results.json"
    out = args.output.resolve()
    assert out != root and root not in out.parents
    out.mkdir(exist_ok=False)
    ledger = json.loads((root / "CHECKSUMS.json").read_text())
    assert digest(input_path) == ledger["numeric_inputs.json"]
    inputs = json.loads(input_path.read_text())
    assert len(inputs) == 6 and len({x["graph_id"] for x in inputs}) == 6
    computed = [verify_graph(graph) for graph in inputs]
    (out / "COMPUTED_BEFORE_REFERENCE.json").write_text(json.dumps(computed, indent=2) + "\n")
    assert digest(reference_path) == ledger["reference_results.json"]
    reference = {r["graph_id"]: r for r in json.loads(reference_path.read_text())}
    max_error = 0.0
    for result in computed:
        expected = reference[result["graph_id"]]
        for field in ["distinct_optima", "distinct_rankings", "distinct_utilities"]:
            assert result[field] == expected[field], (result["graph_id"], field)
        for field in ["optimum_weight", "minimum", "maximum", "unrepaired", "historical"]:
            error = abs(result[field] - expected[field])
            max_error = max(error, max_error)
            assert error <= 1e-12, (result["graph_id"], field, error)
        expected_repairs = {tuple(r["removed_indices"]): r for r in expected["repairs"]}
        assert {tuple(r["removed_indices"]) for r in result["repairs"]} == set(expected_repairs)
        for row in result["repairs"]:
            expected_row = expected_repairs[tuple(row["removed_indices"])]
            assert row["ranking"] == expected_row["ranking"]
            assert abs(row["ndcg10"] - expected_row["ndcg10"]) <= 1e-12
    mean_min = statistics.fmean(r["minimum"] for r in computed)
    mean_max = statistics.fmean(r["maximum"] for r in computed)
    baseline = statistics.fmean(r["unrepaired"] for r in computed)
    report = {
        "state": "COMPLETED_SUCCESS",
        "graphs": len(computed),
        "total_orders_visited": sum(r["orders_visited"] for r in computed),
        "unique_optimum_graphs": sum(r["distinct_optima"] == 1 for r in computed),
        "distinct_repairs": sum(r["distinct_optima"] for r in computed),
        "graphs_with_utility_variation": sum(r["width"] > 1e-12 for r in computed),
        "maximum_query_width": max(r["width"] for r in computed),
        "mean_minimum": mean_min,
        "mean_maximum": mean_max,
        "baseline": baseline,
        "mean_delta_minimum": mean_min - baseline,
        "mean_delta_maximum": mean_max - baseline,
        "historical_selections_utility_best": all(
            r["historical_is_utility_best"] for r in computed
        ),
        "any_negative_query_effect": any(r["minimum"] < r["unrepaired"] - 1e-12 for r in computed),
        "max_reference_absolute_error": max_error,
        "scope": (
            "Independent complete finite reconstruction from preserved processed graphs "
            "and metric-sufficient gains; provider judgments and original corpus "
            "acquisition are not reconstructed"
        ),
        "runtime_seconds": time.monotonic() - started,
    }
    (out / "VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
