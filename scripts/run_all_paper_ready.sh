#!/bin/bash
# Run full paper-ready pipeline. Dense/cross-encoder generation can be slow for 200+ queries.
set -e
cd "$(dirname "$0")/.."

MAX_FIQA=${MAX_FIQA:-100}
MAX_SCIDOCS=${MAX_SCIDOCS:-100}

echo "=== Paper-ready experiments (FiQA n=$MAX_FIQA, SciDocs n=$MAX_SCIDOCS) ==="
echo "Set MAX_FIQA=300 MAX_SCIDOCS=200 for scale-up (requires dense/cross_encoder scores first)"

# Ensure BM25 exists (required for dense rerank-from)
for dataset in fiqa scidocs; do
  max=$([ "$dataset" = "fiqa" ] && echo $MAX_FIQA || echo $MAX_SCIDOCS)
  path="data/processed/beir/$dataset/scores/bm25.jsonl"
  if [ ! -f "$path" ] || [ $(wc -l < "$path" 2>/dev/null || echo 0) -lt $max ]; then
    echo "Generating BM25 for $dataset (max $max)..."
    python3 scripts/generate_bm25_scores.py --dataset "$dataset" --top-k 100 --max-queries $max --force
  fi
done

# Ensure dense exists
for dataset in fiqa scidocs; do
  max=$([ "$dataset" = "fiqa" ] && echo $MAX_FIQA || echo $MAX_SCIDOCS)
  path="data/processed/beir/$dataset/scores/dense.jsonl"
  if [ ! -f "$path" ] || [ $(wc -l < "$path" 2>/dev/null || echo 0) -lt $max ]; then
    echo "Generating dense for $dataset (max $max)..."
    python3 scripts/generate_dense_scores.py --dataset "$dataset" --top-k 50 --max-queries $max --rerank-from bm25 --force
  fi
done

echo ""
echo "=== 2-scorer experiments ==="
python3 scripts/run_paper_ready_experiments.py --dataset fiqa --max-queries $MAX_FIQA --scorers bm25,dense --examples 8
python3 scripts/run_paper_ready_experiments.py --dataset scidocs --max-queries $MAX_SCIDOCS --scorers bm25,dense --examples 8

echo ""
echo "=== 3-scorer (if cross_encoder exists) ==="
if [ -f "data/processed/beir/fiqa/scores/cross_encoder.jsonl" ]; then
  python3 scripts/run_paper_ready_experiments.py --dataset fiqa --max-queries $MAX_FIQA --scorers bm25,dense,cross_encoder --examples 8
fi
if [ -f "data/processed/beir/scidocs/scores/cross_encoder.jsonl" ]; then
  python3 scripts/run_paper_ready_experiments.py --dataset scidocs --max-queries $MAX_SCIDOCS --scorers bm25,dense,cross_encoder --examples 8
fi

echo ""
echo "Done. See outputs/paper_ready/ and PAPER_READY_REPORT.md"
