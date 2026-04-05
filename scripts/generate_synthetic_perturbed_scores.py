#!/usr/bin/env python
"""
generate_synthetic_perturbed_scores.py
======================================
Generate a SYNTHETIC second scorer by perturbing BM25 rankings in a reproducible way.

This creates meaningful disagreement with BM25 so multi-scorer aggregation can produce
cycles. Use for pipeline testing when a real second scorer (dense, cross-encoder) is
not available.

Output: data/processed/<dataset>/scores/synthetic_perturbed.jsonl

Usage
-----
::

    python scripts/generate_synthetic_perturbed_scores.py --dataset fiqa --top-k 100
    python scripts/generate_synthetic_perturbed_scores.py --dataset scidocs --top-k 100

Then run multi-scorer experiment:
    python scripts/run_real_experiment.py --dataset fiqa --preference-source multi_scores \\
        --scorers bm25,synthetic_perturbed --multi-score-weight-mode majority_vote
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_score_rankings, save_score_rankings


def perturb_ranking(
    candidates: list[tuple[str, float]],
    swap_prob: float,
    seed: int,
) -> list[tuple[str, float]]:
    """Perturb ranking by swapping adjacent pairs with probability swap_prob.

    After perturbation, assigns new scores using linear interpolation in [lo, hi]
    so the synthetic scorer has different scores from BM25. This creates real
    disagreement for multi-scorer aggregation (cycles possible with
    summed_margin / vote_plus_margin).

    Rank 1 (best) gets score ``hi`` and rank n (worst) gets exactly ``lo``.
    """
    rng = random.Random(seed)
    result = [(doc_id, score) for doc_id, score in candidates]
    # Multiple passes of adjacent swaps to create inversions
    for _ in range(3):
        for i in range(len(result) - 1):
            if rng.random() < swap_prob:
                result[i], result[i + 1] = result[i + 1], result[i]
    # Assign scores in same range as BM25 so both scorers can "win" when they disagree.
    # Linear interpolation: rank 1 gets hi, rank n gets lo.
    bm25_scores = [s for _, s in candidates]
    lo, hi = min(bm25_scores), max(bm25_scores)
    if hi <= lo:
        hi = lo + 1.0
    n = len(result)
    denom = max(n - 1, 1)
    return [
        (doc_id, lo + (hi - lo) * (n - 1 - r) / denom)
        for r, (doc_id, _) in enumerate(result)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic perturbed scores from BM25 (reproducible, for multi-scorer testing).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=["fiqa", "scidocs"],
        help="Dataset to process.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of top candidates per query.",
    )
    parser.add_argument(
        "--swap-prob",
        type=float,
        default=0.4,
        help="Probability of swapping each adjacent pair (higher = more disagreement, cycles).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing file.",
    )
    args = parser.parse_args()

    cfg = get_config(args.dataset)
    scores_dir = cfg.processed_path / "scores"
    bm25_path = scores_dir / "bm25.jsonl"
    out_path = scores_dir / "synthetic_perturbed.jsonl"

    if not bm25_path.exists():
        print(f"ERROR: BM25 scores not found at {bm25_path}")
        print("Run first: python scripts/generate_bm25_scores.py --dataset", args.dataset)
        sys.exit(1)

    if out_path.exists() and not args.force:
        print(f"[{args.dataset}] File exists: {out_path}. Use --force to overwrite.")
        sys.exit(0)

    print(f"[{args.dataset}] Loading BM25 scores from {bm25_path}...")
    bm25_rankings = load_score_rankings(bm25_path)

    perturbed: dict[str, list[tuple[str, float]]] = {}
    for qid, candidates in bm25_rankings.items():
        top = candidates[: args.top_k]
        # Use query_id in seed so different queries get different perturbations (deterministic)
        qseed = args.seed + sum(ord(c) for c in qid)
        perturbed[qid] = perturb_ranking(top, args.swap_prob, qseed)

    save_score_rankings(perturbed, out_path)
    print(f"[{args.dataset}] Wrote SYNTHETIC perturbed scores for {len(perturbed)} queries → {out_path}")
    print("  (Label: synthetic_perturbed — derived from BM25 with adjacent-pair swaps)")
    print(f"\nRun multi-scorer experiment with:")
    print(f"  python scripts/run_real_experiment.py --dataset {args.dataset} --preference-source multi_scores \\")
    print(f"    --scorers bm25,synthetic_perturbed --multi-score-weight-mode majority_vote --max-queries 50")


if __name__ == "__main__":
    main()
