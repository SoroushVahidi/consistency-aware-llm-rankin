# Running Jobs

**tmux session `exact_ilp_repair`:** does not exist. Confirmed via
`tmux has-session -t exact_ilp_repair` (exit code 1, "can't find session").

**No exact-ILP execution has been launched.** Investigation is currently blocked at
Phase 1 (Gurobi verification) — see `INITIAL_STATE.md` and `COMMANDS_EXECUTED.md` for
the full verification trail. No job will be launched until the path forward (see the
options in the main report / the question put to the user) is confirmed, per the task's
own caution against restarting or duplicating Gurobi jobs without first checking status.

Last updated: 2026-07-13, immediately after Phase 0/1 completed.
