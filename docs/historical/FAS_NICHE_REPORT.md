# FAS Niche Analysis: When Does Consistency-Aware Repair Help?

## Setup

- **Pipeline:** Validated fair comparison (all methods use same candidate set)
- **Datasets:** fiqa, scidocs; top_k=20; mode=summed_margin; n=50 queries
- **Methods:** bm25_raw, dense_raw, rrf_fusion, greedy_fas

---

## 1. Overall Results

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF | Cyclic % |
|---------|---|----------|-----------|------------|------------|--------------|----------|
| fiqa | 50 | 0.250 | **0.410** | 0.357 | 0.308 | 14% | 100% |
| scidocs | 50 | 0.205 | **0.340** | 0.267 | 0.290 | 22% | 100% |

- **FiQA:** Dense > RRF > FAS > BM25. FAS does not beat RRF or dense.
- **SciDocs:** Dense > FAS > RRF > BM25. FAS beats RRF overall.

---

## 2. Grouped by Conflict Level (BEW before)

### FiQA

| BEW bucket | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|-----------|---|----------|-----------|------------|------------|--------------|
| 0≤BEW<1 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0% |
| 1≤BEW<5 | 40 | 0.220 | 0.406 | 0.336 | 0.293 | 12.5% |
| BEW≥5 | 9 | 0.299 | 0.359 | **0.381** | 0.296 | 22% |

On high-BEW FiQA queries, RRF is strongest; FAS does not beat RRF.

### SciDocs

| BEW bucket | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|-----------|---|----------|-----------|------------|------------|--------------|
| 0≤BEW<1 | 4 | 0.249 | 0.270 | **0.274** | 0.202 | 0% |
| 1≤BEW<5 | 39 | 0.207 | 0.362 | 0.281 | **0.309** | 23% |
| BEW≥5 | 7 | 0.168 | 0.261 | 0.188 | **0.234** | 29% |

On SciDocs, FAS beats RRF in medium and high-BEW buckets.

---

## 3. Cyclic vs Acyclic

All 50 queries per dataset had cyclic graphs (100%). No acyclic subset to compare.

---

## 4. FAS on Hardest Queries

### Top 25% by BEW (highest conflict)

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|---------|---|----------|-----------|------------|------------|--------------|
| fiqa | 12 | 0.224 | 0.305 | 0.303 | 0.275 | 25% |
| scidocs | 12 | 0.098 | 0.364 | 0.169 | **0.319** | **42%** |

On high-BEW SciDocs queries, FAS clearly beats RRF (0.319 vs 0.169).

### Top 25% by BM25–dense disagreement

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|---------|---|----------|-----------|------------|------------|--------------|
| fiqa | 12 | 0.128 | 0.320 | 0.252 | 0.241 | 25% |
| scidocs | 12 | 0.015 | 0.278 | 0.092 | **0.267** | **42%** |

When BM25 and dense disagree most, FAS beats RRF on SciDocs.

### Bottom 25% by RRF NDCG (RRF struggles)

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|---------|---|----------|-----------|------------|------------|--------------|
| fiqa | 12 | 0.000 | 0.025 | 0.000 | 0.024 | 8% |
| scidocs | 12 | 0.015 | 0.101 | 0.000 | 0.049 | 17% |

When RRF fails (NDCG=0), FAS does not recover; both are weak.

---

## 5. Selective Repair

**Strategy:** Use base ranking (RRF or dense); apply FAS only when BEW before exceeds threshold.

### Base = RRF

| Threshold | FiQA NDCG | FiQA n_FAS | SciDocs NDCG | SciDocs n_FAS |
|-----------|---|-----------|---|--------------|
| never (baseline) | 0.357 | 0 | 0.267 | 0 |
| bew≥5 | 0.342 | 9 | 0.273 | 7 |
| bew≥3 | 0.345 | 29 | **0.314** | 24 |
| bew≥2 | 0.334 | 41 | **0.315** | 32 |
| bew≥1 | 0.308 | 49 | 0.296 | 46 |
| always | 0.308 | 50 | 0.290 | 50 |

