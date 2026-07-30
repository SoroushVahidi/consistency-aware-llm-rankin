# Local Branch Audit (current)

**Audit date:** 2026-07-26 (evening polish pass)
**Branch:** `fix/outcome-f-production-operating-point`
**HEAD at audit:** `89b9406ea11a7d9cae434284e3e041fee51de4c8`
**Upstream comparison:** `origin/main` = `3e02b73666506f3eb894f5df2c531284ea31a60e` (0 behind, 6 ahead)
**Safety reference:** local branch `backup/pre-polish-outcome-f-20260726` (not pushed)
**Billed API calls:** none for this audit

> The pre-remediation audit that found `PolicySelector` defaulting to
> `selective_three_way` is archived at
> `docs/historical/AUDIT_LOCAL_BRANCH_20260726_pre_remediation.md`.
> That document is **historical**; do not treat it as current status.

---

## 1. Executive verdict

**Interim production operating point is enforced in code; learned routing is not production-approved.**

| Claim | Current status |
|---|---|
| `PolicySelector()` default | `mode=always_uht`, `execution_mode=production_uht` |
| `selective_three_way` in production | **Rejected** (`ValueError`) unless `ExecutionMode.EXPERIMENTAL_GATE` |
| Safety floor | Non-routing budget/actions inside UHT (`run_production_uht`) |
| Learned / selective / soft / staged gates | Experimental only |
| JDIQ manuscript null retrieval-repair conclusion | Unchanged |
| Full pytest suite (this machine, 2026-07-26) | **818 passed** (not 750) |
| Outcome F synthetic evidence | Canonical package `reports/policy_selection_20260726T030500Z/` |
| Multifactor real-query `production_uht` metrics | **Not validated** — keep local; see §4 |

---

## 2. Git relationship (verified)

| Item | Value |
|---|---|
| Merge base with `origin/main` | `3e02b73…` (= remote HEAD) |
| Local-only commits | 6 (linear; starting `3614333` … ending `89b9406`) |
| Staged at polish start | none |
| Tracked unstaged at polish start | `pyproject.toml` multifactor E501 ignores (rejected; E501 already clean) |
| Untracked | large report/supplementary trees; classified under `docs/ARTIFACT_POLICY.md` |

---

## 3. Finding ledger (from pre-remediation audit)

| ID | Pre-remediation issue | Resolving commit / note | Current status |
|---|---|---|---|
| F-001 | Default gate `selective_three_way` | `3614333` | **Resolved** — defaults to `always_uht` / `production_uht` |
| F-002 | Safety floor rewrote policy to HYBRID/CHALLENGER | `3614333` (`apply_experimental_escalation` experimental-only) | **Resolved** |
| F-003 | Stop ban / final challenger unreachable | `3614333` (`production_runner`) | **Resolved** |
| F-004 | Stack uncommitted / unreviewable | Commits `3614333`–`89b9406` on this branch | **Mostly resolved** — reviewable commit range exists; polish/PR still open |
| F-005 | `REPRODUCE.sh` overwrite refusal | `3614333` (`--overwrite-existing`) | **Resolved** |
| F-006 | Oracle utility protocol mixing | Deferred (would change frozen numbers) | **Open / deferred** |
| F-007 | Calibration accuracy framing | Documented in report `IMPLEMENTATION_STATUS_20260726.md` | **Documented** |
| F-008 | Missing production contract tests | `3614333` (`tests/test_production_operating_point.py`) | **Resolved** |
| F-009 | Held-out n=12 too small for learned thresholds | By design: production freezes no learned threshold | **Consistent** |
| F-012 | mypy debt in `policy_selection` | Remediation pass | **Resolved for that package** (other packages still have mypy debt) |

---

## 4. What this branch does *not* claim

- Learned gates are **not** production-ready.
- The untracked multifactor package
  `reports/real_query_multifactor_acquisition_20260726T044254Z/` has **broken
  `production_uht` quality metrics** (empty nDCG; jaccard≡1.0 from prior-as-truth)
  and must not be cited as validation of the safety floor.
- Primary real-query greedy repair replay shows **zero** positive repair gains
  (80 queries); do not claim oracle heterogeneity on that primary table.
- Test-count references of “750” are obsolete; use the current suite count.

---

## 5. Authoritative documents

| Document | Role |
|---|---|
| This file | Current branch audit summary |
| `REMEDIATION_REPORT.md` | How F-001–F-003 were fixed (update currency notes for F-004 / test counts) |
| `docs/historical/AUDIT_LOCAL_BRANCH_20260726_pre_remediation.md` | Frozen pre-remediation findings |
| `reports/policy_selection_20260726T030500Z/README.md` | Canonical Outcome F evidence package |
| `docs/ARTIFACT_POLICY.md` | What belongs in Git vs local-only |
