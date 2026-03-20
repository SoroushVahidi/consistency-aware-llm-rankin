# Paper Outline: Conflict-Aware Selective Repair for Multi-Scorer Ranking

## Suggested Title
**Conflict-Aware Selective Repair for Multi-Scorer Ranking**

(Alternatives in `PAPER_DRAFT_WORDING.md`)

---

## Abstract (Sketch)

When combining multiple retrieval scorers (BM25, dense, cross-encoder) via rank fusion, the aggregated preference graph can contain cycles. Minimum-weight feedback-arc-set (FAS) repair removes cycles to yield a consistent ranking, but always-on FAS is not universally best—it can hurt when the base fusion (e.g., RRF) is already strong. We propose **conflict-aware selective repair**: apply FAS (or graph-consistent ordering) only on high-conflict queries, identified by backward edge weight (BEW) or scorer disagreement. On FiQA and SciDocs (cyclic graphs), selective FAS repair improves over RRF by up to 6.5% NDCG@10 when using three scorers. On HotpotQA (acyclic graphs), FAS removes zero edges; selective application of graph-consistent topological ordering improves over both RRF and always-FAS. We distinguish **cycle repair** (FiQA, SciDocs) from **selective graph-consistent reordering** (HotpotQA) and frame the method as a diagnostic + repair layer.

---

## 1. Introduction

### 1.1 Motivation
- Multi-scorer retrieval (BM25 + dense + cross-encoder) improves over single scorers
- Rank fusion (RRF) and preference aggregation create pairwise graphs
- Scorer disagreement → cycles (on some datasets) → no unique consistent ranking
- FAS repair removes cycles (when present) but can degrade retrieval when base fusion is strong
- **Two regimes:** (a) Cyclic graphs (FiQA, SciDocs): FAS removes edges. (b) Acyclic graphs (HotpotQA): FAS produces topological ordering; no edges removed.

### 1.2 Contributions (bullets)
- **Fair validation:** Enforce identical candidate sets across all methods; identify and fix prior unfair comparison
- **Conflict-aware selective repair:** Apply FAS (or graph-consistent ordering) only when BEW or disagreement exceeds a threshold
- **Two-regime analysis:** Cycle repair on FiQA/SciDocs; selective graph-consistent reordering on HotpotQA (acyclic). Do not overclaim HotpotQA as cycle repair.
- **Empirical analysis:** When does FAS help? High-conflict queries; three scorers strengthen the effect on cyclic graphs
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

### 3.0 Theoretical Foundation (for journal upgrade)
- Formal problem: candidate set, scoring functions, induced preference graph
- BEW: sum of weights of edges (u,v) where v ranked above u
- Proposition 1: Topological order has BEW = 0
- Proposition 2: High BEW ⇒ many high-weight violations
- Proposition 3: In cyclic graphs, min BEW = min-weight FAS
- Unified view: replace with graph-consistent ranking when BEW high
- See `docs/THEORETICAL_FOUNDATION.md`

### 3.1 Setup
- Scorers: BM25, dense retriever, optionally cross-encoder
- Candidate set: union of each scorer's top-k (fair comparison)
- Preference graph: pairwise preferences from score order; weight = margin (summed_margin)

### 3.2 Cycle Detection and FAS Repair
- Backward edge weight (BEW): sum of edge weights that disagree with a ranking
- Greedy FAS: iteratively remove minimum-weight edge in a cycle until DAG (no-op if already acyclic)
- Topological sort on DAG → final ranking
- **On acyclic graphs:** FAS removes zero edges; it simply produces a topological ordering

### 3.3 Selective Repair Policies
- **Never:** RRF only
- **Always:** FAS (or topological ordering) for all queries
- **BEW-based:** FAS if BEW ≥ percentile threshold (e.g. top 25%)
- **Disagreement-based:** FAS if 1 − Kendall τ ≥ percentile threshold
- **Hybrid:** FAS if BEW ≥ p50 AND disagreement ≥ p50
- **Learned:** Simple classifier (logistic regression / decision tree) on BEW, disagreement, n_sccs, cyclic → predict apply FAS

---

## 4. Experiments

### 4.1 Datasets
- FiQA (financial Q&A), SciDocs (scientific citations), HotpotQA (multi-hop QA)
- n = 100 queries per dataset; top_k = 20 (FiQA, SciDocs) or 10 (HotpotQA)
- **Graph regime:** FiQA/SciDocs cyclic (~98%); HotpotQA acyclic (0%)

### 4.2 Scorer Configurations
- 2-scorer: BM25 + dense
- 3-scorer: BM25 + dense + cross-encoder (ms-marco-MiniLM-L6-v2) for FiQA

### 4.3 Metrics
- NDCG@10, MRR, Recall@10, Recall@20
- % cyclic graphs, BEW before/after, % queries where FAS changes ranking, edges removed by FAS

### 4.4 Baselines and Methods
- bm25_raw, dense_raw, rrf_fusion, greedy_fas
- sel_bew25, sel_disc25, sel_hybrid, sel_learned

---

## 5. Analysis

### 5.1 Overall Results
- Dense best overall on FiQA/SciDocs; selective repair beats RRF on FiQA 3-scorer
- HotpotQA: selective graph-consistent reordering beats both RRF and always-FAS
- Table: NDCG@10 by method and dataset

### 5.2 Two Regimes: Cycle Repair vs Acyclic Reordering
- **FiQA, SciDocs:** Cyclic graphs; FAS removes edges; BEW reflects cycle-based inconsistency
- **HotpotQA:** Acyclic graphs; FAS removes zero edges; BEW measures ranking violation only

### 5.3 High- vs Low-Conflict Subsets
- High-conflict (top 25% BEW): FAS helps on FiQA 3-scorer; graph-consistent ordering helps on HotpotQA
- Low-conflict: Selective correctly keeps RRF

### 5.4 Policy Ablation
- Disagreement-based and hybrid often beat BEW-only on FiQA/SciDocs
- BEW top 25% best on HotpotQA

### 5.5 Qualitative Examples
- Success: FAS (or graph-consistent ordering) surfaces relevant doc missed by RRF
- Failure: FAS reorders and drops relevant doc from top-5

### 5.6 Graph Statistics
- % cyclic, BEW before/after, edges removed by FAS by dataset
- FiQA/SciDocs: cyclic, edges removed. HotpotQA: acyclic, zero edges removed.

---

## 6. Discussion and Limitations

### 6.1 Limitations
- Only three datasets (FiQA, SciDocs, HotpotQA); n=100 each
- **HotpotQA is acyclic:** Supports selective graph-consistent reordering, not cycle repair. Do not overclaim.
- Learned selector does not clearly outperform fixed thresholds on held-out test
- Dense remains best on FiQA/SciDocs; selective repair improves over RRF, not over dense

### 6.2 Recommended Framing
- **Diagnostic:** Identify high-conflict queries
- **Repair:** Apply FAS (cycle removal) or graph-consistent ordering only there
- **Two regimes:** Cycle repair (FiQA, SciDocs) and selective graph-consistent reordering (HotpotQA)

### 6.3 Future Work
- Larger scale (200–300+ queries)
- Stronger learned selectors with more data
