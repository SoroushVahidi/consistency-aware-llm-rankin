# Outcome F Production Remediation

**Date:** 2026-07-26 (local)
**Branch:** `fix/outcome-f-production-operating-point` (created from dirty `main`; no work discarded, nothing committed or pushed)
**Scope:** the Critical and High findings in `AUDIT_LOCAL_BRANCH.md`, plus the mypy debt (F-012)
**Billed API calls:** none. Every command below uses synthetic judges or local files.

---

## 1. Final Verdict

**PRODUCTION OPERATING POINT ENFORCED**

The interim operating point is now executable code rather than documentation:
`PolicySelector()` resolves to always-UHT in `production_uht` mode, learned gates
require an explicit `ExecutionMode.EXPERIMENTAL_GATE`, the safety floor executes
inside the UHT path and cannot rewrite the executed policy, and the mandatory
outsider probe / weak-evidence stop ban / final challenger check are invoked and
observable in the returned result.

One caveat, stated plainly because it is a process item rather than a behaviour
item: **F-004 (the stack is uncommitted) is not resolved**, because the task
forbids committing. A dedicated branch exists and all work is on it; a reviewer
still needs a commit to review a diff. See §9.

The Outcome F empirical record is untouched and was reproduced bit-for-bit after
the remediation (§7).

---

## 2. Original Audit Findings Addressed

| ID | Severity | Root cause | Fix | Tests | Status |
|---|---|---|---|---|---|
| F-001 | Critical | `PolicySelector.mode` defaulted to `selective_three_way`; no typed notion of "production" existed, so defaults were per-call-site opinions | New `ExecutionMode` enum and frozen `ProductionPolicyConfig`; `PolicySelector` defaults to `always_uht` + `PRODUCTION_UHT`; a learned gate mode or attached calibration model raises in production mode; unknown modes raise instead of resolving | `test_default_selector_is_production_uht`, `test_default_select_policy_executes_uht`, `test_no_omitted_argument_enables_selective_three_way`, `test_attaching_calibration_model_in_production_is_rejected`, `test_unknown_modes_are_rejected_not_mapped`, `test_environment_variables_cannot_enable_learned_routing`, `test_production_config_is_frozen_and_locked_to_uht` | **Resolved** |
| F-002 | Critical | `apply_fallback_constraints` answered a safeguard *request* by renaming the policy (UHT → HYBRID/CHALLENGER), so the floor was a hidden gate | Renamed to `apply_experimental_escalation` and confined to experimental mode; added `NON_ROUTING_ACTIONS` + `production_safety_actions`; production executes the requests as actions inside UHT via `ProductionSafeguards` | `test_safety_floor_does_not_rewrite_uht_in_production`, `test_same_condition_may_reroute_only_under_experimental_mode`, `test_threshold_equality_at_safety_floor_boundary`, `test_weak_evidence_stop_is_rejected_and_adds_evidence` | **Resolved** |
| F-003 | Critical | The gated runner called `evaluate_safeguards` once with `intending_stop=False`, so the stop ban and final challenger branches were unreachable | New `production_runner.run_production_uht` executes the outsider probe, evaluates the stop decision, acquires the missing top-k evidence when the stop is blocked, and runs the final challenger check, each exactly once | `test_all_safeguards_actually_execute`, `test_final_challenger_runs_even_when_stop_is_not_blocked`, `test_safeguards_are_not_executed_twice`, `test_safeguard_exception_still_returns_uht_ranking`, `test_end_to_end_production_operating_point` | **Resolved** |
| F-004 | Critical (process) | All Outcome F work is untracked on `main`; there is no commit range to review | Dedicated branch `fix/outcome-f-production-operating-point` created without discarding work. Committing is explicitly out of scope for this task | n/a | **Not resolved** (deliberately; see §9) |
| F-005 | High | `mkdir(..., exist_ok=False)` plus a hard-coded output path made `REPRODUCE.sh` fail on any second run | Added `--overwrite-existing`; generated `REPRODUCE.sh` now adds the flag automatically when the target directory exists and accepts an alternative path as `$1`; a dated note in the report directory gives both commands for the historical script | `test_research_cli_help_labels_itself_as_research` (flag present); verified by re-running the experiment twice into `/tmp/ps_verify` | **Resolved** |
| F-006 | High | Oracle "gap" mixes live gated utilities with offline population utilities | Not fixed. It is an experiment-analysis issue, changing it would alter the frozen Outcome F numbers, and the direction of the oracle advantage is unaffected | n/a | **Deferred** (documented in §9) |
| F-007 | High | Calibration accuracy ≈ majority-class rate was reported as if it showed discrimination | `IMPLEMENTATION_STATUS_20260726.md` and the updated `scripts/AUDIT_POLICY_GATE.md` lead with the decision-relevant result (no learned gate beat always-UHT) instead of accuracy. The stored metrics are unchanged | n/a | **Documented** |
| F-008 | High | No test asserted the production default or floor-without-reroute | New `tests/test_production_operating_point.py`: 31 contract tests covering defaults, floor semantics, safeguard execution via spies, diagnostic isolation, CLI resolution, and an end-to-end run | whole file | **Resolved** |
| F-009 | High | Held-out n=12 is too small to freeze thresholds | Not a code defect. The production point deliberately freezes *no learned threshold*: it is always-UHT plus fixed safeguards, which is exactly the conclusion n=12 supports | n/a | **Consistent by design** |
| F-012 | Medium | 36 mypy errors in `policy_selection` | All 36 fixed (§8), plus the 4 errors in the experiment runner | mypy run in §7 | **Resolved** |

