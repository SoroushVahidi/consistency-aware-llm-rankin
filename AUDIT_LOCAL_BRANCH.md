# Local Branch Audit

**Audit date:** 2026-07-26 (local)  
**Auditor:** independent local verification (no billed API calls)  
**Scope:** working tree on `main` at `3e02b73`, with emphasis on Outcome F / policy-selection work  
**Constraint compliance:** no application source, tests, experiment outputs, or configuration were modified; only this file was created.

---

## 1. Executive Verdict

**NOT PRODUCTION-READY**

The **empirical Outcome F conclusion is supported** by independently recomputed numbers from `gate_rows.json`: oracle query-specific selection has a real corrected-utility advantage; no learned/hard/soft/selective/staged gate beat always-UHT on the held-out burial-heavy synthetic test cells; calibrated gates systematically over-route to challenger/hybrid.

However, the **interim production operating point is not enforced in executable code**:

- `PolicySelector.mode` defaults to `selective_three_way`, not `always_uht`.
- The described safety floor (mandatory outsider probe, weak-evidence stop ban, final challenger check) is **not wired as a production UHT+floor path**; safeguard evaluation can rewrite UHT → HYBRID/CHALLENGER, and stop/final-challenger checks are never invoked in the gated runner’s single call site.
- There is **no production entry point** that locks always-UHT + floor and disables learned gating.
- The entire policy-selection / prior-robust / adaptive-acquisition stack is **uncommitted local work**, not a reviewable commit range vs `origin/main`.

**Headline metrics:** independently reproduced from raw `gate_rows.json` (exact match to `summary.json` / FINAL_REPORT tables for mean utilities).  
**Tests:** `tests/test_policy_selection.py` 21/21 passed; full repo `pytest` 750/750 passed.  
**Production default verified:** **No** — documentation claims always-UHT+floor; code defaults and runner behavior contradict that.

---

## 2. Branch and Comparison Scope

| Item | Value |
|---|---|
| Repository root | `/home/soroush/consistency-aware-llm-rankin` |
| Current branch | `main` |
| Current commit | `3e02b73666506f3eb894f5df2c531284ea31a60e` |
| Upstream | `origin/main` (tracking; status clean vs remote at audit start for commits) |
| Merge base with `origin/main` | `3e02b73666506f3eb894f5df2c531284ea31a60e` (**same as HEAD**) |
| Base selection reason | Prefer merge-base with `origin/main`; it equals HEAD, so **all Outcome F work is uncommitted local change**, not commits ahead of main. |

### Working-tree status (verified)

- **Staged:** none
- **Unstaged modified:**
  - `pyproject.toml` (ruff per-file E501 ignores for policy_selection)
  - `src/consistency_ranker/__init__.py` (exports `dag_linear_extensions`, `dag_ambiguity`, `soft_score_ranking`)
  - `src/consistency_ranker/baseline_ranking.py` (docstring note on topological ranking)
- **Untracked:** large set including JDIQ supplementary packages, many `reports/*` directories, and the full research stacks:
  - `src/consistency_ranker/policy_selection/`
  - `src/consistency_ranker/prior_robust/`
  - `src/consistency_ranker/adaptive_acquisition/`
  - `src/consistency_ranker/reliability_repair/`
  - `src/consistency_ranker/multi_provider_eval/`
  - related scripts/tests/reports

### Implication

There is **no commit-level diff** for Outcome F against `origin/main`. The “branch” under audit is the **dirty working tree**. Merge readiness cannot be assessed as a PR of commits; it must be assessed as “can this uncommitted stack be safely adopted as production policy routing?” — answer: **not yet**.

---

## 3. Reconstructed System Design

### Ranking / inference problem

The repository builds **consistency-aware rankings** from noisy pairwise LLM (or synthetic) judgments: construct a preference graph, repair cycles, extract a linear order / top-k. Adaptive acquisition chooses which pairs to judge under a budget to improve top-k quality.

### UHT (operational meaning)

**UHT** = acquisition scoring mode `uncertainty_x_topk_impact` (uncertainty × top-k impact), typically via `plain_uht` / `make_policy("uncertainty_x_topk_impact")` in `prior_robust` / `adaptive_acquisition`.

Mapped in `policy_runner.policy_to_engine_kwargs` (`src/consistency_ranker/policy_selection/policy_runner.py:44-48`):

- `UHT` → `plain_baseline=True`, `score_mode="uncertainty_x_topk_impact"`.

### Challenger / robust policies

