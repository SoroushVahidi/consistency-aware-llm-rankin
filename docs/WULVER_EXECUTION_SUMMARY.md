# Wulver Execution Summary

## Environment used

- cluster / repo path: `/mmfs1/home/sv96/consistency-aware-llm-rankin`
- conda env used for execution: `feedback-weighted-maximization`
- verified Python: `/home/sv96/.conda/envs/feedback-weighted-maximization/bin/python`
- verified Python version: `3.11.14`
- `GRB_LICENSE_FILE`: left unset

## Whether Gurobi worked

Yes.

Verified in the conda env with:

- `import gurobipy` succeeded
- a tiny 1-variable maximize-`x` smoke solve succeeded
- observed banner: `Restricted license - for non-production use only - expires 2026-11-23`

## Dataset readiness status

Verified processed artifacts and loadability for all four paper-relevant datasets:

- `scidocs`
  - processed files present under `data/processed/beir/scidocs/`
  - loaded counts: `1000` queries, `25657` docs, `29928` qrels
- `fiqa`
  - processed files present under `data/processed/beir/fiqa/`
  - loaded counts: `6648` queries, `57638` docs, `17110` qrels
- `hotpotqa`
  - processed files present under `data/processed/hotpotqa/`
  - loaded counts: `7405` queries, `66568` docs, `73642` qrels
- `bright`
  - processed files present under `data/processed/bright/`
  - loaded counts: `1384` queries, `55643` docs, `1271958` qrels

## Commands run

Representative commands executed during this Wulver session:

- environment / solver verification
  - `conda activate feedback-weighted-maximization`
  - Python / Gurobi smoke test via inline Python
- dataset readiness verification
  - processed-file existence checks for all four datasets
  - `load_dataset_splits()` smoke load for `scidocs`, `fiqa`, `hotpotqa`, `bright`
- publication work
  - `python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_all4 --include-fiqa --include-bright --rankers bm25 tfidf`
  - targeted BRIGHT publication scoring follow-up
  - `sbatch scripts/run_pub_vote_all4_bright_remaining.sbatch`
- exact / ILP validation
  - `PYTHONPATH=src pytest tests/test_mwfas_solver.py tests/test_greedy_fas.py -q`

## Scripts changed

- `scripts/run_publication_vote_suite.py`
  - added FiQA support
  - added configurable `--rankers`
- `scripts/build_paper_evidence_package.py`
  - added FiQA to dataset list
  - made plotting layout handle more than two datasets
  - replaced stale two-dataset hard-coded manuscript summary with a conservative package summary
- `scripts/summarize_publication_vote_suite.py`
  - added FiQA to summary loop
- `scripts/run_pub_vote_all4_bright_remaining.sbatch`
  - new Slurm wrapper for the remaining BRIGHT publication work
- `src/consistency_ranker/mwfas_solver.py`
  - replaced stubbed `ilp` backend with a real Gurobi-backed exact solver
- `tests/test_mwfas_solver.py`
  - new tiny correctness tests for the exact solver
- `README.md`
  - corrected the solver description to match the new exact backend
- `TODO.md`
  - marked the ILP task done and recorded the remaining four-dataset publication-package gap
- `docs/WULVER_EXECUTION_PLAN_AND_CHECKPOINT.md`
  - added the fast verification checkpoint

## Jobs submitted and job IDs

Two Slurm submissions were part of the BRIGHT completion work:

- first job: `889822`
  - script: `scripts/run_pub_vote_all4_bright_remaining.sbatch`
  - logs:
    - `outputs/slurm/pub-all4-bright-889822.out`
    - `outputs/slurm/pub-all4-bright-889822.err`
  - result:
    - failed because `outputs/pub_vote_cmp_all4/bright/scores_bm25.jsonl` was missing
- second job: `889894`
  - script: `scripts/run_pub_vote_all4_bright_remaining.sbatch` after correction
  - result:
    - completed successfully
  - observable evidence:
    - BRIGHT score files, vote files, all three variant outputs, and BRIGHT analysis JSON files appeared under `outputs/pub_vote_cmp_all4/`

## Outputs generated

New output root used for honest regeneration:

- `outputs/pub_vote_cmp_all4/`

Confirmed generated publication-vote outputs:

