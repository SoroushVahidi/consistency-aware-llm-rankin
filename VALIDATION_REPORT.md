# Strict Validation Report: BM25 + Dense Multi-Scorer Experiments

## 1. Unfairness Identified in Previous Experiments

**Critical finding:** The original `run_real_experiment.py` multi-scorer pipeline used an **unfair candidate set**:

| Method | Candidate Set | Size (typical) |
|--------|---------------|----------------|
| raw_score (BM25 baseline) | BM25 top-k only | k (e.g., 20) |
| score_sum, greedy_fas_topological | Union of BM25 top-k + dense top-k | 20–40 (k=20) or 50–100 (k=50) |

Graph-based methods had access to **more documents** than the BM25 baseline. Documents retrieved by dense but not by BM25 could appear in the graph and be ranked by FAS. The BM25 baseline was never evaluated on those documents. This inflated the apparent gains from FAS.

**Fix:** `scripts/run_validated_multi_scorer.py` enforces a **common candidate set** for all methods: the union of BM25 top-k and dense top-k. Every method ranks exactly this set.

---

## 2. Verified Inputs and Baselines

| Method | Input | Candidate Set |
|--------|-------|---------------|
| **bm25_raw** | BM25 scores; rank union by BM25 score | Union(bm25[:k], dense[:k]) |
| **dense_raw** | Dense scores; rank union by dense score | Same |
| **rrf_fusion** | RRF on bm25[:k] and dense[:k] | Same (RRF outputs full ordering) |
| **score_sum** | Graph from multi-scorer prefs; score-sum ranking | Same |
| **greedy_fas_topological** | DAG after FAS; topological sort | Same |

**Dense reranking:** Dense scores are produced with `--rerank-from bm25`, so dense only sees BM25 candidates. No full-corpus leakage.

**Qrels:** Qrels are used **only for evaluation** (NDCG, MRR, Recall). They are **not** used in preference construction.

---

## 3. BEW (Backward Edge Weight) Validation

**Definition:** For a ranking and a preference graph, an edge u→v is *backward* if the ranking places v before u (v has higher rank). BEW = sum of weights of backward edges.

**Computation:**
```python
def _backward_edge_weight(graph, ranking):
    pos = {n: i for i, n in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        if pos.get(v) < pos.get(u):  # v ranked before u
            total += data.get("weight", 1.0)
    return total
```

**Reported values:**
- **BEW before:** BEW of bm25_raw ranking on the original (cyclic) graph
- **BEW after:** BEW of greedy_fas_topological ranking on the original graph

FAS produces a DAG, so the FAS ranking has 0 BEW *on the DAG*. We report BEW on the **original graph** to show how much inconsistency remains relative to the original preferences. BEW after FAS is typically low because the FAS ranking respects most of the original edges.

**Example (fiqa k=20 summed_margin):** BEW before ≈ 3.71, BEW after ≈ 0.39. No bug found.

---

## 4. Validated Results Table (Fair Comparison)

All methods use the **same candidate set** per query. Mode: `summed_margin`.

