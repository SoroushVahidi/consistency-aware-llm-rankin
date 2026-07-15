"""
build_votes_file.py
===================
Build pairwise vote edges from multiple ranker score files.

Output schema (one row per ranker-vote pair):
{"query_id":"...","winner_doc_id":"...","loser_doc_id":"...","weight":<float>,"voter":"..."}

**Why ``votes_file`` graphs are often acyclic:** for each unordered document
pair, votes are grouped by *direction* (winner → loser). Only directions with
``--min-support`` rankers and sufficient ``--min-aggregate-margin`` are kept.
With ``--min-support 2`` and three similar rankers (e.g. BM25, TF‑IDF, MiniLM),
one direction usually dominates every pair, so the merged graph is close to a
**total order** (DAG). Use ``--min-support 1`` to emit each ranker's direction,
allowing **both** orientations when rankers disagree (2-cycles and longer cycles
become possible). See also ``scripts/diagnose_vote_graph_cycles.py``.
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
from consistency_ranker.data.dataset_registry import DATASET_NAMES  # noqa: E402
from consistency_ranker.data.unified_loader import load_dataset_splits  # noqa: E402


def _candidate_aligned_rel_map(qrels_for_query: list, candidates: list[str]) -> dict[str, int]:
    rel_map: dict[str, int] = {}
    for e in qrels_for_query:
        rel_map[e.doc_id] = max(rel_map.get(e.doc_id, e.relevance), e.relevance)
    for d in candidates:
        rel_map.setdefault(d, 0)
    return rel_map


def _ndcg_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float:
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return 0.0

    def _dcg(items: list[str]) -> float:
        total = 0.0
        for i, doc_id in enumerate(items[:k_eff]):
            rel = rel_map.get(doc_id, 0)
            total += (2.0 ** rel - 1.0) / math.log2(i + 2.0)
        return total

    dcg = _dcg(ranking)
    ideal = sorted(ranking, key=lambda d: rel_map.get(d, 0), reverse=True)
    idcg = _dcg(ideal)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def _precision_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float:
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return 0.0
    hits = sum(1 for d in ranking[:k_eff] if rel_map.get(d, 0) > 0)
    return hits / k_eff


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
    """Select top-k candidate docs using reciprocal-rank fusion.

    DUPLICATE IMPLEMENTATION, confirmed byte-for-byte identical to
    reports/full_calibrated_core/scripts/run_phase0_phase1._select_candidates
    (see reports/candidate_pool_conditional_audit_20260714/AUDIT.md
    section 1). Kept here unmodified because this script's own output
    (pre-built vote files under experiments/.../inputs/<dataset>/) is a
    committed artifact other diagnostic phases already depend on, and the
    canonical full_calibrated_core pipeline does not read those files back
    for its own pool computation -- it always recomputes fresh. Any new
    candidate-pool policy work should extend
    reports/full_calibrated_core/scripts/candidate_pool_policies.py
    (the reusable, typed policy registry) rather than adding a third copy
    of this function.
    """
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
    ranker_weights: dict[str, float] | None = None,
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
        voter_weight = (ranker_weights or {}).get(voter, 1.0)
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
            base_weight = margin if vote_weight_scheme == "margin" else 1.0
            weight = base_weight * voter_weight
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


def _load_ranker_weights_file(path: Path) -> dict[str, float]:
    if not path.exists():
        raise FileNotFoundError(f"Ranker weights file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Ranker weights file must be a JSON object: {ranker: weight}.")
    out: dict[str, float] = {}
    for k, v in raw.items():
        out[str(k)] = float(v)
    return out


def _derive_ranker_weights(
    *,
    score_index: dict[str, dict[str, dict[str, float]]],
    qrels_by_query: dict[str, list],
    selected_qids: list[str],
    top_k: int,
    weighting_mode: str,
    floor: float,
) -> dict[str, float]:
    """Derive ranker weights from candidate-aligned quality."""
    if weighting_mode not in {"auto_ndcg_at_k", "auto_precision_at_k"}:
        raise ValueError(f"Unsupported weighting mode: {weighting_mode}")

    rankers = sorted(
        {
            ranker
            for qid in selected_qids
            for ranker in score_index.get(qid, {})
        }
    )
    quality: dict[str, list[float]] = {r: [] for r in rankers}
    for qid in selected_qids:
        qrels_for_query = qrels_by_query.get(qid, [])
        for ranker in rankers:
            score_map = score_index.get(qid, {}).get(ranker)
            if not score_map:
                continue
            ranking = [d for d, _ in sorted(score_map.items(), key=lambda x: (-x[1], x[0]))[:top_k]]
            rel_map = _candidate_aligned_rel_map(qrels_for_query, ranking)
            if weighting_mode == "auto_ndcg_at_k":
                val = _ndcg_at_k(ranking, rel_map, k=top_k)
            else:
                val = _precision_at_k(ranking, rel_map, k=top_k)
            quality[ranker].append(val)

    avg_quality: dict[str, float] = {}
    for ranker in rankers:
        vals = quality[ranker]
        avg_quality[ranker] = sum(vals) / len(vals) if vals else 0.0

    raw = {r: max(avg_quality[r], floor) for r in rankers}
    if not raw:
        return {}
    mean_val = sum(raw.values()) / len(raw)
    if mean_val <= 0:
        return {r: 1.0 for r in raw}
    return {r: v / mean_val for r, v in raw.items()}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build pairwise vote edges from multiple score files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=sorted(DATASET_NAMES),
    )
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
    parser.add_argument(
        "--ranker-weighting",
        type=str,
        default="none",
        choices=["none", "auto_ndcg_at_k", "auto_precision_at_k", "from_file"],
        help="Optional ranker weighting mode for vote weights.",
    )
    parser.add_argument(
        "--ranker-weights-file",
        type=Path,
        default=None,
        help="JSON file with ranker weights when --ranker-weighting from_file.",
    )
    parser.add_argument(
        "--ranker-weight-floor",
        type=float,
        default=1e-6,
        help="Minimum floor used when auto-deriving ranker weights.",
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
    qrels_by_query: dict[str, list] = defaultdict(list)
    for e in qrels:
        qrels_by_query[e.query_id].append(e)
    eligible = set(eligible_query_ids(qrels))

    score_index = _load_scores(args.score_files)
    score_qids = sorted(score_index.keys())

    if args.query_id_file is not None:
        requested = load_query_ids_file(args.query_id_file)
        selected_qids = [qid for qid in requested if qid in eligible and qid in score_index]
    else:
        selected_qids = [qid for qid in score_qids if qid in eligible]

    ranker_weights: dict[str, float] | None = None
    if args.ranker_weighting == "from_file":
        if args.ranker_weights_file is None:
            raise ValueError("--ranker-weights-file is required when --ranker-weighting from_file.")
        ranker_weights = _load_ranker_weights_file(args.ranker_weights_file)
    elif args.ranker_weighting in {"auto_ndcg_at_k", "auto_precision_at_k"}:
        ranker_weights = _derive_ranker_weights(
            score_index=score_index,
            qrels_by_query=qrels_by_query,
            selected_qids=selected_qids,
            top_k=args.top_k,
            weighting_mode=args.ranker_weighting,
            floor=args.ranker_weight_floor,
        )

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
                ranker_weights=ranker_weights,
            )
            for row in rows:
                fh.write(json.dumps(row) + "\n")
                n_rows += 1

    print(f"[build_votes_file] dataset={args.dataset}")
    print(f"[build_votes_file] score_files={len(args.score_files)}")
    print(f"[build_votes_file] selected_queries={len(selected_qids)}")
    print(f"[build_votes_file] wrote_rows={n_rows}")
    print(f"[build_votes_file] ranker_weighting={args.ranker_weighting}")
    if ranker_weights:
        print(f"[build_votes_file] ranker_weights={json.dumps(ranker_weights, sort_keys=True)}")
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
