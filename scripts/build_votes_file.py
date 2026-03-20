"""
build_votes_file.py
===================
Build pairwise vote edges from multiple ranker score files.

Output schema (one row per ranker-vote pair):
{"query_id":"...","winner_doc_id":"...","loser_doc_id":"...","weight":<float>,"voter":"..."}
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# Allow running as `python scripts/build_votes_file.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.data.query_ids import (  # noqa: E402
    eligible_query_ids,
    load_query_ids_file,
)
from consistency_ranker.data.unified_loader import load_dataset_splits  # noqa: E402


def _load_scores(
    score_files: list[Path],
) -> dict[str, dict[str, dict[str, float]]]:
    """Load score files as query -> ranker -> doc -> score."""
    by_query: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))

    for score_path in score_files:
        if not score_path.exists():
            raise FileNotFoundError(f"Score file not found: {score_path}")
        with score_path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                qid = row.get("query_id")
                doc_id = row.get("doc_id")
                score = row.get("score")
                if qid is None or doc_id is None or score is None:
                    raise ValueError(
                        f"{score_path}:{lineno} missing required keys "
                        "(query_id, doc_id, score)."
                    )
                ranker = str(row.get("ranker", score_path.stem))
                qid = str(qid)
                doc_id = str(doc_id)
                val = float(score)
                prev = by_query[qid][ranker].get(doc_id)
                by_query[qid][ranker][doc_id] = max(prev, val) if prev is not None else val
    return by_query


def _select_candidates(
    ranker_scores: dict[str, dict[str, float]],
    top_k: int,
) -> list[str]:
    """Select top-k candidate docs using reciprocal-rank fusion."""
    union_docs = sorted({doc_id for scores in ranker_scores.values() for doc_id in scores})
    if len(union_docs) <= top_k:
        return union_docs

    rrf_scores: dict[str, float] = defaultdict(float)
    for ranker in sorted(ranker_scores):
        ranked = sorted(
            ranker_scores[ranker].items(),
            key=lambda x: (-x[1], x[0]),
        )
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            rrf_scores[doc_id] += 1.0 / (60.0 + rank)

    selected = sorted(
        union_docs,
        key=lambda d: (-rrf_scores.get(d, 0.0), d),
    )[:top_k]
    return selected


def _votes_for_query(
    query_id: str,
    ranker_scores: dict[str, dict[str, float]],
    top_k: int,
    vote_weight_scheme: str = "binary",
    min_vote_margin: float = 0.0,
    abstain_missing: bool = False,
    min_support: int = 1,
    min_aggregate_margin: float = 0.0,
) -> list[dict]:
    """Build deterministic pairwise vote rows for one query.

    Votes v2 controls:
    - weight by margin (`vote_weight_scheme="margin"`)
    - abstain for low-margin / missing evidence
    - edge-level filtering by minimum support and aggregate margin
    """
    if vote_weight_scheme not in {"binary", "margin"}:
        raise ValueError(
            f"Unknown vote_weight_scheme {vote_weight_scheme!r}. "
            "Choose 'binary' or 'margin'."
        )

    candidates = _select_candidates(ranker_scores, top_k=top_k)
    if len(candidates) < 2:
        return []

    votes_by_pair: dict[
        tuple[str, str],
        dict[tuple[str, str], list[tuple[str, float, float]]],
    ] = defaultdict(lambda: defaultdict(list))

    for voter in sorted(ranker_scores):
        score_map = ranker_scores[voter]
        floor = (min(score_map.values()) - 1.0) if score_map else -math.inf
        for a, b in combinations(candidates, 2):
            if abstain_missing and (a not in score_map or b not in score_map):
                continue
            sa = score_map.get(a, floor)
            sb = score_map.get(b, floor)
            margin = abs(sa - sb)
            if margin < min_vote_margin:
                continue
            if sa > sb:
                winner, loser = a, b
            elif sb > sa:
                winner, loser = b, a
            else:
                # Deterministic tie break
                winner, loser = (a, b) if a < b else (b, a)
            weight = margin if vote_weight_scheme == "margin" else 1.0
            pair_key = (a, b) if a < b else (b, a)
            votes_by_pair[pair_key][(winner, loser)].append((voter, float(weight), float(margin)))

    rows: list[dict] = []
    for pair_key in sorted(votes_by_pair):
        dir_votes = votes_by_pair[pair_key]
        for direction in sorted(dir_votes):
            recs = dir_votes[direction]
            support = len(recs)
            margin_sum = sum(r[2] for r in recs)
            if support < min_support or margin_sum < min_aggregate_margin:
                continue
            winner, loser = direction
            for voter, weight, _margin in recs:
                rows.append(
                    {
                        "query_id": query_id,
                        "winner_doc_id": winner,
                        "loser_doc_id": loser,
                        "weight": float(weight),
                        "voter": voter,
                    }
                )
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build pairwise vote edges from multiple score files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument(
        "--score-files",
        type=Path,
        nargs="+",
        required=True,
        help="One or more score JSONL files.",
    )
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--vote-weight-scheme",
        type=str,
        default="binary",
        choices=["binary", "margin"],
        help="Edge vote weight scheme.",
    )
    parser.add_argument(
        "--min-vote-margin",
        type=float,
        default=0.0,
        help="Abstain when per-ranker score margin is below this threshold.",
    )
    parser.add_argument(
        "--abstain-missing",
        action="store_true",
        help="Abstain when a ranker lacks either document in a pair.",
    )
    parser.add_argument(
        "--min-support",
        type=int,
        default=1,
        help="Minimum number of voter-supporting votes required per edge.",
    )
    parser.add_argument(
        "--min-aggregate-margin",
        type=float,
        default=0.0,
        help="Minimum aggregate margin (sum) required for edge retention.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--query-id-file",
        type=Path,
        default=None,
        help="Optional TXT/JSONL file with exact query ids to use.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    _queries, _docs, qrels = load_dataset_splits(args.dataset)
    eligible = set(eligible_query_ids(qrels))

    score_index = _load_scores(args.score_files)
    score_qids = sorted(score_index.keys())

    if args.query_id_file is not None:
        requested = load_query_ids_file(args.query_id_file)
        selected_qids = [qid for qid in requested if qid in eligible and qid in score_index]
    else:
        selected_qids = [qid for qid in score_qids if qid in eligible]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with args.output.open("w", encoding="utf-8") as fh:
        for qid in selected_qids:
            rows = _votes_for_query(
                qid,
                score_index[qid],
                top_k=args.top_k,
                vote_weight_scheme=args.vote_weight_scheme,
                min_vote_margin=args.min_vote_margin,
                abstain_missing=args.abstain_missing,
                min_support=args.min_support,
                min_aggregate_margin=args.min_aggregate_margin,
            )
            for row in rows:
                fh.write(json.dumps(row) + "\n")
                n_rows += 1

    print(f"[build_votes_file] dataset={args.dataset}")
    print(f"[build_votes_file] score_files={len(args.score_files)}")
    print(f"[build_votes_file] selected_queries={len(selected_qids)}")
    print(f"[build_votes_file] wrote_rows={n_rows}")
    print(
        "[build_votes_file] vote_cfg="
        f"weight={args.vote_weight_scheme}, min_vote_margin={args.min_vote_margin}, "
        f"abstain_missing={args.abstain_missing}, min_support={args.min_support}, "
        f"min_aggregate_margin={args.min_aggregate_margin}"
    )
    print(f"[build_votes_file] output={args.output}")
    if args.query_id_file is not None:
        print(f"[build_votes_file] query_id_file={args.query_id_file}")


if __name__ == "__main__":
    main()