- **CHALLENGER:** `score_mode="challenger_resolution"` + challenger exploration (`policy_runner.py:64-77`).
- **ROBUST_COMBINED:** `score_mode="robust_combined"` combining evidence-stability, prior-dependence reduction, challenger terms (`robust_acquisition.py`).
- **HYBRID (named):** mapped to guarded/`robust_combined` adaptive prior path (`policy_runner.py:107-122`) — **not** a literal per-action score mixture inside the engine.

### Query-specific policy selection (intended)

1. Extract **pre** features (prior geometry, multi-prior agreement).
2. Optional **diagnostic probe** (`mixed_diagnostic`, budget 3).
3. Extract **probe** features (agreement, contradictions, outsider wins, …).
4. `select_policy` chooses among UHT / challenger / hybrid / etc. under a `GateMode`.
5. Optionally evaluate safeguards / switching; run `run_robust_acquisition`.

### \(\widehat Q\)

`estimate_prior_quality` in `prior_robust/prior_quality.py:137-201`: hand-weighted combination of judgment–prior agreement, high-conf contradiction, score separation/entropy, optional cross-prior Kendall. **Not** probability-calibrated; no CIs; no qrels in the estimator itself. Outcome D used a hard `quality_gated` branch on agreement/`q_hat` thresholds in `prior_robust/engine.py`.

### Outcome D → Outcome F

- **Outcome D (prior_robust report):** gate UHT vs robust using \(\widehat Q\) / probes — conceptually attractive, but \(\widehat Q\) noisy.
- **Outcome F (policy_selection report):** after nested synthetic evaluation of many gates, **no deployable gate beat always-UHT on corrected utility**, while an **oracle** policy selector still wins → selection is valuable in principle; current predictors/gates are not decision-safe → need real calibration; interim always-UHT (+ claimed safety floor).

### Gate types (actual code behavior)

| Mode | Code behavior (`policy_gate.py`) |
|---|---|
| hard / calibrated_hard | Binary trust if `g_q >= threshold` else CHALLENGER |
| selective_three_way | Abstain if max policy prob < `tau_policy`; else argmax; may pick HYBRID / STOP_OR_FALLBACK |
| soft_mixture / budget_split | Returns policy=`HYBRID` + mixture metadata (`g_eff`, floor) |
| staged | `staged_plan` → UHT / CHALLENGER / ROBUST / HYBRID |
| switching | `policy_switching.evaluate_switch` with hysteresis; runner largely **post-hoc / HYBRID substitute**, not true mid-loop policy swap |
| fallback | `safe_fallback.evaluate_safeguards` returns action **requests**; `apply_fallback_constraints` may **change policy name** |
| risk-control | Empirical set filter; `is_formal_guarantee=False` |

### Safety floor vs learned gate

- **Documented floor:** keep mostly UHT; always reserve light exploration (0.15), mandatory outsider probe, ban weak-evidence stop, final challenger.
- **Code floor:** `clipped_credibility` / `split_budget` mixture weight floors (`policy_mixture.py:18-53`); plus safeguard **requests**. These are **not** the same as a locked production UHT path.

### Production-safe vs experimental

| Path | Status |
|---|---|
| Always-UHT via `plain_uht` / `run_named_policy(policy="UHT")` | Research-safe synthetic path; closest to interim recommendation |
| `PolicySelector` default / learned modes | **Experimental only** |
| Calibration models in report dir | Research artifacts |
| Outcome F “production default” text | **Documentation only** — not enforced |

---

## 4. Changed-File Inventory

Because merge-base = HEAD, inventory is **working-tree changes**, not commits.

### Modified (tracked)

| File | Class |
|---|---|
| `pyproject.toml` | configuration |
| `src/consistency_ranker/__init__.py` | production code (export list) |
| `src/consistency_ranker/baseline_ranking.py` | production code (docs) |

### Core Outcome F / policy-selection (untracked)

| Path | Class |
|---|---|
| `src/consistency_ranker/policy_selection/*.py` (14 modules) | production/research library code |
| `scripts/run_policy_selection_experiment.py` | experiment code |
| `scripts/AUDIT_POLICY_GATE.md` | documentation |
| `tests/test_policy_selection.py` | test |
| `reports/policy_selection_20260726T030500Z/*` | generated report + models + plots |
| `reports/policy_selection_20260726T025426Z/*` | generated report (earlier/quick run) |

### Supporting stacks also untracked (in-scope for “branch”, not only Outcome F summary)