---

## 3. Final Runtime Semantics

### `ExecutionMode.PRODUCTION_UHT` (default everywhere)

Executes UHT and only UHT. `select_policy` returns `UHT` without consulting a
model; `PolicySelector` refuses to be constructed with a learned gate mode or an
attached calibration model. The approved safeguards run inside the UHT path.
Missing configuration resolves here (`resolve_execution_mode(None)`), and
unknown values raise.

### `ExecutionMode.DIAGNOSTIC`

Executes UHT, and additionally runs the fixed `mixed_diagnostic` probe (budget 3)
and records what the configured gate would have chosen in
`diagnostic_recommendation`. The recommendation is allowed to disagree with what
ran; it cannot change it. A failure while computing the recommendation is caught
and recorded, and the run continues on UHT.

### `ExecutionMode.EXPERIMENTAL_GATE`

Research only. Unlocks hard, calibrated, selective, soft, staged, switching,
hybrid and challenger routing plus `apply_experimental_escalation`. It must be
requested explicitly on both the selector and the call; `run_gated_acquisition`
raises otherwise, and `run_production_uht` refuses the mode outright. No default
constructor, omitted flag, environment variable, or absent config value can
produce it.

### Safety floor

The floor is a **budget reservation plus three in-UHT actions**, not a mixture
weight and not a router:

1. `reserved_safety_calls` withholds `ceil(0.15 × budget)` calls (never fewer
   than the two mandatory actions) from the main UHT run.
2. A mandatory top-k-insider vs outsider probe runs before the main run.
3. After the main run, stopping is prohibited while the fraction of
   top-k-relevant pairs with acquired support is below 0.2 and budget remains;
   the blocked stop is spent acquiring exactly those unjudged pairs.
4. A final adversarial challenger comparison is evaluated before the ranking is
   returned.

At exactly the threshold (coverage == 0.2) the stop is **allowed** — the check is
a strict `<`, and that boundary is tested.

### Fallback

Every safeguard call is individually wrapped. An exception is appended to
`SafeguardLog.errors` and execution continues on plain UHT; the run still
returns a complete ranking. If a selector somehow returned a non-UHT policy in
production, the runner overwrites it with UHT and records the event.

---

## 4. Code Changes

### New files

