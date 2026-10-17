# Scientific conclusion comparison

Historical versus clean rerun: 93,504 exact decimal-string matches, 0 tolerance-only matches, 0 numerical mismatches.

- Method rankings identical: **True** across aggregate and four benchmarks.
- Baseline outcome counts identical: **True**. Historical improve/harm/tie: 13,873/17,449/56,338.
- Largest aggregate or per-dataset method mean difference: **0**.
- Largest of 1,056 cell-by-method mean differences: **0**.
- Largest dataset/regime/pool/cutoff/method mean difference: **0**.

All larger-pool numerical comparisons are unchanged when these grouped means agree. Cross-pool differences remain descriptive because candidate sets and thresholds can change.

## Method order by mean nDCG

- **ALL:** combsum, markov_hybrid_repaired, markov_hybrid_unrepaired, borda_fuse, rrf, prior_only, pagerank_graph, pagerank_graph_repaired, score_sum, priority_topological_repaired, bradley_terry_graph_repaired, bradley_terry_graph, borda, rank_centrality_graph, rank_centrality_graph_repaired, topological_repaired
- **bright:** combsum, score_sum, pagerank_graph_repaired, rrf, markov_hybrid_unrepaired, markov_hybrid_repaired, priority_topological_repaired, pagerank_graph, borda_fuse, prior_only, bradley_terry_graph_repaired, borda, bradley_terry_graph, rank_centrality_graph, rank_centrality_graph_repaired, topological_repaired
- **fiqa:** combsum, pagerank_graph, borda_fuse, rrf, pagerank_graph_repaired, bradley_terry_graph_repaired, prior_only, markov_hybrid_unrepaired, markov_hybrid_repaired, priority_topological_repaired, score_sum, bradley_terry_graph, rank_centrality_graph, rank_centrality_graph_repaired, borda, topological_repaired
- **hotpotqa:** combsum, score_sum, markov_hybrid_repaired, markov_hybrid_unrepaired, prior_only, rrf, borda_fuse, pagerank_graph, borda, pagerank_graph_repaired, bradley_terry_graph_repaired, priority_topological_repaired, bradley_terry_graph, rank_centrality_graph, rank_centrality_graph_repaired, topological_repaired
- **scidocs:** prior_only, combsum, borda_fuse, markov_hybrid_repaired, markov_hybrid_unrepaired, rrf, priority_topological_repaired, bradley_terry_graph_repaired, pagerank_graph, pagerank_graph_repaired, bradley_terry_graph, score_sum, borda, rank_centrality_graph, rank_centrality_graph_repaired, topological_repaired

## Interpretation

This is computational agreement with a later clean implementation at commit `b3926dee968840b10e1b2c17ef531347e172c236`. The original July 14 dirty working-tree bytes have not been reconstructed exactly. Eight query/document input files lack historical hashes. The original cautious conclusion of no robust repaired-method retrieval gain is not strengthened by this verification.