| Path | Class |
|---|---|
| `src/consistency_ranker/adaptive_acquisition/` | production/research code |
| `src/consistency_ranker/prior_robust/` | production/research code |
| `src/consistency_ranker/reliability_repair/` | production/research code |
| `src/consistency_ranker/multi_provider_eval/` | production/research code |
| `src/consistency_ranker/dag_*.py`, `soft_score_ranking.py` | production/research code |
| matching `scripts/run_*.py`, `tests/test_*.py`, `reports/*` | experiment / test / generated |

### Other large untracked (adjacent local work, not Outcome F core)

- `papers/JDIQ_2026/submission/.../anonymous_supplementary/` (submission package)
- Multiple `reports/final_revision_*`, `linear_extension_*`, `reliability_aware_*`, etc.

**~122** untracked paths match the policy/prior/adaptive/report pattern above (count via `git ls-files --others`).

---

## 5. Claim Reproduction Table

**Utility used in tables:** per-row `utility` from gated runs (`compute_utility` with experiment weights \(\lambda_c=0.008,\lambda_r=0.6\)).  
**Corrected utility (decision criterion):**  
\(\mathrm{corr} = \overline{U} - 0.25\cdot\mathrm{cat\_rate} - 0.1\cdot\overline{\mathrm{gate\_regret}}\)  
independently recomputed from `reports/policy_selection_20260726T030500Z/gate_rows.json` (192 rows = 16 modes × 12 test queries).

| Claim | Source of raw evidence | Independent result | Reported result | Status | Notes |
|---|---|---|---|---|---|
| Oracle corrected utility ≈ 0.17 | `gate_rows.json` mode=`oracle` | **0.17082** | ~0.17 / FINAL_REPORT oracle U=0.229 with corr implied | **independently reproduced exactly** | corr from U/cat/regret means |
| Always-UHT corrected ≈ −0.03 | `gate_rows.json` mode=`always_uht` | **−0.02567** | ~−0.03 | **independently reproduced exactly** | |
| Always-UHT mean U ≈ 0.089 | same | **0.08917** | 0.089 | **exactly** | matches `summary.json` |
| Oracle mean U ≈ 0.229 | same | **0.2285** | 0.229 | **exactly / rounding** | |
| Learned gates did not beat always-UHT (corr) | same | all learned deltas **negative** (selective −0.086 … hard −0.242) | same narrative | **reproduced exactly** | |
| Gates over-route to challenger/robust | `gate_rows` policies | calibrated_hard: **12/12 CHALLENGER**; soft/selective: **12/12 HYBRID** | stated | **reproduced exactly** | UHT usage 0.0 on those modes |
| Efficiency loss exceeds benefit | U and calls | hard/soft lower U than always_uht at similar ~15–16 calls | stated | **reproduced within tolerance** | not a formal efficiency ratio test |
| \(\widehat Q\) too noisy as hard switch | prior_quality heuristic + hard_qhat/calibrated_hard results | hard gates = always challenger on test; class balance UHT-optimal **8.3%** test | Outcome D/F narrative | **approximately reproduced** | “noisy” is interpretive; hard switch empirically harmful here |
| Interim OP: always-UHT + floor | code defaults + runner | **not enforced** | FINAL_REPORT / decision.json | **contradicted by executable defaults** | see §6 |
| 21 policy tests, no billed calls | pytest + ripgrep | **21 passed**; no HTTP/API in package tests | claimed | **verified** | docstring + interactive synthetic judges |
| Nested train/val/test priors disjoint | `rows.jsonl` | train∩test=∅, val∩test=∅ | claimed | **verified** | test priors include `outsider_buried` |
| Probe budget 3 mixed_diagnostic | runner defaults + experiment | default `probe_budget=3`, design `mixed_diagnostic`; always_uht run with probe_budget **0** in experiment | mixed | **approximately reproduced** | probes not applied to always_uht baseline cells |
| Safety floor 0.15 | `PolicySelector.safety_floor`, `MixtureConfig` | default **0.15** exists | 0.15 | **value present; semantics not production-UHT** | |
| Calibration test accuracy 0.917 | `summary.json` + class balance | accuracy matches majority-class baseline (~91.7% if always predict non-UHT) | reported as cal metric | **exactly as stored; interpretation misleading** | all probs in bins ≤0.25 |

**Oracle caveat:** live oracle gated `utility` often ≠ offline `oracle_utility` from the population table (same best policy name, different execution path/seeds). Mean oracle `gate_regret` is **0.368** despite `policy_match=1.0`. Status: **oracle advantage is real in direction**, but absolute “oracle gap” mixes two protocols → **approximately reproduced / implementation details differ**.

---

## 6. Production-Gate Verification

### Search results: what can select a policy?