| Dataset | top_k | Method | NDCG@10 | MRR | R@10 | R@20 |
|---------|-------|--------|---------|-----|------|------|
| fiqa | 20 | bm25_raw | 0.2500 | 0.2504 | 0.2565 | 0.3086 |
| fiqa | 20 | dense_raw | **0.4095** | **0.3893** | **0.3503** | **0.4314** |
| fiqa | 20 | rrf_fusion | 0.3572 | 0.3563 | 0.3119 | 0.3898 |
| fiqa | 20 | score_sum | 0.2561 | 0.2529 | 0.2705 | 0.3836 |
| fiqa | 20 | greedy_fas_topological | 0.3076 | 0.2894 | 0.3143 | 0.3942 |
| fiqa | 50 | bm25_raw | 0.2500 | 0.2491 | 0.2565 | 0.3086 |
| fiqa | 50 | dense_raw | **0.4056** | **0.3908** | **0.3503** | **0.4314** |
| fiqa | 50 | rrf_fusion | 0.3580 | 0.3543 | 0.3344 | 0.3659 |
| fiqa | 50 | score_sum | 0.2540 | 0.2511 | 0.2665 | 0.3086 |
| fiqa | 50 | greedy_fas_topological | 0.3228 | 0.3248 | 0.3080 | 0.3600 |
| scidocs | 20 | bm25_raw | 0.2049 | 0.2189 | 0.1200 | 0.1660 |
| scidocs | 20 | dense_raw | **0.3402** | **0.3143** | 0.1860 | 0.2550 |
| scidocs | 20 | rrf_fusion | 0.2670 | 0.2708 | 0.1570 | 0.2310 |
| scidocs | 20 | score_sum | 0.2084 | 0.2240 | 0.1240 | 0.2090 |
| scidocs | 20 | greedy_fas_topological | 0.2902 | **0.2871** | 0.1520 | 0.2000 |
| scidocs | 50 | bm25_raw | 0.1993 | 0.2164 | 0.1200 | 0.1660 |
| scidocs | 50 | dense_raw | **0.3282** | **0.3144** | 0.1860 | 0.2550 |
| scidocs | 50 | rrf_fusion | 0.2597 | 0.2675 | 0.1610 | 0.2070 |
| scidocs | 50 | score_sum | 0.2031 | 0.2191 | 0.1240 | 0.1700 |
| scidocs | 50 | greedy_fas_topological | 0.2789 | 0.3143 | 0.1360 | 0.2060 |

---

## 5. Example Queries (5)

Run: `python scripts/run_validated_multi_scorer.py --dataset fiqa --top-k 20 --max-queries 50 --mode summed_margin --examples 5`

**Query 5503:** Relevant = {146277, 64279}
- bm25_raw NDCG@10=0.0 (146277 at rank 13)
- dense_raw NDCG@10=1.0 (146277 at rank 1)
- rrf_fusion NDCG@10=0.43
- greedy_fas_topological NDCG@10=0.0 (pushed dense’s top docs down)

**Query 10152:** Relevant = {113585}
- bm25_raw NDCG@10=0.5 (113585 at rank 3)
- dense_raw NDCG@10=1.0 (113585 at rank 1)
- rrf_fusion NDCG@10=0.63
- greedy_fas_topological NDCG@10=0.5 (similar to BM25)

These examples show that dense often finds relevant docs better than BM25; FAS does not always improve over simple fusion when dense is strong.

---

## 6. Strict Judgment

### Are the large gains real?

**No.** Under a fair comparison (same candidate set), the previous ~42% NDCG@10 gain (0.31→0.45) was largely an artifact of the unfair setup. With validation:
- Dense alone: 0.41 NDCG@10 (fiqa k=20)
- FAS: 0.31 NDCG@10
- RRF fusion: 0.36 NDCG@10

FAS improves over BM25 (+23% relative) but is **worse** than dense and RRF.

### How much of the gain comes from dense vs FAS?

**Most of the gain comes from dense.** Dense is the best single method (0.41). RRF fusion (0.36) is second. FAS (0.31) is third among fusion-style methods. FAS reduces BEW and yields a consistent ranking, but it does not outperform simple RRF on retrieval metrics.

### Is there any bug or unfair comparison?

**Yes, in the original setup.** The unfairness was the differing candidate sets. After fixing this, no further bugs were found. BEW computation is correct.

### Is this result credible enough to build a paper on?

**Only with a reframed narrative.** The original claim that “FAS gives large retrieval gains” does not hold under fair comparison. What *does* hold:

1. **Multi-scorer aggregation creates cycles** — BEW before FAS is non-trivial (e.g. ~3.7 avg).
2. **FAS reduces inconsistency** — BEW drops from ~3.7 to ~0.4.
3. **FAS improves over BM25** — +23% NDCG@10 on fiqa k=20.
4. **FAS does not beat RRF or dense** — Simple fusion and dense alone are stronger on these metrics.

A paper could focus on:
- Consistency-aware ranking as a way to resolve cycles in multi-scorer aggregation
- When FAS helps (e.g. when RRF or dense are weak, or when interpretability of a single ordering matters)
- Ablations: FAS vs score_sum (no FAS), and comparison with RRF/dense

It would be misleading to claim that FAS yields the large gains previously reported; those came from the unfair candidate-set advantage.
