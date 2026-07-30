# Paper Draft Wording: Conflict-Aware Selective Repair

## 1. Final Claim Matrix

| Dataset | Graph regime | What FAS does | What claim is supported |
|---------|--------------|---------------|-------------------------|
| FiQA | Cyclic (~98–100%) | Removes edges to break cycles; topological sort on reduced DAG | Cycle repair; selective FAS improves over RRF on high-conflict queries |
| SciDocs | Cyclic (~97%) | Removes edges to break cycles; topological sort on reduced DAG | Cycle repair; selective FAS (disagreement/hybrid) can improve over RRF |
| HotpotQA | Acyclic (0%) | Removes zero edges; produces topological ordering of original graph | Selective graph-consistent reordering; BEW-based selection improves over RRF and always-FAS |

---

## 2. Exact Wording

### Abstract

When combining multiple retrieval scorers (BM25, dense, cross-encoder) via rank fusion, the aggregated preference graph can contain cycles. Minimum-weight feedback-arc-set (FAS) repair removes cycles to yield a consistent ranking, but always-on FAS is not universally best—it can hurt when the base fusion (e.g., RRF) is already strong. We propose conflict-aware selective repair: apply FAS only on high-conflict queries, identified by backward edge weight (BEW) or scorer disagreement. On FiQA and SciDocs, where graphs are cyclic, selective FAS repair improves over RRF by up to 6.5% NDCG@10 when using three scorers. On HotpotQA, where graphs are acyclic, FAS removes no edges and simply produces a topological ordering; selective application of this ordering improves over both RRF and always-FAS. We distinguish cycle repair (FiQA, SciDocs) from selective graph-consistent reordering (HotpotQA) and frame the method as a diagnostic and repair layer rather than a new reranker.

### Contributions (bullet list)

- **Fair validation:** Enforce identical candidate sets across all methods; identify and fix prior unfair comparison.
- **Conflict-aware selective repair:** Apply FAS (or graph-consistent ordering) only when BEW or disagreement exceeds a threshold.
- **Two-regime analysis:** Cycle repair on FiQA and SciDocs (cyclic graphs); selective graph-consistent reordering on HotpotQA (acyclic graphs). We do not overclaim HotpotQA as cycle repair.
- **Empirical analysis:** When does FAS help? High-conflict queries; three scorers strengthen the effect on cyclic graphs.
- **Framing:** Diagnostic and repair layer, not a new best reranker.

### Introduction (one paragraph)

When combining multiple retrieval scorers via rank fusion, scorer disagreement can create cycles in the aggregated preference graph. Minimum-weight feedback-arc-set (FAS) repair removes cycles to yield a consistent ranking, but always-on FAS is not universally best—it can degrade retrieval when the base fusion (e.g., RRF) is already strong. We propose conflict-aware selective repair: apply FAS only on high-conflict queries. On FiQA and SciDocs, where graphs are cyclic, selective FAS improves over RRF. On HotpotQA, where graphs are acyclic, FAS removes no edges and simply produces a topological ordering; selective application of this ordering still improves over both RRF and always-FAS. We distinguish cycle repair (FiQA, SciDocs) from selective graph-consistent reordering (HotpotQA) and frame the method as a diagnostic and repair layer.

### Discussion / Limitations (one paragraph)

Our experiments cover three datasets (FiQA, SciDocs, HotpotQA) with n=100 queries each. An important limitation is that HotpotQA has acyclic graphs (0% cyclic); FAS removes zero edges and does not perform cycle repair. HotpotQA supports selective graph-consistent reordering—choosing when to apply a topological ordering that respects the aggregated preferences—not cycle-based inconsistency resolution. We recommend that papers using HotpotQA avoid claiming cycle repair or MWFAS on this dataset. Dense retrieval remains best overall on FiQA and SciDocs; selective repair improves over RRF, not over dense.

---

### Theoretical Insights (2–3 paragraphs, for Methods or Analysis)

**Paragraph 1 (Problem and BEW):** We formalize multi-scorer ranking as follows. For each query, we have a candidate set \( C \) and \( m \) scoring functions. Aggregating scores yields a weighted directed preference graph \( G = (V, E, w) \), where an edge \( (u, v) \) with weight \( w(u,v) \) indicates that the aggregate preference favors \( u \) over \( v \). Given a ranking \( \pi \), the backward edge weight (BEW) is the sum of weights of edges \( (u, v) \) such that \( v \) is ranked above \( u \) in \( \pi \). BEW measures how much \( \pi \) violates the preference structure encoded in \( G \). Any topological ordering of \( G \) (or of an acyclic subgraph obtained by removing a feedback arc set) has BEW zero with respect to that subgraph.