| Mechanism | Location | Production lock? |
|---|---|---|
| `PolicySelector.mode` default | `policy_gate.py:113` = **`selective_three_way`** | **No — wrong default vs Outcome F** |
| `select_policy(...)` | `policy_gate.py:149+` | Caller-controlled |
| `run_gated_acquisition` | `policy_runner.py:208+` | Research harness; `enable_fallback=True` by default |
| `run_named_policy("UHT")` | `policy_runner.py:150+` | Explicit UHT only if caller chooses |
| `quality_gated` in prior_robust engine | `prior_robust/engine.py` | Legacy Outcome D meta-policy — still present |
| CLI `run_policy_selection_experiment.py` | compares many modes; does not install a production default | Experiment only |
| Env vars / config files enabling learned gates | **None found** for production services | N/A — also no production service entrypoint found |
| Loading calibration JSON | `CalibratedModel.load` | Schema check only; not auto-wired into a prod CLI |

### Checklist vs stated interim OP

| Requirement | Enforced in code? | Evidence |
|---|---|---|
| 1. Always UHT primary | **No** (default selective) | `policy_gate.py:113` |
| 2. mixed_diagnostic budget 3 | Default in runner **yes**; experiment disables probes for always_uht | `policy_runner.py:215-216`; experiment `probe_budget=0` for always_uht |
| 3. Safety floor 0.15 | Constant exists; not a UHT production path | `policy_gate.py:121`, `policy_mixture.py:13` |
| 4. Mandatory outsider probe | Request emitted at step 0 if `outsider_probes_done==0`; **rewrites UHT→HYBRID/CHALLENGER** via `apply_fallback_constraints` | `safe_fallback.py:85-89,142-144`; verified in live Python |
| 5. Weak-evidence stop ban | Only if `intending_stop=True`; runner calls safeguards with **`intending_stop=False` once** | `policy_runner.py:290-298`; `safe_fallback.py:108-111` |
| 6. Final challenger check | Same — requires `intending_stop=True`; **never triggered in runner** | `safe_fallback.py:119-122` |
| 7. No automatic learned-gate activation | **False for library default**; true only if callers avoid `PolicySelector()` | default mode selective |
| 8. Safe if models missing | `select_policy` can run without models (heuristic `g_q`) | partially safe; still may pick non-UHT |
| 9. Conflicting CLI | Experiment CLI has no prod policy lock | `--output-dir`, `--quick` only |
| 10. Diagnostics vs routing distinction | Documented in reports; **not encoded as API/permission boundary** | |

### Critical semantic finding

**“Always UHT plus safety floor” is not accurate in code.**

If `run_gated_acquisition(..., enable_fallback=True)` (the function default) runs with policy UHT, `evaluate_safeguards` at step 0 **always** includes `mandatory_outsider_probe` (because `outsider_probes_done` starts at 0), and `apply_fallback_constraints` then maps:

- high `q_hat` → **HYBRID**
- low `q_hat` → **CHALLENGER**

Verified independently:

```text
step0 high-q actions: ['mandatory_outsider_probe']
UHT overridden to: HYBRID
step0 low-q override: CHALLENGER
```

Thus the “floor” can become a **hidden challenger/hybrid routing gate**, contrary to the interim production story. The experiment avoided this for `always_uht` by setting `enable_fallback=False` for that mode only (`run_policy_selection_experiment.py` gate loop).

---

## 7. Findings

### Critical

#### F-001 — Interim production default not encoded
- **Severity:** Critical  
- **Title:** Library default is selective gating, not always-UHT  
- **Location:** `src/consistency_ranker/policy_selection/policy_gate.py:113`  
- **Evidence:** `PolicySelector.mode: GateMode = "selective_three_way"`; import smoke prints `selective_three_way`.  
- **Impact:** Any caller using defaults enables a learned/selective path Outcome F forbids for production.  
- **Fix:** Default `mode="always_uht"`; require explicit opt-in for experimental modes; add a `ProductionPolicyConfig` frozen object.  
- **Blocks merge:** Yes (for any claim of production-ready routing).  
- **Changes Outcome F conclusion:** No (empirical F still holds); **invalidates “interim OP implemented”**.

#### F-002 — Safety floor rewrites UHT into hybrid/challenger
- **Severity:** Critical  
- **Title:** Mandatory outsider safeguard overrides UHT policy name  
- **Location:** `safe_fallback.py:85-89`, `142-144`; `policy_runner.py:289-303`  
- **Evidence:** Independent Python reproduction (see §6).  
- **Impact:** “UHT + floor” can silently become HYBRID/CHALLENGER acquisition.  
- **Fix:** Execute outsider probe as an **action inside UHT**, not a policy rename; never map UHT→CHALLENGER for floor.  
- **Blocks merge:** Yes.  
- **Changes Outcome F conclusion:** No.

