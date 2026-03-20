# Paper Outline: Conflict-Aware Selective Repair for Multi-Scorer Ranking

## Suggested Title
**Conflict-Aware Selective Repair for Multi-Scorer Ranking**

---

## Abstract (Sketch)

When combining multiple retrieval scorers (BM25, dense, cross-encoder) via rank fusion, the aggregated preference graph can contain cycles. Minimum-weight feedback-arc-set (FAS) repair removes cycles to yield a consistent ranking, but always-on FAS is not universally best—it can hurt when the base fusion (e.g., RRF) is already strong. We propose **conflict-aware selective repair**: apply FAS only on high-conflict queries, identified by backward edge weight (BEW) or scorer disagreement. On FiQA and SciDocs, selective repair improves over RRF by up to 6.5% NDCG@10 when using three scorers, with gains concentrated in high-conflict subsets. We frame the method as a diagnostic + repair layer rather than a new reranker.

---

## 1. Introduction

### 1.1 Motivation
- Multi-scorer retrieval (BM25 + dense + cross-encoder) improves over single scorers
- Rank fusion (RRF) and preference aggregation create pairwise graphs
- Scorer disagreement → cycles → no unique consistent ranking
- FAS repair removes cycles but can degrade retrieval when base fusion is strong

### 1.2 Contributions (bullets)
- **Fair validation:** Enforce identical candidate sets across all methods; identify and fix prior unfair comparison
- **Conflict-aware selective repair:** Apply FAS only when BEW or disagreement exceeds a threshold
- **Empirical analysis:** When does FAS help? High-conflict queries; three scorers strengthen the effect
- **Framing:** Diagnostic + repair layer, not a new best reranker

### 1.3 Paper structure
- §2 Related work; §3 Methods; §4 Experiments; §5 Analysis; §6 Discussion

---

## 2. Related Work

- Multi-scorer fusion (RRF, Borda, CombSUM)
- Preference aggregation and cyclic preferences (Condorcet, Kemeny)
- Feedback arc set and ranking (MWFAS, greedy heuristics)
- Consistency-aware ranking (prior work on transitive closure, cycle resolution)

---

## 3. Methods

### 3.1 Setup
- Scorers: BM25, dense retriever, optionally cross-encoder
- Candidate set: union of each scorer’s top-k (fair comparison)
- Preference graph: pairwise preferences from score order; weight = margin (summed_margin)

### 3.2 Cycle Detection and FAS Repair
- Backward edge weight (BEW): sum of edge weights that disagree with a ranking
- Greedy FAS: iteratively remove minimum-weight edge in a cycle until DAG
- Topological sort on DAG → final ranking

### 3.3 Selective Repair Policies
- **Never:** RRF only
- **Always:** FAS for all queries
- **BEW-based:** FAS if BEW ≥ percentile threshold (e.g. top 25%)
- **Disagreement-based:** FAS if 1 − Kendall τ ≥ percentile threshold
- **Hybrid:** FAS if BEW ≥ p50 AND disagreement ≥ p50
- **Learned:** Simple classifier (logistic regression / decision tree) on BEW, disagreement, n_sccs, cyclic → predict apply FAS

---

## 4. Experiments

### 4.1 Datasets
- FiQA (financial Q&A), SciDocs (scientific citations)
- n = 100 queries per dataset; top_k = 20

### 4.2 Scorer Configurations
- 2-scorer: BM25 + dense
- 3-scorer: BM25 + dense + cross-encoder (ms-marco-MiniLM-L6-v2)

### 4.3 Metrics
- NDCG@10, MRR, Recall@10, Recall@20
- % cyclic graphs, BEW before/after, % queries where FAS changes ranking

### 4.4 Baselines and Methods
- bm25_raw, dense_raw, rrf_fusion, greedy_fas
- sel_bew25, sel_disc25, sel_hybrid, sel_learned

---

## 5. Analysis

### 5.1 Overall Results
- Dense best overall; selective repair beats RRF on FiQA 3-scorer
- Table: NDCG@10 by method and dataset

### 5.2 High- vs Low-Conflict Subsets
- High-conflict (top 25% BEW): FAS helps on FiQA 3-scorer
- Low-conflict: Selective correctly keeps RRF

### 5.3 Policy Ablation
- Disagreement-based and hybrid often beat BEW-only
- Learned selector: conservative; does not consistently beat best fixed threshold on small test sets

### 5.4 Qualitative Examples
- Success: FAS surfaces relevant doc missed by RRF
- Failure: FAS reorders and drops relevant doc from top-5

### 5.5 Graph Statistics
- % cyclic, BEW before/after by scorer combination
- More scorers → more cycles, higher BEW

---

## 6. Discussion and Limitations

### 6.1 Limitations
- Only two datasets (FiQA, SciDocs)
- n = 100; scale-up to 200–300 prepared but not fully run
- Learned selector does not clearly outperform fixed thresholds on held-out test
- Dense remains best; selective repair improves over RRF, not over dense

### 6.2 Recommended Framing
- **Diagnostic:** Identify high-conflict queries
- **Repair:** Apply FAS only there
- **Contribution:** Selective consistency-aware repair that improves over RRF when scorers disagree

### 6.3 Future Work
- HotpotQA, BRIGHT (reasoning-heavy benchmarks)
- Larger scale (200–300+ queries)
- Stronger learned selectors with more data
