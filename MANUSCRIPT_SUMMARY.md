# Manuscript Summary: Conflict-Aware Selective Repair for Multi-Scorer Ranking

## Problem Statement

When combining multiple retrieval scorers (e.g., BM25, dense, cross-encoder) via rank fusion or preference aggregation, the resulting pairwise preference graph can contain **cycles**: A > B > C > A. Such cycles reflect genuine disagreement between scorers and prevent a unique consistent ranking. Minimum-weight feedback-arc-set (FAS) repair removes cycles by deleting the minimum-weight set of edges, yielding a DAG and thus a unique topological ranking. However, **always-on FAS is not universally best**—it can hurt when the base fusion (e.g., RRF) is already strong. The question is: **when does consistency-aware repair help?**

**Two distinct regimes (audited):**

- **(a) Cycle repair in cyclic graphs:** FiQA and SciDocs have cyclic graphs (~98–100%). FAS removes edges to break cycles; BEW measures cycle-based inconsistency.
- **(b) Selective graph-consistent reordering in acyclic graphs:** HotpotQA has acyclic graphs (0% cyclic). FAS removes zero edges; it produces a topological ordering. BEW measures *ranking violation of the graph*, not cycle-based inconsistency. The selective-repair *policy* (when to apply) generalizes.

## Key Hypothesis

Conflict-aware **selective repair**—applying FAS (or graph-consistent ordering) only on high-conflict queries and keeping RRF elsewhere—can improve over both always-FAS and never-FAS (RRF only). Conflict can be measured by backward edge weight (BEW), scorer disagreement (1 − Kendall τ), or both.

## Methods Compared

| Method | Description |
|--------|-------------|
| **bm25_raw** | Rank union of candidates by BM25 score |
| **dense_raw** | Rank union by dense retriever score |
| **rrf_fusion** | Reciprocal Rank Fusion over all scorers |
| **greedy_fas** | FAS repair → topological sort on DAG (removes edges if cyclic; otherwise just topological sort) |
| **sel_bew25** | FAS if BEW in top 25%, else RRF |
| **sel_disc25** | FAS if disagreement in top 25%, else RRF |
| **sel_hybrid** | FAS if BEW≥p50 AND disagreement≥p50, else RRF |
| **sel_learned** | FAS if predicted to help (validation-tuned threshold or simple classifier) |

## Datasets

| Dataset | n | Domain | Graph regime | Scorers |
|---------|---|--------|--------------|---------|
| FiQA | 100 | Financial Q&A | **Cyclic** (~98–100%) | bm25, dense; bm25, dense, cross_encoder |
| SciDocs | 100 | Scientific citations | **Cyclic** (~97%) | bm25, dense |
| HotpotQA | 100 | Multi-hop QA | **Acyclic** (0%) | bm25, dense |

Processed data supports 300 FiQA and 200 SciDocs; dense/cross-encoder scores generated for 100.

## Fairness / Validation Notes

- **Candidate set:** All methods use the **same** candidate set = union of each scorer's top-k. No unfair advantage from larger pools.
- **Dense reranking:** Dense uses `--rerank-from bm25`; no full-corpus leakage.
- **Qrels:** Used only for evaluation (NDCG, MRR, Recall). **Not** used in preference construction.
- **BEW:** Backward edge weight = sum of edge weights that disagree with the ranking. On cyclic graphs (FiQA, SciDocs), BEW reflects cycle-based inconsistency. On acyclic graphs (HotpotQA), BEW measures ranking violation of the graph only.

## Main Results

### Overall (n=100)

| Dataset | Scorers | bm25 | dense | rrf | fas | sel_bew25 | sel_hybrid |
|---------|---------|------|-------|-----|-----|-----------|------------|
| FiQA | 2 | 0.255 | **0.408** | 0.349 | 0.332 | 0.335 | **0.362** |
| FiQA | 3 | 0.255 | **0.408** | 0.339 | 0.337 | **0.361** | **0.363** |
| SciDocs | 2 | 0.210 | **0.357** | 0.281 | 0.274 | 0.270 | **0.290** |
| HotpotQA | 2 | 0.824 | 0.837 | 0.850 | 0.834 | **0.860** | 0.847 |