#### F-003 — Weak-evidence stop ban and final challenger never run in gated harness
- **Severity:** Critical  
- **Title:** Stop/final-challenger safeguards are dead in runner  
- **Location:** `policy_runner.py:290-298` (`intending_stop=False` only); `safe_fallback.py:108-122`  
- **Evidence:** Single safeguard call site; those branches require `intending_stop=True`.  
- **Impact:** Documented production safeguards are aspirational.  
- **Fix:** Integrate safeguard checks into the acquisition loop / stop decision.  
- **Blocks merge:** Yes (for production OP claims).  
- **Changes Outcome F conclusion:** No.

#### F-004 — Outcome F stack is uncommitted on main
- **Severity:** Critical (process / release)  
- **Title:** No commit range vs origin/main; dirty tree only  
- **Location:** git state (§2)  
- **Evidence:** merge-base == HEAD; all policy_selection files `??`.  
- **Impact:** Cannot merge “the branch”; review/repro of a PR is impossible as stated.  
- **Fix:** Commit on a feature branch with scoped files; exclude bulky reports or Git-LFS policy.  
- **Blocks merge:** Yes.  
- **Changes Outcome F conclusion:** No.

### High

#### F-005 — REPRODUCE.sh cannot regenerate into the same directory
- **Severity:** High  
- **Title:** `mkdir(..., exist_ok=False)` + hard-coded output path  
- **Location:** `scripts/run_policy_selection_experiment.py:179`; `reports/.../REPRODUCE.sh`  
- **Evidence:** source inspection; REPRODUCE points at existing `policy_selection_20260726T030500Z`.  
- **Impact:** Fresh clone following REPRODUCE fails after first success; encourages silent reliance on checked-in artifacts.  
- **Fix:** accept `--overwrite-existing` or write a new timestamp dir from REPRODUCE.  
- **Blocks merge:** Yes for reproducibility claims.  
- **Changes Outcome F conclusion:** No.

#### F-006 — Oracle gap mixes offline table with live gated utilities
- **Severity:** High  
- **Title:** Oracle regret is not vs a consistent oracle execution  
- **Location:** experiment gate loop writing `utility` vs `oracle_utility` from `rows.jsonl` population  
- **Evidence:** e.g. live util 0.072 vs offline oracle_u 0.888 for same best policy name; mean oracle gate_regret 0.368 with policy_match 1.0.  
- **Impact:** Inflates/distorts “gap to oracle”; still supports directional oracle advantage.  
- **Fix:** evaluate oracle by reusing the same offline utilities, or match seeds/protocol exactly.  
- **Blocks merge:** Should fix before citing precise gap magnitudes.  
- **Changes Outcome F conclusion:** Softens magnitude, not direction.

#### F-007 — Calibration “accuracy” is majority-class artifact
- **Severity:** High  
- **Title:** Test P(UHT optimal) ≈ 8.3%; model predicts only low probs  
- **Location:** `summary.json` `calibration_test`; `rows.jsonl` labels  
- **Evidence:** reliability bins only populated for conf∈[0,0.25]; accuracy≈0.917 ≈ 1−0.083.  
- **Impact:** Overstates gate discrimination; hard gates always distrust.  
- **Fix:** report balanced metrics / utility; never lead with accuracy.  
- **Blocks merge:** For any claim that calibration is “good.”  
- **Changes Outcome F conclusion:** Strengthens F (predictors weak).

#### F-008 — No tests protect the production operating point
- **Severity:** High  
- **Title:** Tests never assert always-UHT default or floor-without-reroute  
- **Location:** `tests/test_policy_selection.py` (21 tests)  
- **Evidence:** default-mode smoke uses explicit modes; fallback test only checks action membership; no test that `PolicySelector().mode == "always_uht"`.  
- **Impact:** Regressions can enable selective gating unnoticed.  
- **Fix:** add production-config contract tests (see §10).  
- **Blocks merge:** Yes if packaging as prod.  
- **Changes Outcome F conclusion:** No.

#### F-009 — Held-out n=12 is too small for strong production claims
- **Severity:** High (methodology)  
- **Title:** Test set is 3 priors × 2 judges × 2 seeds = 12 queries  
- **Location:** `rows.jsonl` / `population_summary.json`  
- **Evidence:** counted.  
- **Impact:** Supports “current gates unsafe / need more data” (Outcome F), **not** “policy selection impossible.”  
- **Fix:** larger synthetic grid + real multi-provider pilot (already suggested in report).  
- **Blocks merge:** No for research; yes for freezing prod thresholds.  
- **Changes Outcome F conclusion:** Consistent with F.