| File | Behavioural change |
|---|---|
| `src/consistency_ranker/policy_selection/execution_mode.py` | Adds the typed `ExecutionMode` enum and `resolve_execution_mode`, which fails closed to production for `None` and raises on unknown strings. Replaces free-form mode strings. |
| `src/consistency_ranker/policy_selection/production_config.py` | Single authoritative production operating point: frozen `ProductionPolicyConfig` locked to `primary_policy="UHT"`, safety floor 0.15, probe `mixed_diagnostic`/3, and `reserved_safety_calls` implementing the floor as a budget reservation. |
| `src/consistency_ranker/policy_selection/production_runner.py` | The executable production path. `ProductionSafeguards` exposes each safeguard as a method (so tests can spy on real calls) and `run_production_uht` sequences probe → selection → UHT → stop check → final challenger, returning `executed_policy` / `diagnostic_recommendation` / `experimental_policy` as separate fields. Refuses experimental mode. |
| `scripts/run_production_uht.py` | Production CLI. Defaults to `production_uht`, offers only `production_uht`/`diagnostic`, prints the resolved mode and executed policy, and refuses any `CONSISTENCY_RANKER_GATE*` environment variable. |
| `tests/test_production_operating_point.py` | 31 contract tests (§6). |
| `reports/policy_selection_20260726T030500Z/IMPLEMENTATION_STATUS_20260726.md` | Dated note distinguishing the historical empirical record from today's enforced behaviour, and giving working reproduction commands. No existing artifact was edited. |

### Modified files

| File | Behavioural change |
|---|---|
| `policy_gate.py` | Default gate mode is `always_uht` and default execution mode is `PRODUCTION_UHT`. `__post_init__` rejects learned modes and attached models in production and rejects unknown modes. `select_policy` now branches on execution mode: production/diagnostic always return UHT; only experimental mode executes the gate recommendation, which moved into `_experimental_recommendation`. `GateDecision` gained `execution_mode`, `diagnostic_recommendation`, `experimental_policy` and an `executed_policy` property. Added `resolve_gate_mode`, `GATE_MODE_CHOICES`, `PRODUCTION_GATE_MODE`. Typing fixes (`reason` is `str`, `max(key=...)` lambdas, `pol_scores` widened). |
| `safe_fallback.py` | `apply_fallback_constraints` renamed to `apply_experimental_escalation` with a docstring saying it performs routing; added `NON_ROUTING_ACTIONS` and `production_safety_actions` for the production subset; module docstring now separates "safety enforcement within UHT" from "experimental policy switching". |
| `policy_runner.py` | `run_gated_acquisition` is explicitly experimental: it raises unless both the call and the selector carry `EXPERIMENTAL_GATE`, calls the renamed escalation helper, and returns `executed_policy` / `experimental_policy` / `diagnostic_recommendation` / `execution_mode` alongside the old keys. Behaviour under experimental mode is unchanged, which is why the benchmark reproduces exactly. |
| `policy_selection/__init__.py` | Exports the new execution-mode, production-config and production-runner symbols; the docstring states which paths are production and which are experimental. |
| `policy_calibration.py` | Beta-calibration locals renamed (`a, bb, c` → `beta_a, beta_b, beta_c`); they shadowed the one-vs-rest class variable `c: str`. No numeric change. |
| `policy_mixture.py` | `split_budget` return annotation widened to `dict[str, float]` (it always returned a float `g_eff`); the `# type: ignore` is gone. Runtime values unchanged. |
| `diagnostic_probes.py` | Cross-prior loop variable renamed to `prior` so it no longer shadows the pair variable `p`. No behaviour change. |
| `policy_benchmark.py` | `max(utils, key=utils.get)` → lambda form. No behaviour change. |
| `scripts/run_policy_selection_experiment.py` | Labelled a research script in the docstring, `--help` and epilog. All four `PolicySelector` constructions now pass `execution_mode=BENCHMARK_EXECUTION_MODE` explicitly. Added `--overwrite-existing` and `--mode` (rejecting non-experimental modes with a pointer to the production runner), prints the resolved execution mode, and emits a `REPRODUCE.sh` that can regenerate in place. Typing fixes for the shadowed `mode` loop variables and an unguarded `features_probe`. |
| `tests/test_policy_selection.py` | Updated to the renamed escalation helper and to opt into experimental mode where a learned gate is under test. `test_fallback_triggers` was **strengthened**: it now asserts the exact reroute (`CHALLENGER`) instead of a tautological disjunction. |
| `scripts/AUDIT_POLICY_GATE.md` | Added a dated §16 recording what is enforced today versus what was recommended. |

