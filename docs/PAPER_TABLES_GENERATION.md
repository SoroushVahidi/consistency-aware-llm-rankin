# Paper Tables Generation (New Analysis Family)

## Scientific questions answered

1. **Repair-effect summary:** where repair is harmful/neutral/gainful in
   committed Q1 significance tables.
2. **Baseline visibility:** how broad method baselines perform in available
   real-output summaries.
3. **Synthetic robustness:** multiseed stability and noise sensitivity from
   committed synthetic outputs.
4. **Failure context:** whether harmful cases align with cyclicity and
   structural-shift indicators.
5. **Artifact auditability:** which core evidence files exist and row counts.

---

## Entry point

- Script: `scripts/generate_paper_tables.py`
- Primary command:
  - `python scripts/generate_paper_tables.py --out-dir reports/paper_tables`

---

## Expected output location

- `reports/paper_tables/`
  - `table_01_repair_effects.csv`
  - `table_02_proxy_baseline_leaderboard.csv`
  - `table_03_synthetic_multiseed_stability.csv`
  - `table_04_synthetic_noise_sweep.csv`
  - `table_05_failure_context.csv`
  - `table_06_artifact_inventory.csv`
  - `README.md`

---

## Notes

- This script is aggregation-only: it does not run new expensive experiments.
- Missing source files produce empty tables rather than fabricated values.
- Canonical claim support should still prioritize `outputs/q1_journal_package/`
  and `outputs/pub_vote_cmp_v2/paper_package/`.