### Medium

#### F-010 — Soft “HYBRID” is not a true score mixture in the engine
- **Severity:** Medium  
- **Location:** `policy_runner.py:107-122` maps HYBRID → robust_combined/guarded  
- **Impact:** Soft-mixture results are mislabeled relative to the math in docs.  
- **Fix:** implement true mixture scoring or rename policy.  
- **Blocks merge:** No.  
- **Changes Outcome F conclusion:** No (still didn’t beat UHT).

#### F-011 — Online switching is largely simulated
- **Severity:** Medium  
- **Location:** `policy_runner.py:305-348`  
- **Evidence:** comments admit post-hoc / HYBRID substitute.  
- **Impact:** Switching conclusions under-supported.  
- **Blocks merge:** No for Outcome F.  

#### F-012 — mypy reports 36 errors in policy_selection
- **Severity:** Medium  
- **Location:** mypy run on package (diagnostic_probes, policy_gate, calibration, …)  
- **Impact:** type debt; some bugs may hide.  
- **Blocks merge:** Prefer fix; not empirical blocker.

#### F-013 — Ruff E501 ignored for new package via pyproject
- **Severity:** Medium  
- **Location:** `pyproject.toml` per-file-ignores  
- **Impact:** style gate weakened for new code.  
- **Blocks merge:** No.

#### F-014 — Corrected-utility weights (0.25/0.1) are post-hoc decision glue
- **Severity:** Medium  
- **Location:** experiment decision block (not `compute_utility`)  
- **Impact:** ranking of modes depends on these arbitrary weights; sensitivity not formally reported as CI.  
- **Note:** always_uht still wins on raw mean U among non-oracle modes, so central comparison is robust to this.  
- **Blocks merge:** No for F direction.

### Low

#### F-015 — Large generated reports/models in working tree
- **Severity:** Low  
- **Impact:** repo hygiene / Git size if committed blindly.  

#### F-016 — Earlier quick report `...T025426Z` still present with Outcome A
- **Severity:** Low  
- **Impact:** doc confusion if both cited.  

#### F-017 — `test_no_billed_calls_and_topological_validity` does not instrument network
- **Severity:** Low  
- **Evidence:** test name overclaims; relies on synthetic judge path.  

---

## 8. Methodology Assessment

### Leakage
- **Prior regimes** disjoint across train/val/test — verified.  
- **Judge regimes** also split (train clean/position-bias; test nontransitive/correlated).  
- **No qrel keys** in feature schema — tested and ripgrep-clean.  
- **Oracle labels** used only as supervision targets / oracle mode, not as online features — sound.  
- **Thresholds** selected on validation utilities — sound intent.  
- **Risk:** same synthetic family still; leave-one-regime-out only within train priors.

### Evaluation units
- Aggregation is **per (prior_regime, judge_regime, seed)** query cell, then mean over 12 test cells per mode.  
- Not provider/prompt nested uncertainty.  
- Correlated judgments within a query are **not** treated as independent calibration samples for the gate (gate is query-level) — good.  
- Offline policy tournament rebuilds worlds per policy — good isolation.

### Calibration
- Target: `uht_optimal` = best_policy==UHT from offline utilities.  
- Severe **class imbalance** (~9% train, ~8% test).  
- Reported accuracy/ECE overstate usefulness; probabilities never enter high-confidence bins.  
- Fits Outcome F: predictors do not identify UHT-optimal queries well enough to gate.

### Utility / regret
- Sign: higher utility better; catastrophic adds \(\lambda_r\).  
- `catastrophic := topk_jaccard <= 0` is harsh/binary.  
- Corrected utility used for Outcome letter is **extra** penalty beyond `compute_utility`.  
- Oracle construction offline ≠ live — see F-006.

### Multiple comparisons
- 16 gate modes + threshold grids + probe budgets + model kinds — many looks. Outcome F correctly refuses to crown a learned winner; still, selective reporting risk exists for probe curves (val n small).

### Sample size / what the data support
| Statement | Supported? |
|---|---|
| Current learned gates unsafe vs always-UHT on this grid | **Yes** |
| Policy selection impossible | **No** (oracle advantage) |
| Need more real-query calibration | **Yes** (Outcome F) |
| Freeze production learned gate | **No** |

### Distribution shift
- Test includes burial + diverse priors + harder judges — appropriate stress.  
- n_items shift rows exist in summary but tiny.  
- Exchangeability for risk-control correctly disclaimed.

---

