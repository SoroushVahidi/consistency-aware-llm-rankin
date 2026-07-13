# External Solver Execution Trace

**Prepared:** 2026-07-12
**Scope:** Part A3 — for each stronger-repair result in `experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv`, trace exactly what code ran, with what parameters, on what population, and whether it can be rerun today. Labels are not trusted at face value; every claim below is traced to a specific line of code or manifest entry.

---

## How the run was launched

- **Command:** `python /home/soroush/consistency-aware-llm-rankin/experiments/final_method_gap_audit_20260711_221113/run_final_method_gap_audit.py` (`run_in_tmux.sh` line 6).
- **Interpreter:** `/home/soroush/modal-venv/bin/python` — a **different virtualenv** from this repository's own `.venv` (`run_in_tmux.sh` line 5-6). `PYTHONPATH` was set to `.../consistency-aware-llm-rankin/src` (line 5), so this repo's own package (`consistency_ranker`) was importable, but nothing in that `PYTHONPATH` setting makes `mwfas` importable — that comes purely from the `sys.path.insert` calls inside `run_method_improvement_audit.py`, which are absolute and machine-specific, independent of which venv launched the interpreter.
- **Timing:** whole run started `2026-07-11 22:48:21`, task2 (repair comparison, the branch containing all six repair methods) ran `22:48:52`–`22:59:24` (~10.5 minutes), status `completed` (`RUN_MANIFEST.json`).
- **Failures:** `logs/failures/` directory is empty (checked this session: `find .../logs/failures -type f | wc -l` → `0`). No exception was ever recorded via `self.record_failure(...)` for any repair mode.

---

## Per-method trace

### `greedy` (canonical, in-repository)