- Dense is best overall on FiQA/SciDocs.
- **Cycle repair (FiQA, SciDocs):** Selective repair beats RRF on FiQA 3-scorer (0.361–0.363 vs 0.339). On SciDocs, disagreement-based and hybrid selective beat RRF (0.290–0.296 vs 0.281).
- **Acyclic reordering (HotpotQA):** Selective repair (BEW top 25%) beats both RRF (0.850) and FAS (0.834). FAS removes zero edges; it produces a topological ordering. The selective-repair *policy* generalizes.

### Graph Statistics

| Dataset | Scorers | % cyclic | BEW before | BEW after | Edges removed | % FAS changes ranking |
|---------|---------|----------|------------|-----------|---------------|------------------------|
| FiQA | 2 | 98 | 60.4 | 0.4 | >0 | 100 |
| FiQA | 3 | 100 | 141.2 | 8.3 | >0 | 100 |
| SciDocs | 2 | 97 | 71.8 | 0.4 | >0 | 100 |
| HotpotQA | 2 | **0** | 6.56 | 0.00 | **0** | 99 |

## Niche / Subset Results

### High-conflict (top 25% BEW)

- **FiQA 3-scorer:** FAS (0.369) beats RRF (0.281). Selective applies FAS here. **Cycle repair.**
- **SciDocs:** RRF/dense remain best; BEW-based selective does not beat RRF.
- **HotpotQA:** FAS (0.848) beats RRF (0.809). Selective applies graph-consistent ordering. **Acyclic reordering.**

### Low-conflict (bottom 25% BEW)

- Selective correctly keeps RRF (no FAS). Dense often best.

### Policy Ablation

| Policy | FiQA (2) | FiQA (3) | SciDocs | HotpotQA |
|--------|----------|----------|---------|----------|
| never | 0.349 | 0.339 | 0.281 | 0.850 |
| always | 0.332 | 0.337 | 0.274 | 0.834 |
| BEW top25% | 0.335 | **0.361** | 0.270 | **0.860** |
| disagreement top25% | **0.357** | **0.365** | **0.296** | 0.853 |
| hybrid | **0.362** | **0.363** | **0.290** | 0.847 |

Disagreement-based and hybrid policies often outperform BEW-only on FiQA/SciDocs. On HotpotQA, BEW top 25% is best.

### Learned Selector (Conservative)
- Simple logistic regression / decision tree on (BEW, disagreement, n_sccs, cyclic) to predict "apply FAS"
- 60/20/20 train/val/test split
- On small test sets (n=20): learned selector often matches "never" (RRF)—conservative, avoids overfitting
- Does not consistently beat best fixed threshold; fixed policies (BEW, disagreement, hybrid) remain the main recommendation

## Limitations

- Only three datasets (FiQA, SciDocs, HotpotQA); n=100 per dataset.
- **HotpotQA is acyclic:** It supports selective graph-consistent reordering, *not* cycle repair. Do not overclaim.
- Learned selector uses simple validation tuning; no heavy ML.
- Dense remains best on FiQA/SciDocs; selective repair improves over RRF, not over dense.

## Final Recommended Framing

**Diagnostic + repair layer**, not a new best reranker:

1. **Diagnostic:** Identify high-conflict queries (BEW, disagreement, or both).
2. **Repair:** Apply FAS (cycle removal) or graph-consistent ordering (topological sort) only on those queries; keep RRF elsewhere.
3. **Two regimes:** (a) **Cycle repair** on FiQA/SciDocs (cyclic graphs); (b) **Selective graph-consistent reordering** on HotpotQA (acyclic graphs). The selective-repair *policy* generalizes across both.

---

## Strict Final Recommendation

### Venue
**Workshop / findings paper** (e.g., EMNLP Findings, RepL4NLP, SIGIR workshop). The story is clear and validated across three datasets and two regimes (cycle repair + acyclic reordering). A Q1 journal would need more scale and stronger gains. A top-tier full conference would need broader generalization.

### Single Highest-Value Additional Experiment
Scale-up to 200–300 queries on FiQA/SciDocs to confirm stability. HotpotQA already provides generalization to acyclic graphs.

### What to Stop Doing
- **Stop overclaiming HotpotQA as cycle repair.** It is selective graph-consistent reordering in acyclic graphs.
- **Stop chasing always-on FAS as a new best reranker.** The evidence shows it is not. The contribution is selective repair.
- **Stop blurring cycle repair and acyclic reordering** in the paper wording.
