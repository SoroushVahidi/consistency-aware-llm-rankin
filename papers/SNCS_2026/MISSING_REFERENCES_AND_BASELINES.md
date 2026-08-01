# Missing References and Baselines

This report lists only omissions or underdeveloped comparisons that are
substantively relevant to the paper's stated scope. It does not recommend
popular baselines merely because they are common in retrieval papers.

## 1. PRP-Graph

- Bibliographic details: Jian Luo, Xuanang Chen, Ben He, and Le Sun.
  `PRP-Graph: Pairwise Ranking Prompting to LLMs with Graph Aggregation for
  Effective Text Re-ranking`. ACL 2024 Long Papers, pages 5766-5776.
- Official source: https://aclanthology.org/2024.acl-long.313/; DOI
  `10.18653/v1/2024.acl-long.313`.
- Relationship to this paper: PRP-Graph is a close current example of building
  a graph from pairwise LLM ranking prompts and aggregating it for reranking.
  It belongs in Related Work because it is directly adjacent to the paper's
  preference-graph framing.
- Requires citation/discussion or new experiment? Citation/discussion only.
  The current paper does not claim to evaluate state-of-the-art LLM graph
  rerankers.
- Severity if omitted: Moderate. A reviewer familiar with LLM pairwise ranking
  could view the Related Work as incomplete.
- Recommended action: Added to Section 2.2.

## 2. TourRank

- Bibliographic details: Yiqun Chen, Qi Liu, Yi Zhang, Weiwei Sun, Xinyu Ma,
  Wei Yang, Daiting Shi, Jiaxin Mao, and Dawei Yin. `TourRank: Utilizing Large
  Language Models for Documents Ranking with a Tournament-Inspired Strategy`.
  WWW 2025.
- Official source: DOI `10.1145/3696410.3714863`.
- Relationship to this paper: TourRank is a recent tournament-inspired LLM
  document-ranking approach, relevant to pairwise/listwise LLM ranking and
  comparison scheduling.
- Requires citation/discussion or new experiment? Optional discussion or future
  work only. A new experiment would shift the manuscript toward an LLM reranking
  benchmark, which is outside the frozen evidence.
- Severity if omitted: Low to moderate. It is relevant but not necessary for the
  repair-vs-retrieval-utility inference.
- Recommended action: Do not add before submission unless the author wants a
  slightly broader LLM-reranking future-work sentence.

## 3. Exact MWFAS Methods

- Bibliographic details: Ali Baharev, Hermann Schichl, Arnold Neumaier, and
  Tobias Achterberg. `An Exact Method for the Minimum Feedback Arc Set Problem`.
  ACM Journal of Experimental Algorithmics, 26(1), 2021.
- Official source: DOI `10.1145/3446429`.
- Relationship to this paper: The paper uses exact MWFAS repair as a diagnostic
  control. A modern exact-method reference helps make clear that exact repair is
  not claimed as a new algorithmic contribution.
- Requires citation/discussion or new experiment? Citation/discussion only.
- Severity if omitted: Moderate editorial risk in a paper relying on exact
  repair terminology.
- Recommended action: Added to Section 2.3.

## 4. Linear Ordering Problem Lineage

- Bibliographic details: Martin Groetschel, Michael Juenger, and Gerhard
  Reinelt. `A Cutting Plane Algorithm for the Linear Ordering Problem`.
  Operations Research, 32(6):1195-1220, 1984.
- Official source: DOI `10.1287/opre.32.6.1195`.
- Relationship to this paper: The SCIP exact formulation is naturally connected
  to the linear-ordering problem and exact/cutting-plane lineage for ordering
  objectives.
- Requires citation/discussion or new experiment? Citation/discussion only.
- Severity if omitted: Low to moderate. The paper is not an optimization-method
  paper, but the reference improves technical positioning.
- Recommended action: Added to Section 2.3.

## Baselines Considered but Not Recommended Before Submission

- State-of-the-art neural rerankers such as monoT5, dense retrievers, SPLADE, or
  cross-encoders: inappropriate as required baselines because the paper is not a
  retrieval-model leaderboard study.
- Full-scale LLM pairwise ranking systems: useful future work, but not essential
  because the paper's primary canonical study is score-derived multi-ranker
  retrieval and the LLM pilot is deliberately bounded.
- Learned repair policies or per-query repair selectors: useful future work, but
  they would introduce a new research direction and require new experiments.
