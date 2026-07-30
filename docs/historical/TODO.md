# TODO

A living task list for the consistency-aware LLM ranking project.

## Near-term

- [ ] Regenerate `outputs/q1_journal_package/` with `python scripts/generate_q1_tables.py --pub-root outputs/pub_vote_cmp_all4` so journal tables match the four-dataset package (see `reports/repo_cleanup_recommendations.md`)
- [ ] Integrate a real LLM pairwise comparator (e.g. GPT-4o, Llama-3) in `pairwise_prefs.py`
- [x] Add ILP-based exact MWFAS solver — canonical backend is the free,
      open-source SCIP solver via PySCIPOpt (`method="scip"`/`"exact"`/`"ilp"`
      in `mwfas_solver.py`, `pip install "consistency-ranker[exact]"`, no
      license required); a `method="gurobi"` legacy backend also exists but
      is never required for install/test/reproduction
- [ ] Experiment with larger synthetic graphs (N=100–500 items)
- [ ] Add Spearman ρ to `evaluation.py` (NDCG/MRR/Recall@k already live there)
- [ ] Create a Jupyter notebook walkthrough of the synthetic experiment
- [x] Finish the four-dataset publication vote package under `outputs/pub_vote_cmp_all4/`

## Medium-term

- [x] Benchmark greedy heuristic vs. exact ILP on controlled inconsistency levels and bounded real vote graphs — see `reports/exact_open_source_ilp_repair_investigation/` (manuscript's exact-vs-greedy robustness check) and `tests/test_exact_mwfas_scip.py`
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