- **FiQA:** Selective (bew≥3) improves over always-FAS (0.345 vs 0.308) but stays below RRF (0.357).
- **SciDocs:** Selective (bew≥2 or bew≥3) beats both RRF (0.267) and always-FAS (0.290): **0.314–0.315**.

### Base = dense_raw

| Threshold | FiQA NDCG | SciDocs NDCG |
|-----------|---|-------------|
| never (baseline) | 0.410 | 0.340 |
| bew≥5 | 0.398 | 0.337 |
| bew≥2 | 0.326 | 0.330 |
| always | 0.308 | 0.290 |

Selective repair with dense base never beats dense-only; applying FAS on high-conflict queries hurts.

---

## 6. Clean Summary Table

| Subset | Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |
|--------|---------|---|----------|-----------|------------|------------|--------------|
| Overall | fiqa | 50 | 0.250 | 0.409 | 0.357 | 0.308 | 14% |
| Overall | scidocs | 50 | 0.205 | 0.340 | 0.267 | 0.290 | 22% |
| Cyclic only | fiqa | 50 | 0.250 | 0.409 | 0.357 | 0.308 | 14% |
| Cyclic only | scidocs | 50 | 0.205 | 0.340 | 0.267 | 0.290 | 22% |
| High BEW (top 25%) | fiqa | 12 | 0.224 | 0.305 | 0.303 | 0.275 | 25% |
| High BEW (top 25%) | scidocs | 12 | 0.098 | 0.364 | 0.169 | **0.319** | **42%** |
| Low RRF (bottom 25%) | fiqa | 12 | 0.000 | 0.025 | 0.000 | 0.024 | 8% |
| Low RRF (bottom 25%) | scidocs | 12 | 0.015 | 0.101 | 0.000 | 0.049 | 17% |

---

## 7. Strict Judgment

### Does FAS have a niche where it is competitive or beneficial?

**Yes, but only on SciDocs and only in high-conflict settings.**

- **SciDocs overall:** FAS (0.290) beats RRF (0.267).
- **SciDocs high-BEW (top 25%):** FAS (0.319) clearly beats RRF (0.169).
- **SciDocs high BM25–dense disagreement:** FAS (0.267) beats RRF (0.092).
- **FiQA:** FAS does not beat RRF in any subset; dense and RRF dominate.

### Is selective repair stronger than always applying FAS?

**Yes on SciDocs when RRF is the base.**

- SciDocs: Selective (bew≥2 or bew≥3) gives 0.314–0.315 vs 0.290 for always-FAS and 0.267 for RRF.
- FiQA: Selective improves over always-FAS (0.345 vs 0.308) but stays below RRF (0.357).

### Is the story better framed as analysis/repair rather than as a new best reranker?

**Yes.**

- FAS is not a new best reranker: dense and often RRF are stronger globally.
- The useful story is: **when do multi-scorer disagreements create cycles, and when does consistency-aware repair help?**
- Findings:
  1. FAS reduces BEW substantially (e.g. 3.7 → 0.4).
  2. On SciDocs, FAS helps on high-conflict queries and can beat RRF.
  3. Selective repair (FAS only when BEW≥2 or BEW≥3) beats always-FAS and RRF on SciDocs.
  4. When RRF and dense both fail (e.g. bottom 25% RRF), FAS does not recover.
  5. Gains are subset-specific; they should be reported as such.

### FiQA top_k=50 (additional)

With top_k=50, all 50 fiqa queries have BEW≥5, so selective repair collapses to always-FAS. On high-BEW subset (top 25%): FAS (0.341) beats RRF (0.284). So FAS has a niche on high-conflict FiQA queries when top_k is larger.

---

### Caveats

- All graphs were cyclic in this sample; we could not compare cyclic vs acyclic.
- Only two datasets; results may not generalize.
- Selective thresholds (BEW≥2, BEW≥3) are heuristic; tuning may improve results.
- With top_k=50, BEW distribution shifts; selective repair may not apply (all queries above threshold).
