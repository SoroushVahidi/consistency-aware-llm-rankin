# Q1 Claim-to-Evidence Map

Support levels:
- **strong**: directly backed by committed canonical outputs.
- **moderate**: evidence exists but is indirect, proxy, or not canonical.
- **weak**: partial evidence only.
- **unsupported**: no direct evidence in committed artifacts.

| Claim | Scripts / entry points | Exact artifacts | Support | What would strengthen it |
|---|---|---|---|---|
| Vote construction controls cyclicity and SCC size. | `scripts/run_publication_vote_suite.py`, `scripts/build_paper_evidence_package.py`, `scripts/generate_q1_tables.py` | `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`; `outputs/q1_journal_package/table_main_performance.csv` | **strong** | Add more datasets in canonical package. |
| FAS reduces graph-level inconsistency (BEW/PIC) relative to qrels-derived reference. | `scripts/run_real_experiment.py`, `scripts/build_paper_evidence_package.py`, `scripts/generate_q1_tables.py` | `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`; `outputs/q1_journal_package/table_structural_consistency.csv` | **strong** | Add additional structural metrics independent of qrels alignment. |
| FAS-repaired Copeland can significantly harm nDCG under high cyclicity (SciDocs ms1). | `scripts/analyze_publication_vote_deltas.py`, `scripts/build_paper_evidence_package.py`, `scripts/generate_q1_tables.py` | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`; `outputs/q1_journal_package/table_significance.csv` | **strong** | Confirm on more real datasets and query budgets. |
| Harm concentrates in large-SCC queries. | `scripts/analyze_publication_vote_deltas.py`, `scripts/generate_q1_tables.py` | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (`copeland_scc_high/low`); `outputs/q1_journal_package/table_regime_analysis.csv` | **strong** (for current datasets) | Add non-median stratifications and multivariate analysis. |
| Repair is inactive under near-acyclic vote construction. | `scripts/analyze_publication_vote_deltas.py`, `scripts/generate_q1_tables.py` | `outputs/q1_journal_package/table_significance.csv` (ms2 and many ms1_drop_mutual rows near zero/inactive) | **strong** | Add exact per-query edge-removal histograms. |
| Balance-style repaired/unrepaired variants show negligible retrieval difference. | `scripts/analyze_publication_vote_deltas.py`, `scripts/generate_q1_tables.py` | `outputs/q1_journal_package/table_significance.csv` (balance rows) | **strong** | Add effect-size table in canonical package. |
| Findings generalize to four real datasets. | `scripts/run_all_real_experiments.py` | `outputs/real_full/**` (includes scidocs/fiqa/hotpotqa/bright) | **moderate** (proxy data caveat) | Canonical package with non-proxy FiQA/BRIGHT runs. |
| Findings generalize to direct LLM pairwise labels. | `scripts/run_real_experiment.py` (`llm_pairwise_file` mode) | No committed canonical LLM pairwise experiment artifacts | **unsupported** | Run and commit LLM pairwise datasets/results. |
| Exact ILP MWFAS improves over greedy. | `src/consistency_ranker/mwfas_solver.py` | ILP raises `NotImplementedError` | **unsupported** | Implement ILP and benchmark against greedy on real slices. |
| Method is ready for production reranking deployment. | N/A | No production-scale latency/SLA evidence | **unsupported** | Add large-scale performance and stability study. |

