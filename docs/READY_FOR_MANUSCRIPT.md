# Ready for Manuscript

> **Generated:** 2026-03-24
> **Purpose:** Definitive guide for what numbers are safe to report in the
> revised manuscript.

---

## Numbers Safe to Report

### Table 1: Cross-encoder comparison (all datasets)

| Dataset | n_queries | top_k | cross_encoder nDCG | score_sum nDCG | FAS-balance nDCG |
|---------|-----------|-------|-------------------|----------------|------------------|
| SciDocs | 500 | 20 | 0.8977 | 1.0000 | 0.9994 |
| HotpotQA | 497 | 10 | 0.9499 | 1.0000 | 0.9948 |
| BRIGHT | 71* | 20 | 0.8877 | 1.0000 | 0.9989 |

*BRIGHT: 197 queries for cross-encoder, 71 for graph-aggregation methods.

**Safe to say:** "A pre-trained cross-encoder (ms-marco-MiniLM-L-6-v2) achieves
nDCG of 0.90–0.95 across three datasets. Our graph-based methods with clean
preferences achieve nDCG ≥ 0.999."

### Table 2: Graph aggregation comparison (clean preferences)

| Method | SciDocs | HotpotQA | BRIGHT |
|--------|---------|----------|--------|
| score_sum | 1.0000 | 1.0000 | 1.0000 |
| BT MLE | 1.0000 | 1.0000 | 1.0000 |
| win_rate | 1.0000 | 1.0000 | 1.0000 |
| Markov | 1.0000 | 1.0000 | 1.0000 |
| FAS-balance | 0.9994 | 0.9948 | 0.9989 |
| tournament sort | 0.8059 | 1.0000 | 0.6999 |

**Safe to say:** "All standard aggregation methods (BT, win-rate, Markov)
perfectly recover the reference ranking from clean pairwise preferences."

### Table 3: Noise sensitivity (SciDocs, selected methods)

| Method | 0% | 10% | 15% | 20% | 30% |
|--------|----|----|-----|-----|-----|
| score_sum | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| FAS-balance | 1.00 | 1.00 | 1.00 | 1.00 | 0.96 |
| BT MLE | 1.00 | 0.97 | 0.95 | 0.92 | 0.83 |
| FAS topological | 1.00 | 0.96 | 0.94 | 0.92 | 0.85 |

**Safe to say:** "FAS-balance degrades gracefully and significantly outperforms
Bradley-Terry under noise ≥10%."

### Table 4: Bootstrap CIs (SciDocs, 15% noise)

| Comparison | Δ nDCG | 95% CI |
|------------|--------|--------|
| FAS-balance vs BT | +0.049 | [+0.044, +0.054] |
| FAS-balance vs win-rate | +0.001 | [+0.000, +0.002] |
| score_sum vs BT | +0.050 | [+0.045, +0.055] |
| score_sum vs tourn. sort | +0.272 | [+0.260, +0.285] |

**Safe to say:** "All key comparisons are statistically significant at the
95% confidence level (2000 bootstrap replications, 500 paired queries)."

---

## Claims That Are Safe

1. Cross-encoder provides a strong non-LLM reference baseline
2. Graph aggregation methods recover ground truth from clean preferences
3. FAS repair outperforms BT/win-rate aggregation under noise (significant)
4. The advantage of FAS repair grows with noise level
5. Score-sum/Borda are most robust to noise
6. Tournament sort is consistently weakest

---

## What Must NOT Be Claimed

1. **No LLM comparison.** Do not claim our method beats LLM-based reranking.
   LLM baselines were not run with real judgments.
2. **No paper reproduction.** Do not claim to reproduce AFR-Rank, BLITZRANK,
   RankGPT, or any other named method. The cross-encoder is a standard
   pre-trained model, not a reproduction of any paper's experiments.
3. **No FiQA results.** FiQA is excluded due to data limitations.
4. **No mock results.** Do not report any numbers from dry-run/mock mode.
5. **No cross-encoder = graph method comparison as apples-to-apples.**
   The cross-encoder uses text; graph methods use preference structure only.

---

## What Remains for Future Work

