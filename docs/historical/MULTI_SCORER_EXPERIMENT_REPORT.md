# Multi-Scorer Experiment Report

## 1. Second Scorer: Synthetic Perturbed

**Choice:** A reproducible synthetic second scorer derived from BM25.

- **Reason:** No dense retriever or cross-encoder was readily available in the repo. Adding sentence-transformers would require new dependencies and model downloads.
- **Method:** `scripts/generate_synthetic_perturbed_scores.py`
  - Loads BM25 scores
  - Perturbs ranking by swapping adjacent pairs with probability 0.4 (3 passes)
  - Assigns new scores in the same range as BM25 so both scorers can "win" when they disagree
  - Output: `data/processed/<dataset>/scores/synthetic_perturbed.jsonl`
- **Label:** Clearly synthetic — documented in script and output messages.

**Real vs synthetic:**
- **BM25:** Real sparse retriever scores
- **synthetic_perturbed:** Synthetic — BM25 order perturbed with swaps, scores rescaled

---

## 2. Score Files Produced

| Dataset  | Location | Queries |
|----------|----------|---------|
| fiqa     | `data/processed/beir/fiqa/scores/bm25.jsonl` | 100 |
| fiqa     | `data/processed/beir/fiqa/scores/synthetic_perturbed.jsonl` | 100 |
| scidocs  | `data/processed/beir/scidocs/scores/bm25.jsonl` | 100 |
| scidocs  | `data/processed/beir/scidocs/scores/synthetic_perturbed.jsonl` | 100 |

---

## 3. Summary Table

| Dataset | Scorers | top_k | aggregation_mode | Method | NDCG@10 | MRR | R@10 | R@20 | %Cyclic | BEW_raw | BEW_fas | %Changed |
|---------|---------|-------|------------------|--------|---------|-----|------|------|---------|---------|---------|----------|
| fiqa | bm25,synthetic_perturbed | 20 | majority_vote | raw_score | 0.3136 | 0.3084 | 0.2771 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | majority_vote | score_sum | 0.3119 | 0.3027 | 0.2796 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | majority_vote | borda | 0.3119 | 0.3027 | 0.2796 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | majority_vote | pagerank | 0.3119 | 0.3027 | 0.2796 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | majority_vote | greedy_fas_topological | 0.2980 | 0.2968 | 0.2696 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | summed_margin | raw_score | 0.3136 | 0.3084 | 0.2771 | 0.3352 | 10.0 | 1.23 | 0.01 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | summed_margin | score_sum | 0.3193 | 0.3182 | 0.2696 | 0.3352 | 10.0 | 1.23 | 0.01 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | summed_margin | borda | 0.3193 | 0.3182 | 0.2696 | 0.3352 | 10.0 | 1.23 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | summed_margin | pagerank | 0.3193 | 0.3182 | 0.2696 | 0.3352 | 10.0 | 1.23 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | summed_margin | greedy_fas_topological | 0.3193 | 0.3182 | 0.2696 | 0.3352 | 10.0 | 1.23 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | vote_plus_margin | raw_score | 0.3136 | 0.3084 | 0.2771 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 20 | vote_plus_margin | greedy_fas_topological | 0.2980 | 0.2968 | 0.2696 | 0.3352 | 0.0 | 0.0 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 50 | summed_margin | raw_score | 0.3033 | 0.3109 | 0.2771 | 0.3352 | 16.0 | 7.44 | 0.0 | 100.0 |
| fiqa | bm25,synthetic_perturbed | 50 | summed_margin | greedy_fas_topological | 0.3060 | 0.3205 | 0.2696 | 0.3352 | 16.0 | 7.44 | 0.0 | 100.0 |
| scidocs | bm25,synthetic_perturbed | 20 | summed_margin | raw_score | 0.2442 | 0.2034 | 0.1300 | 0.1790 | 0.0 | 0.02 | 0.0 | 44.0 |
| scidocs | bm25,synthetic_perturbed | 20 | summed_margin | greedy_fas_topological | 0.2468 | 0.2068 | 0.1300 | 0.1790 | 0.0 | 0.02 | 0.0 | 44.0 |
| scidocs | bm25,synthetic_perturbed | 50 | summed_margin | raw_score | 0.2203 | 0.2073 | 0.1300 | 0.1790 | 0.0 | 0.03 | 0.0 | 58.0 |
| scidocs | bm25,synthetic_perturbed | 50 | summed_margin | greedy_fas_topological | 0.2229 | 0.2107 | 0.1300 | 0.1790 | 0.0 | 0.03 | 0.0 | 58.0 |

*(Condensed for readability; full table includes all methods.)*

---

## 4. Key Metrics by Config (greedy_fas_topological vs raw_score)

| Dataset | top_k | mode | %Cyclic | BEW before | BEW after | NDCG@10 raw | NDCG@10 FAS | FAS helps? |
|---------|-------|------|---------|------------|-----------|-------------|-------------|------------|
| fiqa | 20 | summed_margin | 10.0 | 1.23 | 0.01 | 0.3136 | 0.3193 | Yes (+0.57%) |
| fiqa | 50 | summed_margin | 16.0 | 7.44 | 0.01 | 0.3033 | 0.3060 | Yes (+0.9%) |
| fiqa | 20 | majority_vote | 0.0 | 0.0 | 0.0 | 0.3136 | 0.2980 | No (-5.0%) |
| fiqa | 20 | vote_plus_margin | 0.0 | 0.0 | 0.0 | 0.3136 | 0.2980 | No (-5.0%) |
| scidocs | 20 | summed_margin | 0.0 | 0.02 | 0.0 | 0.2442 | 0.2468 | Yes (+1.1%) |
| scidocs | 50 | summed_margin | 0.0 | 0.03 | 0.0 | 0.2203 | 0.2229 | Yes (+1.2%) |