## 9. Test and Tool Results

| Command | Exit | Result |
|---|---|---|
| `PYTHONPATH=src pytest tests/test_policy_selection.py -q` | 0 | **21 passed** (~0.28s) |
| `PYTHONPATH=src pytest tests/test_policy_selection.py tests/test_prior_robust.py tests/test_adaptive_acquisition.py -q` | 0 | **65 passed** (~0.81s) |
| `PYTHONPATH=src pytest -q` | 0 | **750 passed** (~9.78s) |
| `ruff check src/consistency_ranker/policy_selection scripts/run_policy_selection_experiment.py tests/test_policy_selection.py` | 0 | All checks passed |
| `mypy src/consistency_ranker/policy_selection --ignore-missing-imports` | 0 with **36 type errors** printed | Not clean |
| `bash -n reports/policy_selection_20260726T030500Z/REPRODUCE.sh` | 0 | Syntax OK |
| `PYTHONPATH=src python -c "…PolicySelector().mode"` | 0 | prints `selective_three_way` |
| `PYTHONPATH=src python scripts/run_policy_selection_experiment.py --help` | 0 | `--output-dir`, `--quick` |
| Independent metric recompute from `gate_rows.json` | 0 | Matches summary utilities exactly |
| Safety-floor override reproduction | 0 | UHT→HYBRID/CHALLENGER |
| ripgrep billed/API markers in policy_selection tests/package | 0 | only docstring mentions |
| Full REPRODUCE.sh end-to-end regen | **Not run** | Would fail `exist_ok=False` on existing dir; avoided modifying artifacts |
| Working tree after tests | unchanged beyond pre-existing dirty state | No unexpected writes observed |

**External/billed calls:** none attempted by the above commands (synthetic judges / local files only).

---

## 10. Test-Coverage Gaps

Covered at least superficially: feature stages, schema guard, utility/asymmetric loss, calibration fit smoke, selective abstention smoke, mixture/split, switching hysteresis smoke, fallback trigger membership, probes budget, regret smoke, OOD flag, tiny benchmark/splits, replay empty cache, risk-control non-guarantee, gate mode smoke, gated dry-run.

**Missing / superficial (propose, do not implement):**

1. **Production contract:** `assert PolicySelector().mode == "always_uht"` (once fixed) and that experimental modes require `allow_experimental=True`.  
2. **Floor without reroute:** with UHT + fallback, outsider probe executes but final `run_policy` remains UHT (or UHT_EXPLORE), never CHALLENGER solely due to step-0 mandatory flag.  
3. **Stop ban / final challenger:** simulate intending_stop with weak evidence; assert stop blocked and challenger action scheduled.  
4. **Learned gate disabled:** loading `model_logistic.json` must not change production router.  
5. **Threshold equality / ties:** `g_q == qhat_threshold` boundary.  
6. **Empty / single-candidate / malformed FeatureBundle.**  
7. **Leakage regression:** features must not contain keys derived from `true_ranking` even if passed in metadata.  
8. **Deterministic seed:** two gated runs same seed → identical decision+utility.  
9. **Grouped split integrity:** assert no shared (prior,judge) across splits.  
10. **Network guard:** monkeypatch `socket`/`httpx` to fail if touched during tests.

---

## 11. Reproducibility Assessment

| Level | Status |
|---|---|
| Fully reproducible from tracked commits alone | **No** — code untracked; merge-base has none of it |
| Reproducible with current local working tree + artifacts | **Partial** — metrics recompute from `gate_rows.json`; tests pass |
| End-to-end regen via REPRODUCE.sh into same dir | **No** — `exist_ok=False` |
| Regen into new dir with same code | **Likely** (synthetic, no network) — not re-executed here to avoid new artifacts |
| Needs external data/credentials | **No** for synthetic Outcome F |
| “No billed calls” enforced | **By construction** of synthetic path; **not** a hard runtime firewall |

Seeds: experiment uses fixed seed tuples; interactive judges are seed-hashed — generally deterministic, but oracle live vs offline mismatch shows residual protocol sensitivity.

---

## 12. Documentation and Report Consistency

| Pair | Consistency |
|---|---|
| FINAL_REPORT vs `gate_rows`/`summary` utilities | **Consistent** (verified) |
| FINAL_REPORT interim OP vs `PolicySelector` defaults | **Contradicts** |
| FINAL_REPORT safety floor vs runner/safeguard wiring | **Contradicts** |
| AUDIT_POLICY_GATE.md vs prior_quality source | **Consistent** (uncalibrated Q̂) |
| `...T025426Z` Outcome A vs `...T030500Z` Outcome F | **Different grids/decisions** — both present locally |
| Soft mixture math docs vs HYBRID engine mapping | **Overstated** |
| Risk-control “not a certificate” | **Consistent** across code/report |
| decision.json Outcome F + rationale | Matches post-hoc decision; empirical base solid |

