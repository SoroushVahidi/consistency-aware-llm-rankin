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
