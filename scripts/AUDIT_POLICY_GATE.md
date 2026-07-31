# AUDIT_POLICY_GATE.md

Audit of the pre-existing Outcome-D prior-quality gate
(`quality_gated` in `prior_robust/engine.py` + `prior_quality.py`),
conducted before implementing calibrated policy selection.

Classification legend: **sound** · **partially sound** · **uncalibrated** ·
**potentially leaky** · **missing** · **unsafe for production**.

---

## 1. How \(\widehat Q\) is calculated

**Location:** `src/consistency_ranker/prior_robust/prior_quality.py` →
`estimate_prior_quality`.

**Heuristic (default):**

* No judgments yet: \(q = 0.5 + 0.2\cdot\mathrm{sep} - 0.1\cdot\mathrm{entropy}\)
* With judgments:
  \(0.55\cdot\mathrm{agree} + 0.15\cdot(1-\mathrm{hc\_contra}) + 0.15\cdot\mathrm{sep} + 0.10\cdot(1-\mathrm{ent}) + 0.05\cdot\mathrm{cross}\)

**Logistic variant:** fixed coefficients on agree / hc / sep / ent — **not
fitted** on labeled data.

| Component | Classification |
|---|---|
| Functional form | **uncalibrated** (hand weights) |
| Range clipping to [0,1] | **sound** |
| No qrel fitting in estimator | **sound** |

---

## 2. Features used by \(\widehat Q\)

| Feature | Stage | Classification |
|---|---|---|
| Judgment–prior agreement rate | probe / online | **partially sound** (needs acquisitions) |
| High-conf contradiction rate | probe / online | **partially sound** |
| Prior score entropy | pre | **sound** |
| Top-k score separation | pre | **sound** |
| Cross-prior Kendall | pre (if alts) | **partially sound** (sparse alts) |
| Evidence fraction (via summary) | probe | **sound** (count only) |

**Missing vs this task’s feature list:** multi-prior top-k overlap, rank
variance, boundary-challenger count, orientation / prompt / provider
agreement, outsiders-defeating-insiders, evidence-only stability,
acquisition-gain trajectory, shared-bias score — **missing**.

---

## 3. Availability before acquisition

Geometry features (entropy, separation) are available **pre-acquisition**.
Agreement / contradiction require judgments — **partially sound** for a
gate that claims to decide before spending budget, but the Outcome-D path
does run a 3-call probe first (**sound** intent, **uncalibrated** design).

---

## 4. Features requiring exploratory judgments

Agreement, contradiction, weighted agreement, and any probe-derived signal.
Outcome-D forces ~3 pairs (boundary / distant / adjacent) before branching.
**partially sound** (fixed, non-optimized probe set).

---

## 5. Indirect use of qrels / synthetic truth

Estimator code paths inspected: **no qrel keys**. Oracle mode
`oracle_prior_quality` injects `true_prior_quality` only when
`score_mode == "oracle_prior_quality"` for diagnostics — **sound** if kept
out of production; **unsafe for production** if enabled online.

Experiment harness computes `true_prior_tau` for metrics only — **sound**.

---

## 6. Pass/fail threshold selection

Hard rules in `engine.py` (`quality_gated`):

* trust if `agr ≥ 0.65` and `hc ≤ 0.25`
* else distrust if `hc ≥ 0.35`
* else trust if `q_hat ≥ 0.55` and `hc < 0.3`
* if no signal: trust if `q_hat ≥ 0.45`

| Aspect | Classification |
|---|---|
| Thresholds | **uncalibrated** (hand-tuned) |
| Selected on same synthetic grid used to report Outcome D | **uncalibrated** / nested-split **missing** |
| Utility-based threshold selection | **missing** |

---

## 7. Global vs query-specific threshold

**Global** constants — **uncalibrated**. No query-adaptive τ, no subgroup
calibration — **missing**.

---

## 8. Same-simulation design risk

`reports/prior_robust_*/FINAL_REPORT.md` notes noisy Q̂ and Outcome-E
follow-up. Gate thresholds and policy comparison share the same adversarial
grid — **uncalibrated** (overfit risk). Nested train/val/test regimes were
**missing**.

---

## 9. Confidence intervals

None on \(\widehat Q\) or on gate decisions — **missing**.

---

## 10. Abstention

Binary trust / distrust only. No `UNCERTAIN`, no selective prediction —
**missing**.

---

## 11. Policy change after initial branch

After trust → plain UHT to budget exhaustion; after distrust → robust loop
with adaptive λ. No hysteresis-based **policy switch** back — **partially
sound** (λ adapts) but hard policy lock — **missing** for online switching.

---

## 12. Policy-selection error logging

`failure_trace` records branch and `q_hat`. No structured false-trust /
false-distrust labels, no expected gate regret — **partially sound**.

---

## 13. Asymmetric false-trust vs false-distrust cost

Not modeled. Prior report shows false distrust is costly under accurate
priors (~0.5 τ) and false trust is catastrophic under burial — but the gate
does not encode \(L_{\mathrm{FT}} \gg L_{\mathrm{FD}}\) — **missing** /
**unsafe for production** if treated as calibrated.

---

## 14. Outcome-D meta-policy overall

| Piece | Classification |
|---|---|
| Idea: gate UHT vs robust | **partially sound** |
| Probe-then-branch | **partially sound** |
| \(\widehat Q\) as probability | **uncalibrated** |
| Production readiness | **unsafe for production** without calibration, abstention, fallback floor |
| Label leakage in online path | **sound** (absent) |

---

## 15. Implications for this task

The calibrated policy-selection layer must:

1. Separate **pre / probe / online** features with schema versioning.
2. Fit interpretable models on **train regimes only**; pick thresholds on
   **validation utility**.
3. Support **selective abstention**, **soft mixtures**, **switching**, and
   **lightweight safe fallback**.
4. Optimize **expected utility** (ranking − cost − catastrophic risk), not
   balanced accuracy.
5. Treat conformal / risk-control numbers as **empirical under exchangeability**,
   not formal deployment certificates.

---

## 16. Implementation status (added 2026-07-26)

This section post-dates the audit above and the Outcome F experiment. It
records what is **enforced in executable code today**, not what was planned.

| Statement | Status |
|---|---|
| Oracle query-specific selection has a real advantage on the synthetic grid | Independently reproduced (corrected utility ≈ 0.171 vs ≈ −0.026 for always-UHT) |
| Some learned gate beat always-UHT on held-out burial-heavy regimes | **No** — every learned/hard/soft/selective/staged mode was worse |
| Learned gates are production-ready | **No** — they remain experimental and require `ExecutionMode.EXPERIMENTAL_GATE` |
| Production routing | Always UHT, enforced by `PolicySelector` defaults and `production_runner.run_production_uht` |
| Safety floor | Non-routing: reserves 15% of budget for a mandatory outsider probe, a weak-evidence stop ban, and a final challenger check. It cannot rewrite UHT into HYBRID/CHALLENGER |
| Diagnostic probe (`mixed_diagnostic`, budget 3) | Recorded in `diagnostic_recommendation`; never changes `executed_policy` |
| Outcome-D `quality_gated` branch in `prior_robust/engine.py` | Still present as a legacy research path; not reachable from the production entry point |

Production entry point: `scripts/run_production_uht.py`.
Research benchmark: `scripts/run_policy_selection_experiment.py` (experimental
gates only; cannot install a production default).
