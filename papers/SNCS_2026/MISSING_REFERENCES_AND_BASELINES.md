# Missing References and Baselines (Related-Work Pass, 2026-08-02)

This file supersedes the prior recommendation list for the Related Work /
literature-positioning pass. It distinguishes **added**, **rejected**, and
**discussion-only / future experiment** items. No new experiments were run.

## A. Four priority candidates (verified)

### 1. TourRank — **ADDED** (`chen2025tourrank`)

- **Title:** TourRank: Utilizing Large Language Models for Documents Ranking
  with a Tournament-Inspired Strategy
- **Authors:** Yiqun Chen, Qi Liu, Yi Zhang, Weiwei Sun, Xinyu Ma, Wei Yang,
  Daiting Shi, Jiaxin Mao, Dawei Yin
- **Venue / year:** Proceedings of the ACM on Web Conference (WWW) 2025,
  pages 1638–1652
- **DOI:** https://doi.org/10.1145/3696410.3714863
- **Summary:** Tournament-style LLM document ranking that ensembles group
  outcomes to reduce input-order sensitivity in zero-shot ranking.
- **Relevance:** Closest recent peer-reviewed LLM ranking system that
  reviewers may expect near pairwise/listwise LLM ranking discussion; shows
  order-bias mitigation without preference-graph FAS repair.
- **Cite in:** Related Work (§2.2); Limitations (External Validity).
- **Not:** Methodology / Results (no experiment).

### 2. GNNRank — **ADDED** (`he2022gnnrank`)

- **Title:** GNNRank: Learning Global Rankings from Pairwise Comparisons via
  Directed Graph Neural Networks
- **Authors:** Yixuan He, Quan Gan, David Wipf, Gesine D. Reinert, Junchi Yan,
  Mihai Cucuringu
- **Venue / year:** ICML 2022 / PMLR 162:8581–8612
- **URL:** https://proceedings.mlr.press/v162/he22b.html
- **Summary:** Directed GNN embeddings with differentiable upset objectives
  for recovering global rankings from pairwise comparison digraphs.
- **Relevance:** Modern learning-based ranking recovery on comparison graphs;
  clarifies that optimizing ranking-upset objectives is not the same question
  as testing qrel nDCG after combinatorial repair.
- **Cite in:** Related Work (§2.1).

### 3. Vahidi & Koutis MWFAS ranking preprint — **ADDED** (`vahidi2024mwfas`)

- **Title:** Minimum Weighted Feedback Arc Sets for Ranking from Pairwise
  Comparisons
- **Authors:** Soroush Vahidi, Ioannis Koutis
- **Venue / year:** arXiv preprint, 2024 (abs/2412.16181)
- **URL:** https://arxiv.org/abs/2412.16181
- **Summary:** Learning-free combinatorial MWFAS algorithms evaluated on
  GNNRank-style ranking-recovery metrics/benchmarks (not document retrieval).
- **Relevance:** Distinguishes the author’s combinatorial ranking-recovery
  preprint from this retrieval-utility audit; avoids reviewer confusion.
- **Cite in:** Related Work (§2.1, §2.3). Marked as preprint.

### 4. Voting with the Graph / TCR — **ADDED** (`liu2025votinggraph`)

- **Title:** Voting with the Graph: Stable RLAIF via Topological Consistency
  Maximization
- **Authors:** Boyin Liu, Zhuo Zhang, Sen Huang, Lipeng Xie, Qingxu Fu,
  Haoran Chen, Li Yu, Tianyi Hu, Zhaoyang Liu, Bolin Ding, Dongbin Zhao
- **Venue / year:** arXiv preprint, 2025 (abs/2510.15514)
- **URL:** https://arxiv.org/abs/2510.15514
- **Summary:** Preference-cycle filtering via greedy Maximum Acyclic Subgraph
  approximation (TCR) for stable RLAIF rewards; introduces CIR diagnostic.
