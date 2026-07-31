# Findings — Exact MWFAS Solver Scaling Study (SCIP vs. Gurobi)

**Question investigated:** `src/consistency_ranker/greedy_fas.py`'s own docstring
asserts "the exact ILP back-end does not scale as well as this heuristic ...
prefer greedy for large graphs" — but this was never empirically measured
beyond n=20 (the largest candidate-pool size used anywhere in the canonical
pipeline) with either exact solver. Every synthetic scale-sweep experiment at
n=50/n=100 (`outputs/scale_sweep_n50`, `outputs/scale_sweep_n100`) used greedy
only. With a working Gurobi license available for the first time, this
investigation asks: (a) is the "exact doesn't scale" assumption actually true,
and where does it break down? (b) does Gurobi meaningfully extend the
tractable range beyond SCIP?

**Method:** synthetic cyclic preference graphs (same generators as
`scripts/run_exact_vs_greedy.py`: `generate_items`/`generate_preferences`/
`build_graph`, margin weighting, noise=0.20), n ∈ {15, 20, 25, 30, 40, 50, ...},
2 seeds each, 30s time limit per solve per backend. SCIP solved via
`mwfas_solver.solve(method="scip", time_limit_s=30)` (module's own public
time-limited path, unmodified). Gurobi solved via a local copy of
`mwfas_solver._solve_gurobi`'s exact formulation with `Params.TimeLimit` added
(the module's own Gurobi path does not expose a time limit; this avoids
modifying `mwfas_solver.py`). Adaptive stopping: grid halts once every seed at
a given n fails to prove optimality on **both** backends within the time limit.

## Bottom line

**The "exact doesn't scale past ~n=20-30" assumption is confirmed true — and Gurobi meaningfully, but not dramatically, extends the tractable range.**

| n | vars | constraints | SCIP time (s) | SCIP proven optimal | Gurobi time (s) | Gurobi proven optimal |
|---|---|---|---|---|---|---|
| 15 | 210 | 1,015 | 0.01–0.02 | yes | 0.01–0.02 | yes |
| 20 | 380 | 2,470 | 0.03–0.06 | yes | 0.02–0.03 | yes |
| 25 | 600 | 4,900 | 0.04–0.07 | yes | 0.05–0.06 | yes |
| 30 | 870 | 8,555 | **5.9–11.0** | yes | **0.27–0.46** | yes |
| 40 | 1,560 | 20,540 | **timeout (30s)** | **no** | **4.5–9.6** | **yes** |
| 50 | 2,450 | 40,425 | timeout (30s) | no | timeout (30s), gap 3.3–6.3% | no |

- Up to n≈25 both solvers are effectively instantaneous and indistinguishable.
- At n=30 a real, sudden gap opens: SCIP takes 6–11s (still proven-optimal),
  Gurobi is **~20–40× faster** (0.27–0.46s) on the identical instances.
- At n=40, SCIP **can no longer prove optimality within 30s at all**, while
  Gurobi still solves both seeds to proven optimality (4.5s and 9.6s). This is
  the clearest new finding: **Gurobi extends the exactly-solvable frontier
  by roughly 10 nodes over SCIP** at this time budget, on this problem family.
- At n=50, both solvers fail within 30s — Gurobi's best incumbent has only a
  3.3–6.3% optimality gap (i.e. it's close, just not certified), SCIP's status
  gives no usable incumbent under this script's error handling (a minor gap in
  this investigation's own recovery path, not a `mwfas_solver.py` issue — see
  Caveats).
- The transition is sharp (near-instant → intractable within one grid step,
  25→30→40), consistent with the O(n³) growth in transitivity constraints
  (2,470 → 40,425 constraints from n=20 to n=50, a 16× increase) combined with
  NP-hardness of the underlying problem.

## Why this matters for the paper

This directly and empirically supports the manuscript's implicit design
decision to use greedy repair in production pipelines (which run on n=20
candidate pools comfortably within the fast/instantaneous regime found here,
consistent with `reports/exact_open_source_ilp_repair_investigation/`'s
observed 7-9ms per-query solve times) rather than exact solving at the n=50/100
scales explored in `outputs/scale_sweep_n50`/`outputs/scale_sweep_n100` for
other (non-repair-focused) synthetic experiments — those scales are
**genuinely intractable for exact MWFAS**, not merely inconvenient, even with
a commercial solver and even with only a modest 30s per-instance budget.

## Caveats

- Small sample (2 seeds/n) — this characterizes the general shape of the
  scaling wall, not tight per-n confidence intervals.
- `run_solver_scaling_study.py`'s SCIP error-recovery path (catching the
  `RuntimeError` that `mwfas_solver.solve()` raises when not proven optimal)
  does not recover SCIP's best incumbent objective/gap at the time limit —
  it only records "timed out, no optimality proof." This is a limitation of
  this investigation script, not of `mwfas_solver.py` itself (which
  deliberately raises rather than silently returning an unproven result —
  correct, conservative behavior for a canonical-reproduction tool). Not
  worth a code change: the qualitative finding (SCIP fails to *certify*
  optimality by n=40, Gurobi still does) is unaffected either way.
- A single time limit (30s) and a single synthetic graph family (margin
  weighting, noise=0.20) were used; different weight schemes / noise levels
  could shift the exact crossover point somewhat, though the underlying
  O(n³)-constraint / NP-hard scaling story would not change qualitatively.

## What was held fixed / not modified

`mwfas_solver.py` was not modified. The Gurobi time-limited solve is a local,
investigation-only copy of `_solve_gurobi`'s formulation (documented in the
script's own docstring) — this mirrors the pattern already used by
`reports/exact_open_source_ilp_repair_investigation/scripts/exact_ilp_scip.py`
(a ported copy of the SCIP formulation, also never touching the canonical
module).

## Outputs

- `tables/solver_scaling_per_instance.csv` — per-(n, seed, solver) results
  (resumable: reruns skip already-completed rows).
- `logs/run_20260731_162314.log` — full tmux session log.

## Recommendation

No code changes needed — no bug found; this is a scaling/performance
characterization, not a correctness issue. Worth citing internally as
empirical support for the existing "greedy for large graphs, exact only for
small ones" design principle, if a future revision wants to justify that
choice with data instead of assumption alone. Not recommended for the
manuscript itself, consistent with the existing Gurobi-exclusion policy.