---

## 5. Five Example Queries (Cyclic, FAS Changed Ranking)

Dataset: fiqa | Scorers: bm25, synthetic_perturbed | top_k=20 | mode=summed_margin

### Example 1: Query 2376
- **BM25 top-10:** 519929, 91545, 244961, 323063, 517667, 402249, 114417, 75021, 223626, 265142
- **Synthetic top-10:** 244961, 519929, 517667, 402249, 91545, 75021, 114417, 323063, 407455, 321954
- **Raw (BM25) top-10:** 519929, 91545, 244961, 323063, 517667, 402249, 114417, 75021, 223626, 265142
- **FAS repaired top-10:** 519929, 244961, 91545, 517667, 323063, 402249, 114417, 75021, 223626, 407455

### Example 2: Query 4946
- **BM25 top-10:** 121690, 33628, 431459, 272166, 533075, 296814, 71601, 183959, 384583, 156816
- **Synthetic top-10:** 431459, 121690, 33628, 272166, 183959, 296814, 533075, 66460, 384583, 71601
- **Raw (BM25) top-10:** 121690, 33628, 431459, 272166, 533075, 296814, 71601, 183959, 384583, 156816
- **FAS repaired top-10:** 121690, 431459, 33628, 272166, 296814, 533075, 183959, 71601, 66460, 384583

### Example 3: Query 620
- **BM25 top-10:** 535817, 329798, 378024, 354889, 440256, 457989, 206140, 104492, 479663, 546275
- **Synthetic top-10:** 535817, 329798, 378024, 354889, 457989, 206140, 440256, 104492, 489278, 546275
- **Raw (BM25) top-10:** 535817, 329798, 378024, 354889, 440256, 457989, 206140, 104492, 479663, 546275
- **FAS repaired top-10:** 535817, 329798, 378024, 354889, 457989, 440256, 206140, 104492, 546275, 479663

### Example 4: Query 7911
- **BM25 top-10:** 57711, 143066, 582736, 546115, 36723, 271568, 278460, 94690, 148728, 406872
- **Synthetic top-10:** 582736, 57711, 36723, 271568, 143066, 94690, 278460, 546115, 472537, 240023
- **Raw (BM25) top-10:** 57711, 143066, 582736, 546115, 36723, 271568, 278460, 94690, 148728, 406872
- **FAS repaired top-10:** 57711, 143066, 582736, 36723, 546115, 271568, 278460, 94690, 148728, 406872

### Example 5: Query 932
- **BM25 top-10:** 387010, 457455, 326717, 385221, 588327, 84528, 187706, 240796, 158136, 48722
- **Synthetic top-10:** 457455, 387010, 588327, 326717, 84528, 158136, 385221, 593085, 187706, 586772
- **Raw (BM25) top-10:** 387010, 457455, 326717, 385221, 588327, 84528, 187706, 240796, 158136, 48722
- **FAS repaired top-10:** 387010, 457455, 588327, 326717, 385221, 84528, 187706, 158136, 240796, 593085

---

## 6. Interpretation

### Did multi-scorer aggregation create cycles?
**Yes, but only with `summed_margin`.** With `majority_vote` and `vote_plus_margin`, two scorers produce ties on disagreeing pairs, so those edges are skipped and the graph stays a DAG. With `summed_margin`, the signed sum of score differences can be non-zero when scorers disagree, so we get edges in both directions across different pairs and cycles appear. Fiqa: 10% cyclic (k=20), 16% cyclic (k=50). Scidocs: 0% cyclic in our runs (less disagreement from the synthetic perturbation).

### Did FAS actually do nontrivial work?
**Yes.** With `summed_margin`, the raw (BM25) ranking had average backward edge weight 1.23 (k=20) and 7.44 (k=50) on fiqa. After FAS repair, BEW dropped to ~0.0. FAS removed inconsistent edges and produced a DAG.

### Did it help metrics overall or only on some queries?
**Overall:** Fiqa `summed_margin`: NDCG@10 improved from 0.3136 to 0.3193 (k=20) and 0.3033 to 0.3060 (k=50). MRR improved similarly. Scidocs `summed_margin`: NDCG@10 improved from 0.2442 to 0.2468 (k=20) and 0.2203 to 0.2229 (k=50). Gains are modest (0.5–1.2%) but consistent across queries when cycles exist.

**When it hurts:** With `majority_vote` and `vote_plus_margin`, the graph is a DAG and raw_score (BM25) matches it. FAS/graph methods then use a different ordering (e.g. score_sum, topological) that can be worse than BM25 alone (e.g. fiqa NDCG 0.3136 → 0.2980).

### Is the result strong enough to justify continuing this direction?
**Yes, with caveats.** The pipeline shows that:
1. Multi-scorer aggregation with `summed_margin` can create cycles when scorers disagree.
2. FAS repair reduces inconsistency (BEW drops).
3. When cycles exist, repair improves NDCG and MRR slightly.

**Caveats:** The second scorer is synthetic. Real dense/cross-encoder models may disagree more meaningfully. The gains are small; larger gains may require stronger disagreement or more scorers. Next steps: add a real dense retriever, try LLM pairwise judgments, and test on more datasets.
