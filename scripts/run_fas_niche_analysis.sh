#!/bin/bash
# Run FAS niche analysis for fiqa and scidocs (top_k=20, 50)
set -e
cd "$(dirname "$0")/.."
for dataset in fiqa scidocs; do
  for k in 20 50; do
    echo "=== $dataset top_k=$k ==="
    python3 scripts/analyze_fas_niche.py --dataset "$dataset" --top-k "$k" --max-queries 50 --mode summed_margin
  done
done
