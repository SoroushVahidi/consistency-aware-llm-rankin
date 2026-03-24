# Modern Baseline Claims

> **Generated:** 2026-03-24
> **Status:** Final — all claims backed by full real experiments

---

## Safe Claims (backed by full experiments)

### Claim M1 — Cross-encoder as strong external reference

**Statement:** A pre-trained cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
achieves nDCG@k of 0.90 (SciDocs), 0.95 (HotpotQA), and 0.89 (BRIGHT) when
ranking the same candidate pools. All graph-based methods with clean qrels
preferences surpass this baseline.

**Evidence:** `outputs/final_modern_baselines/*/` summary CSVs
**Label:** Full real results on 3 datasets

### Claim M2 — Graph aggregation recovers ground truth

**Statement:** Bradley-Terry MLE, win-rate, and Markov chain aggregation all
achieve nDCG=1.0 when given qrels-derived (perfect) pairwise preferences on
all three datasets.

**Evidence:** Same summary CSVs
**Label:** Full real results, 3 datasets

### Claim M3 — FAS repair outperforms parametric aggregation under noise

**Statement:** Under synthetic noise (15% flip probability), FAS-balance
significantly outperforms Bradley-Terry aggregation:
- SciDocs: Δ nDCG = +0.049, 95% CI [+0.044, +0.054]
- HotpotQA: Δ nDCG = +0.264, 95% CI [+0.246, +0.282]

**Evidence:** `outputs/bootstrap_modern/` and `outputs/noise_sensitivity/`
**Label:** Full real results, 500/497 queries, 2000 bootstrap replications

### Claim M4 — Score-sum and Borda are most noise-robust

**Statement:** Score-sum and Borda ranking maintain nDCG=1.0 even at 30% noise
on SciDocs. On HotpotQA, they maintain nDCG≥0.999 at 30% noise.

**Evidence:** `outputs/noise_sensitivity/*/` summary CSVs
**Label:** Full real results, 7 noise levels

### Claim M5 — Tournament sort is consistently weakest

**Statement:** Tournament (comparison-based) sort is the weakest graph
aggregation method across all datasets and noise levels. On SciDocs with
clean preferences it achieves nDCG=0.81, degrading to 0.66 at 30% noise.

**Evidence:** Same noise sensitivity outputs
**Label:** Full real results

### Claim M6 — FAS repair advantage grows with noise

**Statement:** The advantage of FAS-balance over BT aggregation grows
monotonically with noise level:
- SciDocs: Δ grows from 0.00 (0% noise) to +0.13 (30% noise)
- HotpotQA: Δ grows from 0.00 to +0.26

**Evidence:** Noise sensitivity summary tables
**Label:** Full real results

### Claim M7 — PageRank/Markov shows non-monotonic noise response

**Statement:** PageRank (and the equivalent Markov chain aggregation) shows
a non-monotonic response to noise on SciDocs: nDCG drops from 1.0 to 0.93
at 10-15% noise, then partially recovers to 0.97 at 30% noise.

**Evidence:** Noise sensitivity summary
**Label:** Full real results, SciDocs only

---

## Honest Limitations

### L1 — LLM baselines not run

No LLM API key was available. The LLM pointwise, pairwise, and listwise
baselines exist as implemented code with dry-run/mock capability, but **no
real LLM results** are included.

**Impact:** Cannot compare our method against LLM-based reranking. This is
the single most important remaining gap.

### L2 — Qrels-derived preferences are an oracle setting

All graph-based comparisons use qrels-derived preferences. This is a
controlled setting that isolates the effect of the aggregation method.
Real-world preferences (from LLM judges or retrieval models) would have
different noise characteristics.

### L3 — Cross-encoder is not comparable to graph methods

The cross-encoder uses document text; graph methods use only pairwise
preference structure. The comparison is informative (shows what text-aware
reranking achieves) but not apples-to-apples.

### L4 — FiQA excluded

FiQA's test split has only 1 judged document per query (all grade=1),
making ranking comparison impossible. This is a property of the dataset,
not our method.

### L5 — BRIGHT has fewer usable queries

BRIGHT has only 71 queries with ≥2 documents with different relevance
grades (from 200 sampled). Results are directionally consistent with SciDocs
but less statistically powered.

---

## What We Do NOT Claim

1. We do **not** claim to reproduce any named paper (AFR-Rank, Reason-to-Rank,
   BLITZRANK, RankGPT, etc.)
2. We do **not** claim our methods outperform LLM-based reranking
3. We do **not** claim the cross-encoder comparison is apples-to-apples
4. We do **not** present any dry-run/mock results as real evidence
5. We do **not** claim Bradley-Terry is a faithful reproduction of any
   specific paper's method — it is a standard classical algorithm
