#!/bin/bash
# Run expanded selective-repair experiments (2-scorer and 3-scorer)
set -e
cd "$(dirname "$0")/.."

echo "=== Generating cross-encoder scores (if needed) ==="
for dataset in fiqa scidocs; do
  if [ ! -f "data/processed/beir/$dataset/scores/cross_encoder.jsonl" ]; then
    python3 scripts/generate_cross_encoder_scores.py --dataset "$dataset" --top-k 20 --max-queries 100
  fi
done

echo ""
echo "=== 2-scorer experiments (bm25 + dense) ==="
for dataset in fiqa scidocs; do
  python3 scripts/run_expanded_selective_repair.py --dataset "$dataset" --max-queries 100 --scorers bm25,dense
done

echo ""
echo "=== 3-scorer experiments (bm25 + dense + cross_encoder) ==="
for dataset in fiqa scidocs; do
  python3 scripts/run_expanded_selective_repair.py --dataset "$dataset" --max-queries 100 --scorers bm25,dense,cross_encoder
done

echo ""
echo "Done. See outputs/expanded_selective/ and EXPANDED_SELECTIVE_REPORT.md"
