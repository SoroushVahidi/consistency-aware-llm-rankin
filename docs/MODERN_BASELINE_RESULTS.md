# Modern Baseline Results

> **Generated:** 2026-03-24
> **Status:** Final — all numbers are from full real experiments

---

## 1. Result Status Classification

### (A) Full Real Results

| Baseline | Datasets | Queries | Status |
|----------|----------|---------|--------|
| cross_encoder (ms-marco-MiniLM-L-6-v2) | SciDocs, HotpotQA, BRIGHT | 500, 498, 197 | **FULL** |
| bt_from_qrels (Bradley-Terry MLE) | SciDocs, HotpotQA, BRIGHT | 500, 497, 71 | **FULL** |
| win_rate_from_qrels | SciDocs, HotpotQA, BRIGHT | 500, 497, 71 | **FULL** |
| markov_from_qrels (Markov chain) | SciDocs, HotpotQA, BRIGHT | 500, 497, 71 | **FULL** |
| tournament_sort_from_qrels | SciDocs, HotpotQA, BRIGHT | 500, 497, 71 | **FULL** |
| Existing pipeline (12 methods) | SciDocs, HotpotQA, BRIGHT | 500, 497, 71 | **FULL** |
| Noise sensitivity (7 levels × 11 methods) | SciDocs, HotpotQA | 500, 497 | **FULL** |
| Bootstrap CIs (2000 replications) | SciDocs, HotpotQA | 500, 497 | **FULL** |

### (B) Not Available

| Baseline | Reason |
|----------|--------|
| LLM pointwise | No API key (`OPENAI_API_KEY` not set) |
| LLM pairwise | No API key |
| LLM listwise (RankGPT-style) | No API key |

### (C) Not Applicable

| Dataset | Reason |
|---------|--------|
| FiQA | All qrels have grade=1 only; no ranking differentiation possible |

---

## 2. Main Comparison Table — Clean Preferences (qrels)

Methods ranked by nDCG@k within each dataset.

### SciDocs (500 queries, top-k=20)

| Method | nDCG@20 | MAP@20 | Type |
|--------|---------|--------|------|
| score_sum | 1.0000 | 1.0000 | Existing |
| borda | 1.0000 | 1.0000 | Existing |
| BT MLE | 1.0000 | 1.0000 | **New** |
| win_rate | 1.0000 | 1.0000 | **New** |
| Markov chain | 1.0000 | 1.0000 | **New** |
| hybrid_rrf_fas_regularized | 1.0000 | 1.0000 | Existing |
| FAS copeland | 0.9994 | 0.9983 | Existing |
| FAS topological | 0.9552 | 0.8872 | Existing |
| PageRank | 0.9478 | 0.9060 | Existing |
| **cross_encoder** | **0.8977** | **0.7807** | **New** |
| tournament sort | 0.8059 | 0.6518 | **New** |

### HotpotQA (497 queries, top-k=10)

| Method | nDCG@10 | MAP@10 | Type |
|--------|---------|--------|------|
| score_sum | 1.0000 | 1.0000 | Existing |
| BT MLE | 1.0000 | 1.0000 | **New** |
| win_rate | 1.0000 | 1.0000 | **New** |
| Markov chain | 1.0000 | 1.0000 | **New** |
| tournament sort | 1.0000 | 1.0000 | **New** |
| FAS copeland | 0.9948 | 0.9920 | Existing |
| PageRank | 0.9900 | 0.9841 | Existing |
| **cross_encoder** | **0.9499** | **0.9241** | **New** |
| FAS topological | 0.8386 | 0.7756 | Existing |

### BRIGHT (71 queries, top-k=20)

| Method | nDCG@20 | MAP@20 | Type |
|--------|---------|--------|------|
| score_sum | 1.0000 | 1.0000 | Existing |
| BT MLE | 1.0000 | 1.0000 | **New** |
| Markov chain | 1.0000 | 1.0000 | **New** |
| FAS copeland | 0.9989 | 0.9974 | Existing |
| PageRank | 0.9704 | 0.9553 | Existing |
| **cross_encoder** | **0.8877** | **0.8424** | **New** |
| FAS topological | 0.8562 | 0.7863 | Existing |
| tournament sort | 0.6999 | 0.5776 | **New** |

---

## 3. Noise Sensitivity (nDCG@k at multiple flip probabilities)

### SciDocs (500 queries, top-k=20)