---

## 5. Production Call-Path Proof

Default construction through to the returned result:

1. **Default UHT selection.**
   `policy_gate.py:197` — `mode: GateMode = PRODUCTION_GATE_MODE` (`always_uht`).
   `policy_gate.py:211` — `execution_mode: ExecutionMode = ExecutionMode.PRODUCTION_UHT`.
   `policy_gate.py:213-235` — `__post_init__` rejects any learned mode (`:220`) or attached model (`:231`) in production.
   `policy_gate.py:481-500` — `select_policy` only enters the gate at `:500` when the mode is `EXPERIMENTAL_GATE`; otherwise it falls through to `:544`, `policy=_production_policy()`, which returns `"UHT"`.
   `execution_mode.py:65-84` — `resolve_execution_mode(None)` yields `PRODUCTION_UHT`; unknown strings raise at `:81`.

2. **Outsider probe execution.**
   `production_runner.py:389` reserves the floor budget; `:410` calls `guards.run_outsider_probe(...)`, implemented at `production_runner.py:163-190`, which judges a real insider-vs-outsider pair and returns whether it executed. The flag and the judged pair id are recorded in `SafeguardLog`.

3. **Weak-evidence stop prohibition.**
   `production_runner.py:462` calls `guards.check_weak_evidence_stop(...)` (`:198-206`, strict `<` against `min_evidence_fraction_to_stop = 0.2`). When it returns True, `:470` calls `guards.gather_additional_evidence(...)` (`:219-247`), which judges the unjudged top-k-relevant pairs rather than returning a different policy.

4. **Final challenger check.**
   `production_runner.py:491` calls `guards.run_final_challenger(...)` (`:249-263`), unconditionally when `require_final_challenger` is set, on both the blocked-stop and normal-stop paths. It is outside the stop branch, so no early return can skip it.

5. **Non-routing diagnostic behaviour.**
   `production_runner.py:432` selects the policy through the production-mode `select_policy`; `:526` returns `executed_policy="UHT"` with `experimental_policy=None`, and the recommendation is carried separately in `decision.diagnostic_recommendation`. Escalation lives only in `safe_fallback.py:175` and is called only from `policy_runner.py:334`, which is unreachable without the check at `policy_runner.py:243`.

6. **Safe fallback.**
   `production_runner.py:416`, `:465`, `:481`, `:496` catch safeguard exceptions into `SafeguardLog.errors` and continue on UHT; `:438` overrides any non-UHT selector output; `:357` refuses experimental mode entirely.

---

## 6. Tests Added

`tests/test_production_operating_point.py` (31 tests). Each entry states the regression it blocks.

**Defaults**
- `test_default_selector_is_production_uht` — a default constructor silently enabling selective gating (the exact F-001 state).
- `test_default_select_policy_executes_uht` — `select_policy` routing away from UHT with no selector supplied.
- `test_no_omitted_argument_enables_selective_three_way` — re-adding a learned mode to production without opting in.
- `test_attaching_calibration_model_in_production_is_rejected` — a loaded model quietly becoming a production router.
- `test_unknown_modes_are_rejected_not_mapped` — an unrecognised mode string being coerced to something experimental.
- `test_environment_variables_cannot_enable_learned_routing` — env-driven routing.
- `test_production_config_is_frozen_and_locked_to_uht` — a caller mutating the shared operating point or declaring a non-UHT primary.

**Safety floor**
- `test_safety_floor_does_not_rewrite_uht_in_production` — the F-002 reroute (outsider-beats-insider ⇒ CHALLENGER/HYBRID).
- `test_same_condition_may_reroute_only_under_experimental_mode` — losing the experimental escape hatch, or letting it leak into production.
- `test_threshold_equality_at_safety_floor_boundary` — silent drift in how 0.15 is turned into reserved calls.
- `test_weak_evidence_threshold_equality_is_documented_and_tested` — flipping the `<` at exactly 0.2, or blocking a stop with no budget left.
- `test_malformed_calibration_artifact_cannot_activate_learned_gating` — a corrupt model file changing production behaviour.
- `test_malformed_safety_data_fails_closed_to_uht` — a broken safeguard aborting the run instead of degrading to UHT.

