# TODO

A living task list for the consistency-aware LLM ranking project.

## Near-term

- [ ] Integrate a real LLM pairwise comparator (e.g. GPT-4o, Llama-3) in `pairwise_prefs.py`
- [x] Add ILP-based exact MWFAS solver using `gurobipy`
- [ ] Experiment with larger synthetic graphs (N=100–500 items)
- [ ] Add Spearman ρ and NDCG evaluation metrics to `evaluation.py`
- [ ] Create a Jupyter notebook walkthrough of the synthetic experiment
- [x] Finish the four-dataset publication vote package under `outputs/pub_vote_cmp_all4/`

## Medium-term

- [ ] Benchmark greedy heuristic vs. ILP on controlled inconsistency levels and bounded real vote graphs
- [ ] Integrate real retrieval datasets (MS-MARCO, TREC-DL)
- [ ] Implement sinkhorn-based soft ranking baseline
- [ ] Add confidence / uncertainty estimates for pairwise preferences
- [ ] Explore approximation algorithms for MWFAS (e.g. 2-approximation)

## Long-term / Research

- [ ] Study the relationship between cycle density and ranking quality degradation
- [ ] Investigate LLM self-consistency: does chain-of-thought reduce preference cycles?
- [ ] Apply framework to reasoning chains (action ranking for agent planning)
- [ ] Write and submit first paper draft
- [ ] Release cleaned dataset of LLM pairwise preference cycles
