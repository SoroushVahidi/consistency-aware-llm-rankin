#!/usr/bin/env python
"""
Summarize directed-cycle structure for a votes JSONL (or any pairwise file
accepted by the real experiment loader).

Usage::
    python scripts/diagnose_vote_graph_cycles.py --pairwise-file path/to/votes.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from consistency_ranker.cycle_detection import has_cycle  # noqa: E402
from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402


def _load_by_query(path: Path) -> dict[str, list[Preference]]:
    import json

    by_q: dict[str, list[Preference]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = str(row["query_id"])
            w = str(row.get("winner_doc_id", row.get("winner")))
            ell = str(row.get("loser_doc_id", row.get("loser")))
            wt = float(row.get("weight", 1.0))
            by_q[qid].append(Preference(winner=w, loser=ell, weight=wt))
    return dict(by_q)


def _has_mutual_edge(prefs: list[Preference]) -> bool:
    edges = {(p.winner, p.loser) for p in prefs}
    return any((b, a) in edges for (a, b) in edges)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pairwise-file", type=Path, required=True)
    p.add_argument("--max-queries", type=int, default=None)
    args = p.parse_args()

    by_q = _load_by_query(args.pairwise_file)
    qids = sorted(by_q.keys())
    if args.max_queries is not None:
        qids = qids[: args.max_queries]

    n_cyclic = 0
    n_bidir = 0
    total_edges = 0
    for qid in qids:
        prefs = by_q[qid]
        g = build_graph(prefs)
        total_edges += g.number_of_edges()
        if has_cycle(g):
            n_cyclic += 1
        if _has_mutual_edge(prefs):
            n_bidir += 1

    n = len(qids)
    print(f"[diagnose_vote_graph_cycles] file={args.pairwise_file}")
    print(f"[diagnose_vote_graph_cycles] queries={n}")
    if n:
        print(
            f"[diagnose_vote_graph_cycles] pct_cyclic={100.0 * n_cyclic / n:.1f}% "
            f"({n_cyclic}/{n})"
        )
        print(
            f"[diagnose_vote_graph_cycles] queries_with_any_mutual_pair="
            f"{100.0 * n_bidir / n:.1f}% ({n_bidir}/{n})"
        )
        print(
            f"[diagnose_vote_graph_cycles] avg_edges_per_query={total_edges / n:.2f}"
        )
    else:
        print("[diagnose_vote_graph_cycles] no queries")


if __name__ == "__main__":
    main()
