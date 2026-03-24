# Modern Baseline Claims

> **Generated:** 2026-03-24
> **Purpose:** What we can honestly claim about the new baselines.

---

## Safe Claims

### Claim M1 — Cross-encoder provides a strong non-LLM reference

**Statement:** A cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) achieves
nDCG@20 = 0.91 on SciDocs when ranking the same candidate pool used by our
graph-based methods. Our consistency-repair methods with clean preferences
surpass this baseline (nDCG = 1.0), and under 15% noisy preferences, our best
hybrid methods remain at or above the cross-encoder's quality (nDCG ≥ 0.92).

**Evidence:** `outputs/modern_baselines/scidocs/scidocs_modern_baselines_summary.csv`

### Claim M2 — Graph aggregation methods correctly recover ground-truth ranking

**Statement:** Bradley-Terry MLE, win-rate, and Markov chain aggregation all
achieve nDCG = 1.0 when applied to qrels-derived (perfect) pairwise preferences.
This confirms the aggregation methods are mathematically sound.

**Evidence:** Same summary CSV.

### Claim M3 — FAS repair adds value under noisy preferences

**Statement:** Under 15% random preference flips, FAS-repair methods maintain
higher nDCG than simple aggregation baselines. Specifically:
- score_sum/borda/FAS-balance: nDCG ≈ 1.0
- FAS topological: nDCG ≈ 0.91
- PageRank: nDCG ≈ 0.89

**Evidence:** `outputs/modern_baselines_reference/scidocs/qrels_flip/`

### Claim M4 — Tournament sort is the weakest graph aggregation

**Statement:** Tournament (comparison-based) sort achieves nDCG = 0.82 on
SciDocs with clean preferences, significantly below all other aggregation
methods. This demonstrates that sort-based approaches suffer from suboptimal
tie-breaking and lost information.

**Evidence:** Same summary CSV.

---

## Honest Limitations

### L1 — LLM baselines not yet run with real judgments

The LLM-based baselines (pointwise, pairwise, listwise) were only run in
dry-run/mock mode. The mock results use deterministic hash-based scores and
are NOT meaningful for comparison. Real results require LLM API access.

**Recommendation:** Run with `OPENAI_API_KEY` set to produce publishable
LLM baseline comparisons.

### L2 — Qrels-derived preferences are an oracle setting

When preferences come directly from ground-truth relevance labels, all
reasonable aggregation methods achieve near-perfect ranking. The interesting
comparison is under noisy or incomplete preferences (qrels_flip, LLM judgments,
or multi-ranker votes).

### L3 — Cross-encoder uses document text, graph methods do not

The cross-encoder baseline has access to the full document text and is thus
not directly comparable to graph aggregation methods which operate only on
pairwise preference structure. The comparison is nevertheless informative
because it shows what text-aware reranking achieves in the same setting.

### L4 — Only SciDocs results available for modern baselines

FiQA has only 1 judged document per query in the test split, making it
unsuitable for ranking comparison (all methods trivially achieve nDCG = 1.0).
HotpotQA and BRIGHT require additional dataset preparation. The full
multi-dataset comparison should be produced before submission.

---

## What We Do NOT Claim

1. We do NOT claim to reproduce any specific paper's results (AFR-Rank,
   Reason-to-Rank, BLITZRANK).
2. We do NOT claim the mock LLM results are meaningful.
3. We do NOT claim the cross-encoder is the strongest possible neural baseline.
4. We do NOT claim our methods are better than LLM-based reranking (we have
   not yet run real LLM experiments).

---

## Recommended Next Steps for Manuscript

1. Run LLM baselines with real API access (pointwise, pairwise, listwise).
2. Run on additional datasets (HotpotQA, BRIGHT if downloadable).
3. Add bootstrap confidence intervals for the modern baselines.
4. Produce a figure showing nDCG vs noise level for all methods.
5. Add per-query analysis showing where FAS repair helps vs graph aggregation.
