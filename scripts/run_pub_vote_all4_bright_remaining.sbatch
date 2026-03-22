#!/bin/bash
#SBATCH --job-name=pub-all4-bright
#SBATCH --output=/mmfs1/home/sv96/consistency-aware-llm-rankin/outputs/slurm/%x-%j.out
#SBATCH --error=/mmfs1/home/sv96/consistency-aware-llm-rankin/outputs/slurm/%x-%j.err
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G

set -euo pipefail

REPO="/mmfs1/home/sv96/consistency-aware-llm-rankin"
ROOT="${REPO}/outputs/pub_vote_cmp_all4"

mkdir -p "${REPO}/outputs/slurm"

source /apps/easybuild/software/Anaconda3/2023.09-0/etc/profile.d/conda.sh
conda activate feedback-weighted-maximization

cd "${REPO}"

python scripts/generate_score_file.py \
  --dataset bright \
  --ranker bm25 \
  --max-queries 50 \
  --top-n 50 \
  --seed 42 \
  --query-id-file outputs/pub_vote_cmp_all4/bright/query_ids.txt \
  --output outputs/pub_vote_cmp_all4/bright/scores_bm25.jsonl

python scripts/generate_score_file.py \
  --dataset bright \
  --ranker tfidf \
  --max-queries 50 \
  --top-n 50 \
  --seed 42 \
  --query-id-file outputs/pub_vote_cmp_all4/bright/query_ids.txt \
  --output outputs/pub_vote_cmp_all4/bright/scores_tfidf.jsonl

python scripts/build_votes_file.py \
  --dataset bright \
  --score-files outputs/pub_vote_cmp_all4/bright/scores_bm25.jsonl outputs/pub_vote_cmp_all4/bright/scores_tfidf.jsonl \
  --top-k 20 \
  --vote-weight-scheme margin \
  --min-vote-margin 0.05 \
  --abstain-missing \
  --query-id-file outputs/pub_vote_cmp_all4/bright/query_ids.txt \
  --min-support 2 \
  --min-aggregate-margin 0.1 \
  --output outputs/pub_vote_cmp_all4/bright/votes_ms2.jsonl

python scripts/build_votes_file.py \
  --dataset bright \
  --score-files outputs/pub_vote_cmp_all4/bright/scores_bm25.jsonl outputs/pub_vote_cmp_all4/bright/scores_tfidf.jsonl \
  --top-k 20 \
  --vote-weight-scheme margin \
  --min-vote-margin 0.05 \
  --abstain-missing \
  --query-id-file outputs/pub_vote_cmp_all4/bright/query_ids.txt \
  --min-support 1 \
  --min-aggregate-margin 0.0 \
  --output outputs/pub_vote_cmp_all4/bright/votes_ms1.jsonl

python scripts/postprocess_votes_drop_mutual_pairs.py \
  --input outputs/pub_vote_cmp_all4/bright/votes_ms1.jsonl \
  --output outputs/pub_vote_cmp_all4/bright/votes_ms1_drop_mutual.jsonl

for VAR in ms2 ms1 ms1_drop_mutual; do
  python scripts/run_real_experiment.py \
    --dataset bright \
    --preference-source votes_file \
    --pairwise-file "outputs/pub_vote_cmp_all4/bright/votes_${VAR}.jsonl" \
    --query-id-file outputs/pub_vote_cmp_all4/bright/query_ids.txt \
    --score-prior-files outputs/pub_vote_cmp_all4/bright/scores_bm25.jsonl outputs/pub_vote_cmp_all4/bright/scores_tfidf.jsonl \
    --max-queries 50 \
    --top-k 20 \
    --include-hybrid-ablation \
    --methods hybrid_rrf_prior_only hybrid_rrf_unrepaired_copeland_a03 hybrid_rrf_repaired_copeland_a03 hybrid_rrf_unrepaired_balance_a03 hybrid_rrf_repaired_balance_a03 \
    --save-timings \
    --no-plots \
    --output-dir "outputs/pub_vote_cmp_all4/bright/${VAR}" \
    --seed 42
done

mkdir -p "${ROOT}/analysis"
for DS in scidocs fiqa hotpotqa bright; do
  for VAR in ms2 ms1 ms1_drop_mutual; do
    CSV="${ROOT}/${DS}/${VAR}/${DS}/votes_file/${DS}_per_query.csv"
    if [[ ! -f "${CSV}" ]]; then
      echo "Skipping missing ${CSV}"
      continue
    fi
    python scripts/analyze_publication_vote_deltas.py \
      --per-query-csv "${CSV}" \
      --method-a hybrid_rrf_unrepaired_copeland_a03 \
      --method-b hybrid_rrf_repaired_copeland_a03 \
      --json-out "${ROOT}/analysis/${DS}_${VAR}_delta_copeland.json"
    python scripts/analyze_publication_vote_deltas.py \
      --per-query-csv "${CSV}" \
      --method-a hybrid_rrf_unrepaired_balance_a03 \
      --method-b hybrid_rrf_repaired_balance_a03 \
      --json-out "${ROOT}/analysis/${DS}_${VAR}_delta_balance.json"
  done
done

python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_all4
python scripts/summarize_publication_vote_suite.py --root outputs/pub_vote_cmp_all4 > outputs/pub_vote_cmp_all4/SUMMARY.md