**Safeguard execution (spies on real methods, not returned labels)**
- `test_all_safeguards_actually_execute` — safeguards being instantiated but never called (the F-003 state).
- `test_weak_evidence_stop_is_rejected_and_adds_evidence` — a blocked stop that buys nothing, or buys a policy change.
- `test_final_challenger_runs_even_when_stop_is_not_blocked` — the final check hiding behind the stop branch.
- `test_safeguards_are_not_executed_twice` — duplicated probes / duplicated final checks.
- `test_safeguard_exception_still_returns_uht_ranking` — an exception in a safeguard losing the ranking.
- `test_production_runner_refuses_experimental_mode` / `test_gated_runner_requires_explicit_experimental_opt_in` — the two runners swapping responsibilities.

**Diagnostic isolation**
- `test_diagnostic_recommendation_does_not_alter_executed_policy` — diagnostics regaining routing power.
- `test_strong_challenger_preference_still_executes_uht` — a confident CHALLENGER recommendation overriding production.
- `test_result_fields_keep_the_three_meanings_separate` — collapsing the three policy fields back into one.
- `test_replay_keeps_diagnostic_and_executed_outputs_separate` — serialized output that cannot distinguish recommendation from execution.

**CLI / configuration**
- `test_production_cli_defaults_to_production_uht` — an unsafe CLI default.
- `test_production_cli_rejects_experimental_gate` — experimental routing reachable from the production binary.
- `test_production_cli_help_labels_experimental_and_diagnostic` / `test_research_cli_help_labels_itself_as_research` — help text that lets a research script be mistaken for production.
- `test_research_cli_rejects_conflicting_mode` — a conflicting `--mode` silently proceeding (and creating an output directory).

**End-to-end (release critical)**
- `test_end_to_end_production_operating_point` — asserts, from resolved configuration to final result: executed policy UHT, gate mode `always_uht`, no diagnostic recommendation in production, each safeguard called exactly once, outsider probe and final challenger executed, floor reserved 3 of 20 calls, budget respected, no errors, and a complete ranking.
- `test_production_run_is_deterministic` — nondeterminism in the production path.

---

## 7. Validation Results

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `PYTHONPATH=src pytest tests/test_policy_selection.py -q` | 0 | 21 passed |
| 2 | `PYTHONPATH=src pytest tests/test_production_operating_point.py -q` | 0 | 31 passed |
| 3 | `PYTHONPATH=src pytest -q` | 0 | **781 passed** (750 pre-existing + 31 new), 10.7 s, no warnings surfaced |
| 4 | `ruff check src/consistency_ranker/policy_selection scripts/run_policy_selection_experiment.py scripts/run_production_uht.py tests/test_policy_selection.py tests/test_production_operating_point.py` | 0 | All checks passed |
| 5 | `mypy src/consistency_ranker/policy_selection --ignore-missing-imports` | 0 | Success, 17 files, **0 errors** (was 36) |
| 6 | `mypy scripts/run_production_uht.py scripts/run_policy_selection_experiment.py --ignore-missing-imports` | 0 | Success, 0 errors (was 4 in the experiment runner) |
| 7 | `PYTHONPATH=src python -c "import consistency_ranker.policy_selection …"` | 0 | prints `always_uht production_uht 0.15` |
| 8 | `bash -n` on the generated and the historical `REPRODUCE.sh` | 0 | both syntactically valid |
| 9 | `PYTHONPATH=src python scripts/run_production_uht.py --help` / `--budget 8 --n-items 6 --top-k 2` / `--mode experimental_gate` | 0 / 0 / 2 | help labels experimental options; run reports `production_uht` + `UHT`; experimental mode rejected |
| 10 | `PYTHONPATH=src python scripts/run_policy_selection_experiment.py --help` and `--mode production_uht` | 0 / 2 | labelled `RESEARCH BENCHMARK`; conflicting mode rejected with a pointer to the production runner |
| 11 | `PYTHONPATH=src python scripts/run_policy_selection_experiment.py --output-dir /tmp/ps_verify` (full benchmark, synthetic judges) | 0 | 31.6 s, Outcome **F**, best production mode `always_uht` |
| 12 | Same command again with `--overwrite-existing` | 0 | 30.9 s, regenerates in place (F-005 fix verified) |
| 13 | Diff of `/tmp/ps_verify` against `reports/policy_selection_20260726T030500Z` | 0 | **0** numeric differences across every `mode_summary` field; **0** mismatches across all 192 `gate_rows` policies and utilities; identical `calibration_test`; same outcome letter |