- `scidocs`
  - score files, vote files, and all three variant outputs under:
    - `outputs/pub_vote_cmp_all4/scidocs/`
    - `outputs/pub_vote_cmp_all4/scidocs/ms2/scidocs/votes_file/`
    - `outputs/pub_vote_cmp_all4/scidocs/ms1/scidocs/votes_file/`
    - `outputs/pub_vote_cmp_all4/scidocs/ms1_drop_mutual/scidocs/votes_file/`
- `hotpotqa`
  - score files, vote files, and all three variant outputs under:
    - `outputs/pub_vote_cmp_all4/hotpotqa/`
    - `outputs/pub_vote_cmp_all4/hotpotqa/ms2/hotpotqa/votes_file/`
    - `outputs/pub_vote_cmp_all4/hotpotqa/ms1/hotpotqa/votes_file/`
    - `outputs/pub_vote_cmp_all4/hotpotqa/ms1_drop_mutual/hotpotqa/votes_file/`
- `fiqa`
  - score files, vote files, and all three variant outputs under:
    - `outputs/pub_vote_cmp_all4/fiqa/`
    - `outputs/pub_vote_cmp_all4/fiqa/ms2/fiqa/votes_file/`
    - `outputs/pub_vote_cmp_all4/fiqa/ms1/fiqa/votes_file/`
    - `outputs/pub_vote_cmp_all4/fiqa/ms1_drop_mutual/fiqa/votes_file/`
- `bright`
  - score files, vote files, and all three variant outputs under:
    - `outputs/pub_vote_cmp_all4/bright/`
    - `outputs/pub_vote_cmp_all4/bright/ms2/bright/votes_file/`
    - `outputs/pub_vote_cmp_all4/bright/ms1/bright/votes_file/`
    - `outputs/pub_vote_cmp_all4/bright/ms1_drop_mutual/bright/votes_file/`

Additional generated outputs:

- `outputs/pub_vote_cmp_all4/analysis/`
  - 24 bootstrap delta JSON files covering all 4 datasets × 3 variants × 2 method-pairs
- `outputs/pub_vote_cmp_all4/paper_package/`
  - tables:
    - `table_graph_ndcg_and_consistency.csv`
    - `table_bootstrap_delta_ndcg.csv`
    - `table_consistency_qrels_bew.csv`
  - plots:
    - `fig_cyclicity_and_scc.png`
    - `fig_delta_ndcg_bootstrap.png`
    - `fig_graph_qrels_bew_pre_post.png`
    - `fig_mean_ndcg_hybrids.png`
  - summary:
    - `MANUSCRIPT_SUMMARY.md`

## Exact-vs-greedy / ILP status

What is now true:

- the repo no longer has a stub-only `method="ilp"` path in `mwfas_solver.py`
- `solve(graph, method="ilp")` now uses a real Gurobi exact formulation
- targeted tests passed in the Gurobi-enabled conda env:
  - `tests/test_mwfas_solver.py`
  - `tests/test_greedy_fas.py`

What I did **not** finish:

- I did not produce a new committed real-data exact-vs-greedy artifact beyond the tested solver implementation itself
- the attempted bounded real-vote audit did not yield a trustworthy artifact in this session, so I am not counting it as completed evidence

## Verification run

Verified successfully:

- `python -m py_compile` on the changed publication and solver files
- `PYTHONPATH=src pytest tests/test_mwfas_solver.py tests/test_greedy_fas.py -q`
  - result: `9 passed`

## What was pushed to GitHub

Nothing was pushed.

I did not create commits or push because this session focused on getting the repo and publication artifacts into a coherent local state first.

## What remains blocked

1. MiniLM publication stack
   - blocker: `sentence-transformers` / `transformers` / `torch` compatibility in this env remained unstable
   - mitigation used here: the finished four-dataset package was built with `--rankers bm25 tfidf`
2. Commit / push hygiene
   - the repo has useful changes and new outputs, but I stopped short of creating commits and pushing in this session
3. Optional stronger exact-evidence artifact
   - the exact Gurobi solver is now real and tested, but I did not finish a new manuscript-facing real-data exact-vs-greedy comparison artifact

## Recommended next command

If you want the new package table in terminal form again:

```bash
python scripts/summarize_publication_vote_suite.py --root outputs/pub_vote_cmp_all4
```
