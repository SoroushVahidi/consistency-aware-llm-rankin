# Running Jobs

**Status: COMPLETE.** The tmux session below ran to completion and was killed after
its process exited cleanly. No exact-ILP job is currently running.

**tmux session `exact_open_ilp_repair`:** launched 2026-07-13, completed 2026-07-13
(27.1s elapsed; 1,025/1,025 queries solved to proven optimality; 0 timeouts/gap-limited
results). Session closed with `tmux kill-session -t exact_open_ilp_repair` after
confirming the script had exited (exit code 0, per the full log in
`logs/exact_open_ilp_repair.log`).

- Repo root: `/home/soroush/consistency-aware-llm-rankin`
- Branch: `main`, HEAD: `873fa3199432ab27c738fb1ffccb86385adfaa25`
- Python: `.venv/bin/python` (3.12.3), solver: PySCIPOpt 6.2.1 (SCIP)
- Command:
  ```
  cd /home/soroush/consistency-aware-llm-rankin && \
    source .venv/bin/activate && \
    python -u reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py \
    2>&1 | tee reports/exact_open_source_ilp_repair_investigation/logs/exact_open_ilp_repair.log
  ```
- Scope: all 4 datasets (bright, fiqa, hotpotqa, scidocs) x all 3 vote regimes
  (ms1, ms1_drop_mutual, ms2) under the primary protocol
  (`primary_minmax_retention_matched`) — approx. 1,000+ queries total.
- Expected runtime: a few minutes (smoke test on 4 hotpotqa queries: ~0.11s/query
  including both greedy and exact-ILP repair + full downstream metric computation;
  ILP solves themselves take ~2-4ms per query at n<=20).
- Expected output: per-query CSVs (`tables/structural_per_query.csv`,
  `tables/ilp_solver_status_per_query.csv`, `tables/retrieval_metric_paired_per_query.csv`),
  aggregated summaries (`tables/*_summary*.csv`), and `manifests/study_summary.json`.

To inspect:
```
tmux attach -t exact_open_ilp_repair
tmux capture-pane -pt exact_open_ilp_repair -S -200
tail -f reports/exact_open_source_ilp_repair_investigation/logs/exact_open_ilp_repair.log
```