Before running #11 I inspected the runner: all judgments come from
`policy_benchmark.build_world` synthetic judges and `synthetic_roster` profiles;
there is no HTTP client, provider SDK, or API-key lookup on the path.

**Working tree after validation.** The benchmark re-runs were written to
`/tmp/ps_verify`, outside the repository. `reports/policy_selection_20260726T030500Z`
retains its original 23:00–23:01 timestamps on every artifact; the only new file
in it is the dated `IMPLEMENTATION_STATUS_20260726.md` (23:43). `git status`
shows no unexpected regeneration: the tracked diff is still only the three
pre-existing modified files (`pyproject.toml`, `src/consistency_ranker/__init__.py`,
`src/consistency_ranker/baseline_ranking.py`, 19 insertions total), and the new
work appears as untracked additions.

---

## 8. Type-Checking Status

- **Original:** 36 errors in `src/consistency_ranker/policy_selection` (5 files), matching the audit's count. Plus 4 in `scripts/run_policy_selection_experiment.py`.
- **Final:** 0 in both.
- **What was fixed:** the `reason` variable in `policy_gate` was inferred as `GateMode` because it was seeded from `mode` (18 errors); `max(d, key=d.get)` overload mismatches in `policy_gate` (×2), `policy_benchmark`, and the experiment runner; `pol_scores` narrowed to `PolicyName` keys where a `dict[str, float]` was required; beta-calibration locals shadowing a `str` loop variable in `policy_calibration` (5 errors); a cross-prior loop variable shadowing a `str` in `diagnostic_probes` (8 errors); `split_budget`'s int-only return annotation in `policy_mixture`; and in the runner, two shadowed `mode` loop variables, an unannotated dict, a `Collection` inference, and an unguarded optional `features_probe`.
- **How:** by correcting names and annotations. No `# type: ignore` was added, no strictness disabled, and no useful type replaced with `Any` except the `curves` aggregation dict in the experiment runner, which genuinely holds heterogeneous plot series.
- **Remaining, unrelated, pre-existing:** `mypy src/consistency_ranker --ignore-missing-imports` reports 42 errors in 20 other modules (`adaptive_acquisition`, `prior_robust/adaptive_prior`, `failure_mining`, `multi_provider_eval`, `repair_selector_mining`, `utils/llm_api_status`, `scripts/run_real_experiment.py`). None are in the Outcome F stack and none were introduced here; several would require behavioural decisions (e.g. widening `Literal` unions in `adaptive_prior`) rather than a small unambiguous edit.

---

## 9. Remaining Risks

Each item below is backed by an observation from this session.

