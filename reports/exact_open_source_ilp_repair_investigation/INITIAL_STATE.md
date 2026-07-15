# Initial State Snapshot — Exact Open-Source ILP Repair Investigation

**Snapshot taken:** 2026-07-13
**Investigator scope:** Whether exact **open-source** ILP repair changes the structural or
retrieval conclusions relative to the canonical greedy cycle-peeling repair. Nothing else
(no manuscript edits, no candidate-pooling/retention/calibration-variant changes, no
overwriting canonical outputs, no commits/pushes, no paid APIs).

## Relationship to the prior `reports/exact_ilp_repair_investigation/` attempt

A prior investigation directory (`reports/exact_ilp_repair_investigation/`, untracked,
already present in the working tree) attempted this exact question using **Gurobi** and
concluded at Phase 1 that Gurobi is not installed, not licensed, and not on `PATH`
anywhere on this machine — see its `INITIAL_STATE.md` / `COMMANDS_EXECUTED.md`. That
investigation is left untouched. This is a fresh, separate investigation using an
open-source solver instead, per this task's explicit solver requirement.

## Repository identity

| Field | Value |
|---|---|
| Repo root | `/home/soroush/consistency-aware-llm-rankin` |
| Branch | `main` |
| HEAD | `873fa3199432ab27c738fb1ffccb86385adfaa25` (`Release calibrated JDIQ manuscript PDF`) |
| Remote | `origin` -> `https://github.com/SoroushVahidin/consistency-aware-llm-rankin.git`, up to date |
| git status | 4 modified tracked files unrelated to repair/ILP (in-progress LLM-provider work: `baseline_ranking.py`, `llm_api_status.py`, `llm_pairwise.py`, `test_llm_api_status.py`) + many untracked prior-investigation directories and the JDIQ manuscript workspace. None overlap the repair/ILP code paths touched here. This investigation writes only under `reports/exact_open_source_ilp_repair_investigation/`. |

## Environment

| Field | Value |
|---|---|
| Python executable | `/home/soroush/consistency-aware-llm-rankin/.venv/bin/python` |
| Python version | 3.12.3 |
| Activation | `source .venv/bin/activate` (repo root) |
| Key packages (pre-existing) | networkx 3.6.1, pandas 3.0.3, numpy 2.5.1, scipy 1.18.0, matplotlib 3.11.0, scikit-learn 1.9.0, pytest 9.1.1 |
| CPU | Intel i7-12700K, 20 logical CPUs |
| RAM | 62 GiB total, ~50 GiB available |
| Disk free | 427 GB available on `/` (700 GB volume, 36% used) |

## Solver selection (see Phase 1 below for full detail)

- **Selected solver: PySCIPOpt 6.2.1 (SCIP)** — preference order option **A** (top choice).
- Not pre-installed; installed via `pip install pyscipopt` into the existing local
  `.venv` only (no global/system package changes). Network access to PyPI was available.
- Verified with a smoke-test MIP (binary knapsack-style toy problem): solver reports
  `getStatus() == "optimal"` and `getGap() == 0.0`.
- highspy/scipy.optimize.milp (option B, HiGHS) and CBC/GLPK (options C/D) were not
  needed since option A succeeded; scipy.optimize.milp (HiGHS-backed) was confirmed
  available as a fallback (scipy 1.18.0 already installed) but not used.

## Canonical protocol paths (as specified by the task)

| What | Path |
|---|---|
| Manuscript (not edited) | `papers/JDIQ_2026/manuscript/main.tex` |
| Canonical calibrated outputs (not overwritten) | `reports/full_calibrated_core/outputs/calibrated_all4/` |
| Primary protocol | `reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/` (per-query/per-ranker min-max calibration + raw-reference retention-matched thresholds) |
| Datasets | `bright`, `fiqa`, `hotpotqa`, `scidocs`; regimes `ms1`, `ms1_drop_mutual`, `ms2` |
| Per-query graph/candidate data | `.../<dataset>/<regime>/query_records.jsonl` |
| Query-level canonical metrics | `.../<dataset>/<regime>/query_method_metrics.csv`, `alpha_query_metrics.csv` |

### Candidate-graph sizes (primary protocol, `ms1`)

| Dataset | n_nodes | # queries (ms1) |
|---|---|---|
| bright | 20 | 50 |
| fiqa | 20 | 120 |
| scidocs | 20 | 120 |
| hotpotqa | 10 | 52 |

All three regimes (`ms1`, `ms1_drop_mutual`, `ms2`) share the same candidate pools per
query (same `n_nodes`); only the retained edge set changes with the vote regime. This
directly bounds the exact-ILP linear-ordering formulation size: `n*(n-1)` binary
variables and `C(n,2) + 2*C(n,3)` constraints — at n=20 that is 380 vars / 2,470
constraints; at n=10 it is 90 vars / 285 constraints. Trivial for SCIP.

## Existing repair implementations found

1. `src/consistency_ranker/greedy_fas.py` — **canonical** repair (`greedy` cycle-peeling
   heuristic via NetworkX cycle discovery). This produced `reports/full_calibrated_core/`.
2. `src/consistency_ranker/mwfas_solver.py` — dispatcher; `method="ilp"` is an exact
   linear-ordering MIP formulation **hardcoded to `gurobipy`** (unavailable). This
   investigation does not modify this file; it ports the same formulation to SCIP in a
   new, separate module (`scripts/exact_ilp_scip.py`) so the canonical dispatcher and its
   behavior are untouched.
3. `src/consistency_ranker/exact_fas.py` — a *different* exact method: brute-force
   enumeration of all `n!` permutations, feasible only for `n<=10`. Used here purely as an
   **independent cross-check** of the new SCIP ILP port (Phase 3), not as the study's main
   exact method (it cannot scale to the `n=20` bright/fiqa/scidocs graphs).
4. `reports/additional_metrics_investigation/scripts/run_additional_metrics.py` — a prior,
   unrelated investigation that already built (and validated) nDCG/MRR/MAP/Recall/
   Precision/Success computation plumbing against the canonical calibrated_all4 primary
   protocol, comparing unrepaired vs. **greedy**-repaired graphs. This investigation reuses
   its metric helpers and the shared `full_calibration_utils.py` module (both read-only,
   unmodified) but adds a third condition (exact SCIP-ILP-repaired) that script does not
   compute.

## What this investigation adds

A new evaluator subclass that overrides only the repair step (`_apply_repair`) to call the
open-source SCIP exact ILP solver instead of `greedy_fas`, while reusing every other piece
of the canonical evaluation pipeline unchanged (candidate pools, calibration thresholds,
graph construction, downstream ranking methods, metric implementations). This isolates the
repair-method variable exactly as the task requires.
