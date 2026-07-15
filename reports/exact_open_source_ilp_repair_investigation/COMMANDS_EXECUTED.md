# Commands Executed

All commands below are read/append-only with respect to the repository (no `git add` /
`commit` / `push` / `checkout` / `reset`). The only filesystem writes were new files under
`reports/exact_open_source_ilp_repair_investigation/`, plus one package install into the
local `.venv` (see Phase 1).

## Repo/branch/HEAD detection (Phase 0)

```bash
cd ~/consistency-aware-llm-rankin
git rev-parse --abbrev-ref HEAD          # -> main
git rev-parse HEAD                        # -> 873fa3199432ab27c738fb1ffccb86385adfaa25
git status                                # 4 unrelated modified files + untracked dirs
git log --oneline -10
```

## Environment inspection (Phase 0)

```bash
which python python3; python3 --version   # 3.12.3
ls -la .venv
nproc; free -h; df -h .
```

## Reviewed prior investigation (Phase 0)

```bash
# reports/exact_ilp_repair_investigation/ already existed (untracked) — a prior attempt
# at this same question using Gurobi, blocked at Phase 1 because Gurobi is not
# installed/licensed anywhere on this machine. Read in full (read-only):
cat reports/exact_ilp_repair_investigation/INITIAL_STATE.md
cat reports/exact_ilp_repair_investigation/COMMANDS_EXECUTED.md
cat reports/exact_ilp_repair_investigation/RUNNING_JOBS.md
cat reports/exact_ilp_repair_investigation/tables/repair_implementation_inventory.csv
```

## Existing repair-implementation inventory (Phase 0)

Read in full: `src/consistency_ranker/mwfas_solver.py`, `src/consistency_ranker/greedy_fas.py`,
`src/consistency_ranker/exact_fas.py`, `reports/full_calibrated_core/scripts/full_calibration_utils.py`,
`experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py`
(`AuditRunner._apply_repair`), `reports/additional_metrics_investigation/scripts/run_additional_metrics.py`,
`src/consistency_ranker/evaluation.py`.

## Phase 1 — open-source solver detection and installation

```bash
source .venv/bin/activate
python - <<'PY'
mods = ["pyscipopt", "highspy", "scipy", "pulp", "mip"]
for m in mods:
    try:
        mod = __import__(m)
        print(m, "AVAILABLE", getattr(mod, "__version__", "unknown"))
    except Exception as e:
        print(m, "UNAVAILABLE", repr(e))
PY
# -> pyscipopt UNAVAILABLE (not yet installed); scipy AVAILABLE 1.18.0 (milp available,
#    HiGHS-backed); highspy/pulp/mip UNAVAILABLE
which scip highs cbc glpsol   # none on PATH

# Network check + safe local-venv-only install of the top-preference open-source solver:
pip install --dry-run pyscipopt   # confirmed resolvable from PyPI
pip install pyscipopt             # installed PySCIPOpt-6.2.1 into .venv only

python - <<'PY'
import pyscipopt
from pyscipopt import Model
m = Model("smoketest")
x = m.addVar("x", vtype="B"); y = m.addVar("y", vtype="B")
m.addCons(x + y <= 1)
m.setObjective(x + y, "maximize")
m.hideOutput(); m.optimize()
print("status:", m.getStatus(), "gap:", m.getGap(), "obj:", m.getObjVal())
PY
# -> status: optimal  gap: 0.0  obj: 1.0
```

## Phase 2 — port Gurobi ILP formulation to SCIP

Wrote `scripts/exact_ilp_scip.py` (`solve_ilp_scip`), mirroring
`mwfas_solver.py::_solve_ilp`'s linear-ordering MIP exactly (same variables, same
antisymmetry/transitivity constraints, same objective), but using PySCIPOpt, with
`limits/time` and `limits/gap` params and a strict `getStatus() == "optimal"` check
before trusting any result. `mwfas_solver.py` itself was not touched.

```bash
python -m py_compile reports/exact_open_source_ilp_repair_investigation/scripts/exact_ilp_scip.py
```

## Phase 3 — independent validation against brute-force exact_fas

```bash
python reports/exact_open_source_ilp_repair_investigation/scripts/validate_scip_vs_bruteforce.py
# -> n_cases=49 all_match=True all_proven_optimal=True; VALIDATION PASSED
#    (34 synthetic random cyclic graphs n in {4,6,8,10} + 15 real hotpotqa n=10 graphs
#    from the canonical calibrated_all4 primary-protocol package)
```

## Phase 4 — full canonical-data exact-ILP run (tmux, mandatory per task policy)

```bash
tmux has-session -t exact_open_ilp_repair 2>/dev/null   # confirmed: no existing session
tmux new-session -d -s exact_open_ilp_repair \
  "cd /home/soroush/consistency-aware-llm-rankin && \
   source .venv/bin/activate && \
   python -u reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py \
   2>&1 | tee reports/exact_open_source_ilp_repair_investigation/logs/exact_open_ilp_repair.log"
```

Scope: 4 datasets x 3 vote regimes under `primary_minmax_retention_matched`, 1,025
queries. Completed in 27.1s; all 1,025 solves proven-optimal (`status == "optimal"`),
max per-query solve time 236ms. Session was killed after the script exited cleanly
(`tmux kill-session -t exact_open_ilp_repair`).

## Phase 5 — structural/retrieval comparison

Analysis run inline (not in tmux — well under the "full exact-ILP execution and full
statistical analysis" runtime threshold that motivated the tmux mandate; the heavy
compute, the actual 1,025-query ILP solve + full metric computation, was the Phase 4
tmux run). Bootstrap CIs (10,000 reps) and paired-permutation p-values (10,000 reps),
Holm/BH correction, computed inside `run_exact_open_ilp_study.py` itself as part of the
same tmux-run process — see `tables/retrieval_metric_paired_summary*.csv`.