| Method | 0% | 5% | 10% | 15% | 20% | 25% | 30% |
|--------|----|----|-----|-----|-----|-----|-----|
| score_sum | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| FAS-balance | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 | 0.96 |
| win_rate | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.98 | 0.94 |
| Copeland (unrep.) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 |
| BT MLE | 1.00 | 0.99 | 0.97 | 0.95 | 0.92 | 0.88 | 0.83 |
| FAS topological | 1.00 | 0.98 | 0.96 | 0.94 | 0.92 | 0.89 | 0.85 |
| tournament sort | 0.81 | 0.78 | 0.76 | 0.73 | 0.71 | 0.68 | 0.66 |

### HotpotQA (497 queries, top-k=10)

| Method | 0% | 5% | 10% | 15% | 20% | 25% | 30% |
|--------|----|----|-----|-----|-----|-----|-----|
| score_sum | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| FAS-balance | 1.00 | 1.00 | 1.00 | 0.99 | 0.96 | 0.92 | 0.85 |
| PageRank/Markov | 1.00 | 0.99 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| Copeland (unrep.) | 1.00 | 1.00 | 1.00 | 0.99 | 0.97 | 0.93 | 0.87 |
| BT MLE | 1.00 | 0.89 | 0.80 | 0.73 | 0.67 | 0.61 | 0.56 |
| FAS topological | 1.00 | 0.88 | 0.77 | 0.68 | 0.61 | 0.56 | 0.52 |
| tournament sort | 1.00 | 0.94 | 0.87 | 0.81 | 0.76 | 0.70 | 0.65 |

---

## 4. Bootstrap Confidence Intervals (95%)

### SciDocs, 15% noise

| Comparison | Δ nDCG | 95% CI | Sig. |
|------------|--------|--------|------|
| FAS-balance vs BT MLE | +0.049 | [+0.044, +0.054] | *** |
| FAS-balance vs win-rate | +0.001 | [+0.000, +0.002] | *** |
| FAS-balance vs Markov | +0.069 | [+0.062, +0.077] | *** |
| FAS-copeland vs BT MLE | +0.049 | [+0.044, +0.054] | *** |
| score_sum vs BT MLE | +0.050 | [+0.045, +0.055] | *** |
| score_sum vs tournament sort | +0.272 | [+0.260, +0.285] | *** |

### HotpotQA, 15% noise

| Comparison | Δ nDCG | 95% CI | Sig. |
|------------|--------|--------|------|
| FAS-balance vs BT MLE | +0.264 | [+0.246, +0.282] | *** |
| FAS-balance vs win-rate | +0.232 | [+0.212, +0.251] | *** |
| score_sum vs BT MLE | +0.275 | [+0.257, +0.293] | *** |
| score_sum vs tournament sort | +0.190 | [+0.171, +0.210] | *** |

---

## 5. Cross-Encoder as External Reference

The cross-encoder (`ms-marco-MiniLM-L-6-v2`) provides the only fully
text-aware external baseline:

| Dataset | cross_encoder nDCG | Best graph method nDCG | Gap |
|---------|-------------------|----------------------|-----|
| SciDocs | 0.8977 | 1.0000 (score_sum) | +0.102 |
| HotpotQA | 0.9499 | 1.0000 (score_sum) | +0.050 |
| BRIGHT | 0.8877 | 1.0000 (score_sum) | +0.112 |

Note: Graph methods achieve nDCG=1.0 because they use qrels-derived
(perfect) preferences. The cross-encoder uses document text only and
does not have access to relevance labels.

---

## 6. Provenance Notes

| Baseline | Label | Source | Model / Algorithm |
|----------|-------|--------|-------------------|
| cross_encoder | Tier A: official pre-trained model | sentence-transformers | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| bt_from_qrels | Tier A: classical algorithm | Bradley & Terry (1952) | MM algorithm MLE |
| win_rate_from_qrels | Tier A: classical algorithm | Social choice theory | win/(win+loss) fraction |
| markov_from_qrels | Tier A: classical algorithm | Dwork et al. (2001) | PageRank on preference graph |
| tournament_sort_from_qrels | Tier A: classical algorithm | Standard comp. sort | merge-sort with pairwise comparator |
| llm_pointwise | Tier B: not yet run | Standard practice | Requires API key |
| llm_pairwise | Tier B: not yet run | PRP (Qin et al., 2023) | Requires API key |
| llm_listwise | Tier B: not yet run | RankGPT (Sun et al., 2023) | Requires API key |
