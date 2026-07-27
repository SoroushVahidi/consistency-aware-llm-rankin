# Implementation status note — added 2026-07-26

This note post-dates the experiment in this directory. The experiment artifacts
(`summary.json`, `gate_rows.json`, `rows.jsonl`, `decision.json`, models, plots,
`FINAL_REPORT.md`) are unmodified historical records of the run that produced
Outcome F. Nothing below changes them.

## Why this note exists

`FINAL_REPORT.md` states an **interim production default** of "always UHT with a
lightweight safety floor". At the time of the run that was a *recommendation*,
not enforced behaviour: `PolicySelector` defaulted to `selective_three_way`, and
the safeguard path could rewrite a UHT decision into HYBRID or CHALLENGER. A
subsequent audit (archived as
`docs/historical/AUDIT_LOCAL_BRANCH_20260726_pre_remediation.md`; current status
in root `AUDIT_LOCAL_BRANCH.md`) recorded this gap.

The operating point is now enforced in code. Read `FINAL_REPORT.md` as the
empirical record and this note as the implementation record.

## What was reproduced

Re-running `scripts/run_policy_selection_experiment.py` after the remediation
reproduced this directory's results **bit-for-bit**: all 192 `gate_rows`
policies and utilities, every numeric field of `mode_summary`, the calibration
metrics, and the Outcome F letter are identical. The remediation changed
defaults and added a production path; it did not change the benchmark.

Independently confirmed from the raw rows:

- The oracle query-specific selector really is better (corrected utility
  ≈ 0.171 versus ≈ −0.026 for always-UHT), so policy selection has value in
  principle.
- **No** learned, hard, calibrated, selective, soft, or staged gate beat
  always-UHT on the held-out burial-heavy regimes.

## What is enforced now

- Production executes **always UHT**. `PolicySelector()` resolves to gate mode
  `always_uht` in `ExecutionMode.PRODUCTION_UHT`, and a learned gate mode or an
  attached calibration model is rejected in that mode.
- Learned gates **remain experimental**. They require an explicit
  `ExecutionMode.EXPERIMENTAL_GATE`, which no default constructor, omitted CLI
  flag, environment variable, or missing configuration value can produce.
- The **safety floor is non-routing**. It reserves 15% of the budget for a
  mandatory outsider probe, a weak-evidence stop ban, and a final challenger
  check, all executed inside the UHT path. It cannot substitute HYBRID or
  CHALLENGER for UHT; that escalation now lives in
  `safe_fallback.apply_experimental_escalation` and is experimental-only.
- **Diagnostic recommendations are recorded separately** from the executed
  policy: `executed_policy`, `diagnostic_recommendation`, and
  `experimental_policy` are distinct fields.

Entry points: `scripts/run_production_uht.py` (production / diagnostic) and
`scripts/run_policy_selection_experiment.py` (research benchmark, experimental
gates only).

## Reproducing this directory

`REPRODUCE.sh` in this directory predates the fix and will fail on a second run
because the experiment refused to write into an existing directory. Use either
form instead:

```bash
export PYTHONPATH=src
# regenerate in place
python scripts/run_policy_selection_experiment.py \
  --output-dir reports/policy_selection_20260726T030500Z --overwrite-existing
# or write a fresh directory
python scripts/run_policy_selection_experiment.py --output-dir /tmp/ps_verify
```

Newly generated report directories ship a `REPRODUCE.sh` that handles both cases
automatically.