- **Function called:** `src/consistency_ranker/greedy_fas.py::greedy_fas` (imported and called directly; no external path).
- **Backend:** cycle-peeling heuristic (find any cycle, remove its minimum-weight edge, repeat).
- **Input population:** all 1,020 query×regime records from `experiments/failure_class_audit_20260711_212157/analysis/canonical_query_records.jsonl` (`RUN_MANIFEST.json` field `canonical_records`).
- **Seed:** none required (deterministic given the input graph and NetworkX's `find_cycle` iteration order).
- **Timeout:** none applied (`repair_mode not in {"exact_scc_dp20", "lrta_external", "wmsf_external", "ipsns_external"}` branch, `run_final_method_gap_audit.py:1089-1104` — calls `_evaluate_repair_light` directly, no `_run_with_timeout` wrapper).
- **Fallback behavior:** none needed; the greedy heuristic always terminates.
- **Completeness:** complete — 1,020/1,020 rows present in `repair_comparison_per_query.csv` (verified this session: `cut -d, -f4 repair_comparison_per_query.csv | sort | uniq -c` → `1020 greedy`).
- **Rerunnable now?** Yes, fully, using only this repository.

### `no_repair` (trivial baseline)

- **Function called:** inline in `run_method_improvement_audit.py::_apply_repair`, `mode == "no_repair"` branch — returns `graph.copy()` with an empty removed-edges list. Not a solver at all.
- **Population / seed / timeout:** same as `greedy` (all 1,020 records, no timeout, deterministic).
- **Completeness:** 1,020/1,020 rows (`repair_comparison_per_query.csv`).
- **Rerunnable now?** Trivially yes.

### `exact_small_greedy_hybrid` (in-repository, canonical "stronger repair")

- **Function called:** `apply_exact_small_greedy_hybrid` defined inline in `run_final_method_gap_audit.py:270-315`, itself calling `src/consistency_ranker/exact_fas.py::exact_fas` (brute-force permutation enumeration) for each strongly connected component with ≤10 nodes (`EXACT_BRUTE_MAX = 10`, line 80), and `src/consistency_ranker/greedy_fas.py::greedy_fas` as a fallback for components of 11–20 nodes or larger (both fallback branches recorded in `skipped_sccs` with a `"reason"` field: `"exact_fas_limit"`, `"scc_11_20_greedy_fallback"`, or `"size_gt_20_greedy"`).
- **Backend:** exact for small SCCs, greedy for the rest, all in-repository.
- **Population:** all 1,020 records.
- **Timeout:** none (not in the `{"exact_scc_dp20", "lrta_external", "wmsf_external", "ipsns_external"}` timeout set).
- **Completeness:** 1,020/1,020 rows.
- **Rerunnable now?** Yes, fully, using only this repository. This is the method actually used for the pooled `best_stronger_repair` row in Table 6 (Results, not yet drafted) — confirmed by `REPAIR_COMPARISON_FINAL_REPORT.md` line 7: "Best stronger repair selected for Task 3: `exact_small_greedy_hybrid`."

### `exact_scc_dp20`, `lrta_external`, `wmsf_external`, `ipsns_external` (external-package-dependent)

- **Function called:** `run_method_improvement_audit.py::_apply_external_repair` (lines 1025–1074), dispatching by `mode` to, respectively: `mwfas.exact.exact_min_fas_from_dimacs`, `mwfas.lrta.paper_fas_ranking_from_dimacs_fast`, `mwfas.wmsf.wmsf_ranking_from_dimacs_fast`, `mwfas.ipsns.lns_merge_wmsf_lr_best_incumbent` — all imported via `sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")` immediately before the respective import (lines 1042, 1047, 1052, 1057).
- **Data interchange:** the graph is serialized to a temporary **DIMACS** arc-list file (`tmp_dir / f"{mode}_{ts}.gr"`, lines 1029-1039), the external function is called with that file path plus an output CSV path, and the resulting node ordering is read back from the output CSV (lines 1070-1074). This is a file-based interchange, not an in-process call — the external package's functions accept file paths, not graph objects, in their public API as used here.
- **`ipsns_external`-specific parameter:** `iters=40` (hardcoded at the call site, `run_method_improvement_audit.py:1060-1066`); the external repository's own documentation (`docs/baselines_and_datasets_references.md`) records substantially higher iteration counts for its own experiments (200–400), so this specific invocation uses a **lower iteration budget** than the external package's own reported experiments — worth flagging if IPSNS's negative-looking nDCG result is ever discussed in Results, since it may partly reflect an under-budgeted run rather than the algorithm's ceiling performance.
- **Population:** capped to at most `EXTERNAL_CYCLIC_CAP = 100` cyclic queries (`run_final_method_gap_audit.py:82`), sampled via `random.Random(42).sample(cyclic, 100)` when more than 100 cyclic queries exist (`_cyclic_external_cap`, lines 967-974) — i.e., **not all cyclic queries**, a fixed-seed subsample.
- **Additional gate for `exact_scc_dp20` only:** within that 100-query cap, `exact_scc_dp20` is further restricted to queries whose largest SCC has ≤20 nodes (`EXACT_SCC_MAX = 20`, `_should_run_expensive_repair`, lines 985-989); `lrta_external`/`wmsf_external`/`ipsns_external` have no such additional size gate and run on the full 100-query cap.
- **Timeout:** `EXTERNAL_REPAIR_TIMEOUT = 10` seconds per query, enforced via a `SIGALRM`-based wrapper (`_run_with_timeout`, lines 956-966); a timeout raises `TimeoutError`, which is caught by the enclosing `except Exception` and recorded via `self.record_failure(...)`.
- **Completeness:** **complete for all four methods** — each has exactly 100 rows in `repair_comparison_per_query.csv` (verified this session), and `logs/failures/` is empty, meaning zero timeouts or exceptions were recorded across the whole run. This is a genuinely complete run of the capped sample, not a partial/degraded one.
- **Rerunnable now?** **Not from this repository alone.** Rerunning requires the sibling repository `minimum-weighted-fas-heuristics` to exist at the exact absolute path `/home/soroush/minimum-weighted-fas-heuristics` (or the two lines of `sys.path.insert` to be edited to point elsewhere), which is a machine-specific precondition not encoded anywhere in this repository's own reproduction instructions (`docs/REPRODUCTION_Q1.md`).

---

## Summary judgment

Every one of the four external-dependent methods produced a **complete, un-timed-out, seed-fixed run** on a **bounded 100-query sample** — this is a real, honest result, not a broken or partial one. The dependency is genuine (a hardcoded absolute path to a sibling repository), but it does not taint the completeness or determinism of the specific numbers reported. The main risk is **reproducibility by someone other than the author**, not correctness of what's reported.