1. **The stack is still uncommitted (F-004).** `git status` shows `policy_selection/`, `production_runner.py`, both CLIs and both test files as untracked. Committing was out of scope, so there is still no reviewable diff. A reviewer should run `git add -A src/consistency_ranker/policy_selection scripts/run_production_uht.py scripts/run_policy_selection_experiment.py tests/test_production_operating_point.py tests/test_policy_selection.py` on this branch before review, and decide separately whether the ~660 KB of generated report artifacts belong in Git.
2. **The safety floor costs 2–3 calls, which can hurt at small budgets.** Comparing `run_production_uht` against `run_named_policy(policy="UHT")` over 12 synthetic cells, mean top-k Jaccard was 0.225 versus 0.208 — but on one cell (16 items, budget 8, seed 1) the floor scored 0.2 against plain UHT's 0.5, because two of eight calls went to safeguards. The floor is not free on tight budgets. It has not been benchmarked at the scale that produced Outcome F, and I did not re-run the frozen benchmark against it, to avoid perturbing those numbers.
3. **`gate_features` reads an `evidence_fraction` key that `evidence_fraction_summary` never returns.** `gate_features.py:241` uses `summary.get("evidence_fraction") or 0.0`, but that function returns only counts, so `evidence_only_stability_proxy` is always 0.0 and `preliminary_g_prior` always 1.0 in every recorded feature vector. This weakens the experimental gates' feature set (consistent with Outcome F's finding that the predictors are weak) and does not affect production, which computes its own coverage from `topk_evidence_coverage`. I left it alone because changing it would alter the frozen benchmark inputs.
4. **Weak-evidence stops are blocked on essentially every synthetic query.** Measured top-k coverage after a UHT run was 0.0–0.08 across all scenarios tried, so the ban fires constantly. That is a real signal (UHT's judged pairs are frequently disjoint from the final top-k boundary) rather than a bug, but the safeguard is closer to "always acquire a little more boundary evidence" than to a selective check, and its threshold has not been tuned on real data.
5. **F-006 (oracle protocol) and F-007 (accuracy framing) are documented, not fixed.** The oracle gap magnitude in `FINAL_REPORT.md` still mixes live and offline utilities; only the direction of the oracle advantage is safe to cite.
6. **The production path has only been exercised on synthetic worlds.** `run_production_uht` takes the same `world` dict as the research harness; wiring it to a real provider roster and a real judge is untested.

---

## 10. Final Answers

1. **Does a default constructor execute UHT?** Yes. `PolicySelector()` is `always_uht` / `production_uht`, and `select_policy` with no selector returns UHT.
2. **Can the safety floor rewrite UHT to challenger in production mode?** No. The rewrite lives in `apply_experimental_escalation`, which production never calls; production filters requests through `production_safety_actions` and executes them as in-UHT actions.
3. **Are learned gates possible without explicit opt-in?** No. They require `ExecutionMode.EXPERIMENTAL_GATE` on both the selector and the call; defaults, `None`, unknown strings and environment variables all resolve to or raise before production.
4. **Does the outsider probe always execute when required?** Yes when a probeable insider/outsider pair and budget exist; the spy tests confirm the method is called exactly once and `outsider_probe_executed` plus the judged pair id are recorded. If no pair is judgeable it records `False` rather than pretending.
5. **Is weak-evidence stopping prohibited?** Yes, while budget remains and top-k coverage is strictly below 0.2; the blocked stop is spent acquiring the missing top-k comparisons.
6. **Does the final challenger check execute?** Yes, on both the blocked-stop and normal-stop paths, outside any early return, exactly once.
7. **Do diagnostic predictions remain non-routing?** Yes. They are returned in `diagnostic_recommendation`, and a confident CHALLENGER recommendation still executes UHT.
8. **Do malformed models/configurations fail closed?** Yes. Unknown modes raise, `None` resolves to production, corrupt model files cannot be attached to a production selector, and safeguard exceptions degrade to plain UHT with the error recorded.
9. **Are all tests passing?** Yes: 781 passed, 0 failed.
10. **Is mypy clean?** Clean for the Outcome F stack (0 of the original 36, plus the runner's 4). 42 unrelated pre-existing errors remain elsewhere in the repository.
11. **Is the working branch clean enough for review?** Partly. The behaviour is review-ready and isolated on `fix/outcome-f-production-operating-point`, but nothing is committed, so there is still no diff to review (risk 1).
12. **Is the repository production-ready for the stated interim operating point?** Yes for the operating point as specified — always-UHT with a non-routing safety floor, enforced and tested. Not yet for a *learned* gate, and the floor's budget cost and thresholds still need validation on real queries.
