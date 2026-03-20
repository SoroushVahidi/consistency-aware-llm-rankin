#!/bin/bash
# Run multi-scorer experiments for fiqa and scidocs.
# Scorers: bm25, synthetic_perturbed
# Aggregation: majority_vote, summed_margin, vote_plus_margin
# top_k: 20, 50

set -e
cd "$(dirname "$0")/.."

OUT=outputs/multi_scorer_experiments
mkdir -p "$OUT"

for dataset in fiqa scidocs; do
  for k in 20 50; do
    for mode in majority_vote summed_margin vote_plus_margin; do
      name="${dataset}_k${k}_${mode}"
      dir="$OUT/$name"
      mkdir -p "$dir"
      echo "=== $name ==="
      python3 scripts/run_real_experiment.py \
        --dataset "$dataset" \
        --preference-source multi_scores \
        --scorers bm25,synthetic_perturbed \
        --multi-score-weight-mode "$mode" \
        --top-k "$k" \
        --max-queries 50 \
        --output-dir "$dir" \
        2>&1 | tee "$dir/log.txt" || true
    done
  done
done

echo "Done. Results in $OUT"
