# Findings — Gurobi vs. SCIP Solver Cross-Validation

**Question investigated:** Now that a working Gurobi 13.0.2 academic WLS license is
available on this machine for the first time (previously Gurobi was completely
unusable — see `reports/_archive/exact_ilp_repair_investigation_SUPERSEDED/`), does
the commercial Gurobi MWFAS backend (`mwfas_solver.solve(..., method="gurobi")`)
independently agree with the canonical, open-source SCIP backend
(`method="scip"`) on the same 1,025 production preference graphs used to produce
`reports/exact_open_source_ilp_repair_investigation/`?

**This is an internal correctness/robustness check only.** Per
`papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`
and the repo's own documentation, Gurobi is never used to produce any manuscript
result, and this investigation does not change that — its sole purpose is
independent verification of the canonical SCIP-based exact-repair results using a
second, mature, industrial-grade MIP solver.

## Bottom line

**Perfect agreement. No discrepancies of any kind found.**

- **1,025 / 1,025** canonical queries (bright/fiqa/hotpotqa/scidocs × ms1/ms1_drop_mutual/ms2,
  `primary_minmax_retention_matched` protocol) solved by both backends.
- **0** objective-value mismatches (tolerance 1e-6).
- **0** removed-edge-set mismatches.
- **0** queries where either solver failed to reach proven optimality.
- Both solver calls went through the actual shipped `consistency_ranker.mwfas_solver`
  module (not a reimplementation), so this also cross-validates that module's own
  SCIP path against the separate ported copy used in
  `reports/exact_open_source_ilp_repair_investigation/scripts/exact_ilp_scip.py`
  (which had already been validated against brute-force independently).

## Timing

| | SCIP | Gurobi |
|---|---|---|
| Total solve time (1,025 queries) | 7.43s | 7.64s |
| Mean | 7.2ms | 7.5ms |
| Max (single query) | 23.7ms | 178.7ms |

At this problem size (n=20 nodes, 380 vars, 2,470 constraints), SCIP and Gurobi
are comparably fast — both solve essentially instantly. Gurobi's higher max is
consistent with per-call Python/model-construction overhead, not solver
difficulty; neither backend came close to any time limit. This size regime does
not distinguish the two solvers' scaling behavior — see the companion
`reports/exact_solver_scaling_study_20260731T162314Z/` for that question at
larger n.

## What this confirms

The paper's central exact-repair claim (`reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`:
exact repair removes materially less weight than greedy on the 379 cyclic
queries, but this does not change the retrieval-level conclusion) now has
**two independent solver implementations agreeing on every single instance**,
in addition to the pre-existing brute-force cross-check on 49 synthetic/real
cases. This is the strongest form of solver-correctness evidence available for
this formulation.

## What was held fixed / not modified

`mwfas_solver.py`, `full_calibration_utils.py`, and every canonical output under
`reports/full_calibrated_core/` and `reports/exact_open_source_ilp_repair_investigation/`
were read-only inputs. No repository code was modified — the two solver
backends already existed in `mwfas_solver.py`; this investigation only added a
new script (`scripts/run_gurobi_vs_scip_cross_validation.py`) that calls both
through the existing public `solve()` API.

## Outputs

- `tables/gurobi_vs_scip_per_query.csv` — per-query comparison (objective, gap,
  status, removed-edge-set match, timing, for both solvers).
- `manifests/cross_validation_summary.json` — top-line counts.
- `logs/run_20260731_162314.log` — full tmux session log.

## Recommendation

No code changes needed or warranted — no bug was found. This result can be
cited internally (e.g., in `docs/RESULTS_AUDIT.md` or a future revision note)
as an additional, non-manuscript robustness confirmation of the exact-repair
pipeline's correctness, consistent with the existing policy of not introducing
Gurobi into the manuscript itself.