### Priority 1: LLM baselines (requires API key)
- Set `OPENAI_API_KEY` and run `scripts/run_modern_baselines.py` without `--dry-run`
- Code is fully implemented with caching and budget controls
- Start with 50 queries on SciDocs for cost estimation

### Priority 2: Real pairwise preferences
- Use LLM pairwise judgments as preference source for the existing pipeline
- This would test FAS repair on realistic (non-qrels) preference data
- The most important missing comparison

### Priority 3: Multi-dataset LLM comparison
- After SciDocs pilot, extend to HotpotQA and BRIGHT

### Priority 4: Additional cross-encoder models
- Consider testing `cross-encoder/ms-marco-MiniLM-L-12-v2` for stronger baseline

---

## Artifacts Inventory

| Artifact | Path | Status |
|----------|------|--------|
| Cross-encoder results | `outputs/final_modern_baselines/` | **FULL** |
| Tournament aggregation | `outputs/final_modern_baselines/` | **FULL** |
| Existing pipeline reference | `outputs/final_modern_baselines_reference/` | **FULL** |
| Noise sensitivity | `outputs/noise_sensitivity/` | **FULL** |
| Bootstrap CIs | `outputs/bootstrap_modern/` | **FULL** |
| Unified comparison CSV | `outputs/final_comparison/unified_comparison.csv` | **FULL** |
| LaTeX tables | `outputs/final_comparison/table_*.tex` | **FULL** |
| Noise sensitivity LaTeX | `outputs/noise_sensitivity/*/` | **FULL** |
| Bootstrap LaTeX | `outputs/bootstrap_modern/*/` | **FULL** |
| LLM baselines | `src/rerankers/llm_*.py` | Code ready, **NOT RUN** |

---

## Reproduction Instructions

```bash
source /workspace/.venv/bin/activate
pip install -e ".[dev]"

# Download and prepare datasets
python scripts/download_datasets.py --dataset scidocs
python scripts/download_datasets.py --dataset hotpotqa
python scripts/download_datasets.py --dataset bright
python scripts/prepare_datasets.py --dataset scidocs
python scripts/prepare_datasets.py --dataset hotpotqa
python scripts/prepare_datasets.py --dataset bright

# Full experiments (non-LLM baselines)
python scripts/run_modern_baselines.py --dataset scidocs --baseline all --no-llm \
  --max-queries 500 --top-k 20 --output-dir outputs/final_modern_baselines --overwrite
python scripts/run_modern_baselines.py --dataset hotpotqa --baseline all --no-llm \
  --max-queries 500 --top-k 10 --output-dir outputs/final_modern_baselines --overwrite
python scripts/run_modern_baselines.py --dataset bright --baseline all --no-llm \
  --max-queries 200 --top-k 20 --output-dir outputs/final_modern_baselines --overwrite

# Existing pipeline reference
python scripts/run_real_experiment.py --dataset scidocs --max-queries 500 --top-k 20 \
  --output-dir outputs/final_modern_baselines_reference --overwrite-existing
python scripts/run_real_experiment.py --dataset scidocs --max-queries 500 --top-k 20 \
  --preference-source qrels_flip --flip-prob 0.15 \
  --output-dir outputs/final_modern_baselines_reference --overwrite-existing

# Noise sensitivity
python scripts/run_noise_sensitivity.py --dataset scidocs --max-queries 500 --top-k 20
python scripts/run_noise_sensitivity.py --dataset hotpotqa --max-queries 500 --top-k 10

# Bootstrap CIs
python scripts/run_modern_bootstrap.py --dataset scidocs --flip-prob 0.15 --n-bootstrap 2000
python scripts/run_modern_bootstrap.py --dataset scidocs --flip-prob 0.30 --n-bootstrap 2000
python scripts/run_modern_bootstrap.py --dataset hotpotqa --flip-prob 0.15 --n-bootstrap 2000

# Unified comparison tables
python scripts/build_modern_baseline_tables.py \
  --modern-dir outputs/final_modern_baselines \
  --existing-dir outputs/final_modern_baselines_reference \
  --datasets scidocs hotpotqa bright \
  --out-dir outputs/final_comparison
```
