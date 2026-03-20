# Manuscript Summary: Conflict-Aware Selective Repair for Multi-Scorer Ranking

## Problem Statement

When combining multiple retrieval scorers (e.g., BM25, dense, cross-encoder) via rank fusion or preference aggregation, the resulting pairwise preference graph can contain **cycles**: A > B > C > A. Such cycles reflect genuine disagreement between scorers and prevent a unique consistent ranking. Minimum-weight feedback-arc-set (FAS) repair removes cycles by deleting the minimum-weight set of edges, yielding a DAG and thus a unique topological ranking. However, **always-on FAS is not universally best**—it can hurt when the base fusion (e.g., RRF) is already strong. The question is: **when does consistency-aware repair help?**

## Key Hypothesis

Conflict-aware **selective repair**—applying FAS only on high-conflict queries and keeping RRF elsewhere—can improve over both always-FAS and never-FAS (RRF only). Conflict can be measured by backward edge weight (BEW), scorer disagreement (1 − Kendall τ), or both.

## Methods Compared

| Method | Description |
|--------|-------------|
| **bm25_raw** | Rank union of candidates by BM25 score |
| **dense_raw** | Rank union by dense retriever score |
| **rrf_fusion** | Reciprocal Rank Fusion over all scorers |
| **greedy_fas** | FAS repair → topological sort on DAG |
| **sel_bew25** | FAS if BEW in top 25%, else RRF |
| **sel_disc25** | FAS if disagreement in top 25%, else RRF |
| **sel_hybrid** | FAS if BEW≥p50 AND disagreement≥p50, else RRF |
| **sel_learned** | FAS if predicted to help (validation-tuned threshold or simple classifier) |

## Datasets

| Dataset | n | Domain | Scorers |
|---------|---|--------|---------|
| FiQA | 100 | Financial Q&A | bm25, dense; bm25, dense, cross_encoder |
| SciDocs | 100 | Scientific citations | bm25, dense |

Processed data supports 300 FiQA and 200 SciDocs; dense/cross-encoder scores generated for 100.

## Fairness / Validation Notes

- **Candidate set:** All methods use the **same** candidate set = union of each scorer’s top-k. No unfair advantage from larger pools.
- **Dense reranking:** Dense uses `--rerank-from bm25`; no full-corpus leakage.
- **Qrels:** Used only for evaluation (NDCG, MRR, Recall). **Not** used in preference construction.
- **BEW:** Backward edge weight = sum of edge weights that disagree with the ranking. Computed on the original graph for both RRF and FAS rankings.

## Main Results

### Overall (n=100)

| Dataset | Scorers | bm25 | dense | rrf | fas | sel_bew25 | sel_hybrid |
|---------|---------|------|-------|-----|-----|-----------|-----------|
| FiQA | 2 | 0.255 | **0.408** | 0.349 | 0.332 | 0.335 | **0.362** |
| FiQA | 3 | 0.255 | **0.408** | 0.339 | 0.337 | **0.361** | **0.363** |
| SciDocs | 2 | 0.210 | **0.357** | 0.281 | 0.274 | 0.270 | **0.290** |

- Dense is best overall.
- Selective repair (BEW top25%, hybrid) beats RRF on FiQA 3-scorer (0.361–0.363 vs 0.339).
- On SciDocs, disagreement-based and hybrid selective beat RRF (0.290–0.296 vs 0.281).

### Graph Statistics

| Dataset | Scorers | % cyclic | BEW before | BEW after | % FAS changes ranking |
|---------|---------|----------|------------|-----------|------------------------|
| FiQA | 2 | 98 | 60.4 | 0.4 | 100 |
| FiQA | 3 | 100 | 141.2 | 8.3 | 100 |
| SciDocs | 2 | 97 | 71.8 | 0.4 | 100 |

## Niche / Subset Results

### High-conflict (top 25% BEW)

- **FiQA 3-scorer:** FAS (0.369) beats RRF (0.281). Selective applies FAS here.
- **SciDocs:** RRF/dense remain best; BEW-based selective does not beat RRF.

### Low-conflict (bottom 25% BEW)

- Selective correctly keeps RRF (no FAS). Dense often best.

### Policy Ablation

| Policy | FiQA (2) | FiQA (3) | SciDocs |
|--------|----------|----------|---------|
| never | 0.349 | 0.339 | 0.281 |
| always | 0.332 | 0.337 | 0.274 |
| BEW top25% | 0.335 | **0.361** | 0.270 |
| disagreement top25% | **0.357** | **0.365** | **0.296** |
| hybrid | **0.362** | **0.363** | **0.290** |

Disagreement-based and hybrid policies often outperform BEW-only.

### Learned Selector (Conservative)
- Simple logistic regression / decision tree on (BEW, disagreement, n_sccs, cyclic) to predict “apply FAS”
- 60/20/20 train/val/test split
- On small test sets (n=20): learned selector often matches “never” (RRF)—conservative, avoids overfitting
- Does not consistently beat best fixed threshold; fixed policies (BEW, disagreement, hybrid) remain the main recommendation

## Limitations

- Only two datasets (FiQA, SciDocs); no HotpotQA or BRIGHT yet.
- n=100 per dataset; scale-up to 200–300 prepared but not fully run.
- Learned selector uses simple validation tuning; no heavy ML.
- Dense remains best; selective repair improves over RRF, not over dense.

## Final Recommended Framing

**Diagnostic + repair layer**, not a new best reranker:

1. **Diagnostic:** Identify high-conflict queries (BEW, disagreement, or both).
2. **Repair:** Apply FAS only on those queries; keep RRF elsewhere.
3. **Contribution:** Selective consistency-aware repair that improves over RRF when multiple scorers disagree, especially with three or more scorers.

---

## Strict Final Recommendation

### Venue
**Workshop / findings paper** (e.g., EMNLP Findings, RepL4NLP, SIGIR workshop). The story is clear and validated, but evidence is limited to two datasets and n=100. A Q1 journal would need more datasets, scale, and stronger gains. A top-tier full conference would need broader generalization.

### Single Highest-Value Additional Experiment
**Run the same pipeline on HotpotQA (50–100 queries).** It would test generalization to a reasoning-heavy, multi-hop setting with minimal new engineering (add dataset to BM25/dense scripts, download, prepare, run). If selective repair helps there, the story is stronger.

### What to Stop Doing
- **Stop chasing always-on FAS as a new best reranker.** The evidence shows it is not. The contribution is selective repair.
- **Stop adding new scorers or methods** before confirming generalization. One more dataset (HotpotQA) matters more than a fourth scorer.
- **Stop over-investing in learned selectors** on 100 queries. Fixed thresholds (BEW, disagreement, hybrid) already work; learned models need more data to add value.