**Paragraph 2 (Two regimes and unified view):** Our pipeline applies a greedy feedback arc set (FAS) heuristic followed by topological sort. In cyclic graphs, FAS removes edges to break cycles; in acyclic graphs, no edges are removed and we simply compute a topological ordering. In both cases, the output is a ranking consistent with a DAG. We unify these regimes under a single principle: when the base ranking (e.g., RRF) has high BEW—i.e., it strongly violates the aggregated preferences—we replace it with a graph-consistent ranking (a topological order). When BEW is low, we keep the base ranking. Thus, selective repair replaces the base ranking with a graph-consistent one when inconsistency is high.

**Paragraph 3 (Why selective repair helps):** High BEW implies the ranking violates many high-weight preferences (Proposition 2). In such cases, the graph encodes strong aggregate signal that the base ranking ignores; replacing it with a graph-consistent ranking may improve relevance. Conversely, when BEW is low, the base ranking already agrees with most preferences, and forcing a topological order can introduce arbitrary choices (multiple topological orders exist) that may hurt retrieval. Empirically, applying FAS only when BEW exceeds a threshold (e.g., top 25%) outperforms both always-FAS and never-FAS on FiQA, SciDocs, and HotpotQA.

---

## 3. Paper Title and Alternatives

### Recommended title
**Conflict-Aware Selective Repair for Multi-Scorer Ranking**

### Alternative titles (conservative, match audited evidence)

1. **When to Apply FAS: Selective Repair for Multi-Scorer Ranking**
2. **Conflict-Aware Selective Repair: Cycle Removal and Graph-Consistent Reordering**
3. **Selective Consistency-Aware Repair for Multi-Scorer Retrieval**
4. **Choosing When to Repair: Conflict-Aware FAS for Multi-Scorer Ranking**
5. **Conflict-Aware Selective Repair in Cyclic and Acyclic Preference Graphs**

---

## 4. Venue Recommendation

| Venue type | Recommendation | Rationale |
|------------|----------------|-----------|
| **Q1 journal** | Not recommended | Evidence is limited to n=100 per dataset; gains are modest (up to 6.5% over RRF); dense remains best. A Q1 journal would expect larger scale, stronger gains, and broader impact. |
| **Findings / workshop** | **Recommended** | The story is clear, validated across three datasets and two regimes (cycle repair + acyclic reordering). Fair comparison, explicit distinction of regimes, and conservative framing fit Findings or a SIGIR/EMNLP workshop (e.g., RepL4NLP, SIGIR workshop on retrieval). |
| **Stronger conference (SIGIR, EMNLP main)** | Marginal | The contribution is incremental: selective repair improves over RRF but not over dense. The two-regime framing (cycle repair vs acyclic reordering) is a strength, but main-track venues may expect more novelty or larger-scale evidence. A short paper or findings track is more realistic. |

**Final recommendation:** Submit to **EMNLP Findings** or a **SIGIR/EMNLP workshop** (e.g., RepL4NLP, SIGIR workshop on retrieval). Emphasize the two-regime analysis and the explicit distinction between cycle repair and selective graph-consistent reordering. Keep wording conservative; do not blur the two regimes.

---

## 5. Related Work Paragraph (Publication-Ready)

See `docs/LITERATURE_ALIGNMENT.md` for full analysis. Suggested paragraph:

> Rank aggregation combines multiple rankings into one. Dwork et al. (2001) establish Kemeny optimal aggregation (minimizing pairwise disagreements) and local Kemenization. Ailon et al. (2008) show that rank aggregation is equivalent to the minimum weighted feedback arc set (MWFAS) problem on tournaments and provide approximation algorithms. Prior work on MWFAS for ranking applies FAS globally to produce a consistent ranking. Reciprocal Rank Fusion (RRF) (Cormack et al., 2009) offers a rank-based fusion that avoids score normalization. We use a simple greedy heuristic that iteratively removes the minimum-weight edge from an arbitrary cycle until the graph is acyclic, then apply topological sort. This heuristic has no known approximation guarantee. Our contribution is not a new FAS algorithm but a **selective repair policy**: we apply FAS (or graph-consistent ordering) only when the base ranking (RRF) has high backward edge weight (BEW) or scorer disagreement, and keep RRF otherwise. Unlike prior MWFAS-for-ranking work that applies FAS to all queries, we condition on an inconsistency signal. We compare against a local Kemenization-style baseline (greedy adjacent-swap refinement to minimize BEW): selective FAS outperforms it on all datasets, and FAS is orders of magnitude faster. We show empirically that this policy improves over both always-FAS and never-FAS on FiQA, SciDocs, and HotpotQA.