- **Relevance:** Closest recent cycle-breaking preference-graph method; gains
  are on RLAIF/LLM-eval objectives, not Holm-corrected retrieval nDCG.
- **Cite in:** Related Work (§2.3, closest-works table); Discussion literature.
  Marked as preprint. **Not** peer-reviewed.

## B. Candidates considered but not added (or already present)

| Work | Decision | Why |
|---|---|---|
| PRP-Graph (Luo et al., ACL 2024) | Already cited | Closest graph-aggregation LLM reranker |
| LLM-RankFusion (Zeng et al.) | Already cited | Multi-LLM pairwise inconsistency mitigation |
| PGED / Hu et al. acyclic prefs | Already cited | Acyclicity for LLM eval/selection |
| Baharev et al. exact FAS (2021) | Already cited | Exact MWFAS lineage |
| Groetschel et al. linear ordering (1984) | Already cited | Exact ordering lineage |
| DuoT5 / pairwise T5 rerankers | Rejected for RW expansion | Adjacent LLM pairwise reranking; already covered by PRP / Qin / Sun line; adding would inflate without sharpening the repair gap |
| Tang et al. permutation self-consistency | Rejected | Order-bias theme already via Zheng/Shi; not FAS repair |
| monoT5 / RankT5 / ColBERTv2 / SPLADE | Discussion only | Strong modern baselines, not comparable as repair controls |
| Learned fusion / cross-encoders | Discussion only | Out of frozen evidence scope |

## C. Baseline relevance audit (no new experiments)

### Already included (controlled anchors, not SOTA)

- Lexical: BM25, TF-IDF
- Dense: MiniLM
- Graph-free fusion: RRF, CombSUM, Borda
- Graph extraction / unrepaired vs repaired comparisons (study core)

### Framing requirement (now in Limitations § External Validity)

Describe these as **controlled multi-ranker construction anchors**, not as a
modern retrieval leaderboard. Explicitly disclaim SOTA status.

### Omitted baselines — classification

| Baseline class | Action |
|---|---|
| Stronger dense retrievers / hybrids beyond MiniLM | Limitations / future work only |
| Cross-encoder / monoT5-style neural rerankers | Limitations / future work only |
| Tournament / listwise LLM rankers (e.g., TourRank) | Cite in RW + Limitations; **experiment later** only if author expands scope |
| Full-scale LLM pairwise graph systems (PRP-Graph scale) | Cite in RW; experiment later if desired |
| Learned repair / routing policies | Future work; new research direction |

### Not actually comparable as repair baselines

Systems that never build a preference graph, or that replace the entire
ranking stack, cannot answer the paper’s marginal-repair question. They are
relevant as **external validity** context, not as missing cells in the
repair-vs-unrepaired table.

## D. Closest works (3–6) — difference summary

See manuscript Table `tab:closest-works` and `RELATED_WORK_CHANGELOG.md`.
Short form:

1. **PRP-Graph** — pairwise LLM graph aggregation for text reranking; no
   unrepaired-vs-repaired Holm audit.
2. **LLM-RankFusion** — inconsistency mitigation for fusion; no exact MWFAS
   diagnostic on retrieval deltas.
3. **PGED (Hu)** — acyclic preference ensembles for LLM eval/selection.
4. **TCR (Liu)** — cycle filtering for RLAIF rewards (preprint).
5. **TourRank** — tournament LLM ranking; no FAS repair stage.
6. **Earlier Research Square preprint** — same theme; superseded protocol.

## E. Journal alignment notes

- SN Computer Science: numeric `sn-basic`+`Numbered` citations (already used).
- No strict research-article page cap verified on the journal submission
  guidelines page; self-imposed target remains ~36 pages for this package.
- Preprints are disclosable; entries carry “not peer-reviewed” notes where
  applicable (TCR; MWFAS ranking preprint; Research Square preprint).
