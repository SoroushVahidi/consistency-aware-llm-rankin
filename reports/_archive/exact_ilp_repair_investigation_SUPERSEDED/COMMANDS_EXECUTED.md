# Commands Executed — Phase 0 / Phase 1

All commands below are read-only with respect to the repository (no `git add`/`commit`/
`push`/`checkout`/`reset`; the only filesystem writes were new files under
`reports/exact_ilp_repair_investigation/`).

## Repo/branch/HEAD detection

```bash
cd ~/consistency-aware-llm-rankin && pwd
git rev-parse --abbrev-ref HEAD          # -> main
git rev-parse HEAD                        # -> 873fa3199432ab27c738fb1ffccb86385adfaa25
git log -1 --format='%H %ad %s' --date=iso
git status                                 # full output: /tmp/git_status_snapshot.txt (103 lines)
git remote -v
```

## Environment

```bash
.venv/bin/python --version                # 3.12.3
.venv/bin/python -c "import sys; print(sys.executable)"
which python3; python3 --version
nproc; lscpu | grep -E "Model name|CPU\(s\):"
free -h
df -h ~
.venv/bin/pip list | grep -iE "networkx|pandas|numpy|scipy|gurobi|pulp|ortools|matplotlib|pytest"
```

## Gurobi verification (Phase 1)

```bash
which gurobi_cl || true                    # command not found
gurobi_cl --version || true                # command not found

.venv/bin/python - <<'PY'
try:
    import gurobipy as gp
    print("GUROBI_VERSION", gp.gurobi.version())
    env = gp.Env()
    m = gp.Model("test", env=env)
    print("MODEL_OK", m)
except Exception as e:
    print("IMPORT_ERROR", repr(e))
PY
# -> IMPORT_ERROR ModuleNotFoundError("No module named 'gurobipy'")

grep -i gurobi requirements.txt pyproject.toml   # no matches
.venv/bin/pip show gurobipy                       # not found
find / -maxdepth 6 -iname "*gurobi*" 2>/dev/null  # no matches
/home/soroush/modal-venv/bin/python3 -c "import gurobipy"  # ModuleNotFoundError
env | grep -i gurobi                              # empty
find / -maxdepth 4 -iname "gurobi.lic" 2>/dev/null  # no matches
```

## Existing repair-implementation inventory (Phase 0)

```bash
grep -rniIE "gurobipy|Model\(|feedback arc|MWFAS|linear ordering|transitivity constraint|lazy constraint|SCC decomposition|MIPGap|TimeLimit|optimality status" \
  --include="*.py" --exclude-dir=.venv --exclude-dir=.git -l .
```
Result: 23 files (list in `manifests/ilp_grep_files.txt`). Read in full:
`src/consistency_ranker/mwfas_solver.py`, `src/consistency_ranker/exact_fas.py`,
`scripts/run_exact_vs_greedy.py`.

## Canonical graph-size survey

```bash
for f in reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/*/ms1/query_records.jsonl; do
  python3 -c "
import json
counts=[]; nodes=[]
for line in open('$f'):
    d=json.loads(line)
    counts.append(d.get('candidate_count'))
    nodes.append(d['graph_stats']['n_nodes'])
print('candidate_count set:', sorted(set(counts)))
print('n_nodes min/max/mean:', min(nodes), max(nodes), sum(nodes)/len(nodes))
print('num queries:', len(nodes))
"
done
```
Result: bright/fiqa/scidocs all have n_nodes=20 uniformly; hotpotqa n_nodes=10 uniformly.
342 total queries in the `ms1` sub-condition across all four datasets (50+120+120+52).

## Outcome of Phase 0/1

Gurobi is confirmed unavailable (no package, no CLI, no license file/env var) on this
machine and in every Python environment checked. This blocks any actual Gurobi-ILP
execution. Proceeding to flag this to the user before Phase 2 (study design/execution)
per the task's own instruction: "First verify whether Gurobi is actually usable."
No exact_ilp_repair tmux session has been created; none will be created until the path
forward is confirmed, per the "do not restart a quiet Gurobi job without first checking
the process" / "do not launch duplicate sessions" cautions in the task brief.