---

## 13. Recommended Pre-Merge Actions

### P0 — merge blockers
1. Put work on a **feature branch with commits**; do not pretend dirty `main` is mergeable.  
2. Encode **production config**: default always-UHT; experimental gates opt-in only.  
3. Fix safeguard semantics so floor **cannot** rename UHT→CHALLENGER/HYBRID; implement probes/stop/final-challenger inside the acquisition loop.  
4. Add **contract tests** for production OP.  
5. Fix REPRODUCE to write a **new** output directory (or overwrite flag).  
6. Align docs with code (or code with docs) before any “production ready” language.

### P1 — before production use
1. Resolve oracle offline/live utility protocol (F-006).  
2. Report calibration with class-balanced / utility metrics; stop leading with accuracy.  
3. Rename or implement true soft mixture.  
4. Clear mypy errors in policy_selection.  
5. Decide Git policy for `reports/` binaries/models.

### P2 — follow-ups
1. Larger synthetic nested grid + real 30–40 query multi-provider calibration pilot (as FINAL_REPORT Q15).  
2. True online switching experiments.  
3. Sensitivity sweeps for corrected-utility weights.  
4. Remove/archive superseded `...T025426Z` report to reduce confusion.

---

## 14. Final Answers

1. **Is the oracle advantage real in the available data?**  
   **Yes.** Independently, oracle corrected utility ≈ **0.171** vs always-UHT ≈ **−0.026** (exact from `gate_rows.json`). Directionally robust despite live/offline utility mismatch.

2. **Did any learned gate beat always-UHT on the stated held-out regimes?**  
   **No.** All calibrated/hard/soft/selective/staged/contextual/cost-sensitive modes had lower mean U and lower corrected utility than always-UHT.

3. **Is \(\widehat Q\) decision-safe as a hard switch?**  
   **No** on this evidence. Hard/calibrated gates routed **100%** to CHALLENGER on the 12 test cells and underperformed always-UHT.

4. **Is always-UHT genuinely the current default in executable code?**  
   **No.** `PolicySelector.mode` defaults to `selective_three_way`.

5. **Is the safety floor implemented exactly as described?**  
   **No.** Constants exist (0.15), but mandatory outsider logic can **reroute policy**, and weak-evidence stop / final challenger are **not exercised** by the gated runner.

6. **Can ordinary configuration accidentally enable learned gating?**  
   **Yes** — constructing `PolicySelector()` or calling `select_policy` without args enables selective mode. Experiment CLI itself is multi-mode research. No separate prod binary locks UHT.

7. **Are the reported numbers independently reproducible?**  
   **Mean utilities / catastrophic rates / corrected utilities: yes, exactly from `gate_rows.json`.** End-to-end regeneration of the report dir via REPRODUCE.sh into the same path: **no**. Full regen into a new dir: **not re-run in this audit** (to avoid writing artifacts).

8. **Are the tests sufficient to protect the production operating point?**  
   **No.** They validate library pieces and forbid qrel leakage at unit level, but do not lock always-UHT+floor semantics.

9. **Can the branch be merged safely?**  
   **Not as a production policy-routing release.** Empirically, Outcome F’s caution is right; code/docs/defaults are not aligned for a safe merge claiming that interim OP.

10. **Single most important next experiment?**  
    **A small real multi-provider calibration pilot** (≈30–40 queries × 2 providers × 2 prompts × orientation reverse on top-12; fixed 3-call mixed diagnostic probe; endpoints: catastrophic false-trust, buried-outsider recovery, utility vs always-UHT/always-challenger) — **after** wiring a true always-UHT+non-rerouting floor path so the pilot measures the intended production policy.

---

## Appendix A — Severity counts

| Severity | Count |
|---|---|
| Critical | 4 (F-001–F-004) |
| High | 5 (F-005–F-009) |
| Medium | 5 (F-010–F-014) |
| Low | 3 (F-015–F-017) |

## Appendix B — Distinction preserved

| Concept | Audit stance |
|---|---|
| Oracle policy heterogeneity | **Real** on this synthetic grid |
| Failure of current predictors/gates | **Real** |
| Failure of current calibration for decision-making | **Real** (imbalance + always-distrust) |
| Interim production decision (always-UHT + floor) | **Empirically reasonable**, **not implemented as claimed** |

---

*End of audit.*
