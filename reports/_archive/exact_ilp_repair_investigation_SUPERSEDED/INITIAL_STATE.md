# Initial State Snapshot — Exact ILP Repair Investigation

**Snapshot taken:** 2026-07-13 (see exact timestamps below)
**Investigator scope:** Whether exact Gurobi ILP repair changes structural or retrieval
conclusions relative to the canonical greedy cycle-peeling repair. Nothing else.

## Repository identity

| Field | Value |
|---|---|
| Repo root | `/home/soroush/consistency-aware-llm-rankin` |
| This is a linked-worktree setup | Yes — this is the **main worktree**; a sibling linked worktree exists at `/home/soroush/consistency-aware-llm-rankin-caar` (branch `caar-adaptive-reranking`), plus several `/tmp` worktrees. Not otherwise relevant to this investigation. |
| Branch | `main` |
| HEAD | `873fa3199432ab27c738fb1ffccb86385adfaa25` |
| HEAD commit | "Release calibrated JDIQ manuscript PDF", 2026-07-13 15:02:33 -0400 |
| Remote | `origin` → `https://github.com/SoroushVahidin/consistency-aware-llm-rankin.git` |
| Branch sync | up to date with `origin/main` |

## git status at snapshot time

Working tree has 4 modified tracked files (unrelated to repair/ILP: `baseline_ranking.py`,
`llm_api_status.py`, `llm_pairwise.py`, `test_llm_api_status.py` — in-progress LLM-provider
work) and a large set of untracked directories (prior audit/report investigations, the
JDIQ manuscript workspace, and this investigation's own new directory). Full untracked list
captured in `COMMANDS_EXECUTED.md`. None of the untracked/modified content overlaps the
repair/ILP code paths this investigation touches.

## Environment

| Field | Value |
|---|---|
| Python executable | `/home/soroush/consistency-aware-llm-rankin/.venv/bin/python` |
| Python version | 3.12.3 |
| Activation command | `source .venv/bin/activate` (from repo root) |
| Key packages | networkx 3.6.1, pandas 3.0.3, numpy 2.5.1, scipy 1.18.0, matplotlib 3.11.0, pytest 9.1.1 |
| gurobipy installed | **No** — `ModuleNotFoundError: No module named 'gurobipy'` in `.venv`, and not found in the system Python (`/home/soroush/modal-venv`) either. |
| `gurobi_cl` on PATH | **No** — `command not found` |
| Gurobi license file | **None found** — `GRB_LICENSE_FILE` unset, no `gurobi.lic` anywhere searched (`/`, depth 4) |
| CPU | Intel i7-12700K, 20 logical CPUs |
| RAM | 62 GiB total, ~50 GiB available at snapshot time |
| Disk free | 426 GB available on `/` (700 GB volume, 36% used) |

**Conclusion: Gurobi is not currently usable on this machine in any form.** See
`RUNNING_JOBS.md` / the main report for how this blocks Phase 2+ and the options put to
the user.

## Canonical protocol paths (as specified by the task)

| What | Path |
|---|---|
| Manuscript | `papers/JDIQ_2026/manuscript/main.tex` |
| Canonical calibrated outputs | `reports/full_calibrated_core/outputs/calibrated_all4/` |
| Primary protocol run | `reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/` (per-query/per-ranker min-max calibration + raw-reference retention-matched thresholds — matches the task's stated primary protocol) |
| Datasets in canonical package | `bright`, `fiqa`, `hotpotqa`, `scidocs` — each with `ms1`, `ms1_drop_mutual`, `ms2` sub-conditions |
| Per-query graph/candidate data | `.../<dataset>/<ms-condition>/query_records.jsonl` (one JSON object per query: `graph_stats.preference_edges`, `graph_stats.n_nodes`, `candidate_count`, calibration metadata) |
| Query-level metrics already computed | `.../<dataset>/<ms-condition>/query_method_metrics.csv`, `alpha_query_metrics.csv` |

### Candidate-graph sizes actually present in the canonical `ms1` primary-protocol data

| Dataset | n_nodes (candidate pool) | # queries (ms1) |
|---|---|---|
| bright | 20 | 50 |
| fiqa | 20 | 120 |
| scidocs | 20 | 120 |
| hotpotqa | 10 | 52 |

This directly determines ILP feasibility (see `tables/repair_implementation_inventory.csv`
and the Gurobi-sizing analysis in the main report): the `_solve_ilp` linear-ordering
formulation in `mwfas_solver.py` uses `n·(n-1)` binary variables and
`C(n,2) + 2·C(n,3)` constraints. At n=20 that is 380 variables / 2,470 constraints; at
n=10 it is 90 variables / 285 constraints.

## Existing repair implementations found (see `tables/repair_implementation_inventory.csv` for full detail)

1. `src/consistency_ranker/greedy_fas.py` — the **canonical** repair method (`greedy` cycle-peeling heuristic via NetworkX cycle discovery). This is what `reports/full_calibrated_core/` was generated with.
2. `src/consistency_ranker/mwfas_solver.py` — dispatcher; `method="greedy"` (delegates to #1) or `method="ilp"` (**exact, Gurobi-backed**, linear-ordering MIP formulation — the method this investigation is asked about). Also, on the sibling `caar-adaptive-reranking` branch/worktree only (not on `main`/this worktree), `fas_heuristics/` adds `exact_dp`, `lrta`, `wmsf`, `ipsns` — out of scope here since the task specifies canonical greedy vs. exact Gurobi ILP specifically, and those live on a different branch not checked out here.
3. `src/consistency_ranker/exact_fas.py` — a **different** exact method: brute-force enumeration of all `n!` permutations (not Gurobi, not an ILP). Exact but only tractable for `n ≤ 10` (default `max_n=10`). Already exercised by `scripts/run_exact_vs_greedy.py`, but only on small **synthetic** graphs (`n_items ∈ {6, 8}`), never on the canonical real-data calibrated_all4 graphs.

No prior run in this repository has applied Gurobi's exact ILP solver to the canonical
`calibrated_all4` real-data graphs. `run_exact_vs_greedy.py`'s exact-vs-greedy comparison
exists only for the brute-force method on synthetic toy graphs, and it does not touch Gurobi.
