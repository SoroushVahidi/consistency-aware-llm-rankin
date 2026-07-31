# JDIQ Overnight Continuation Report

**Finished:** 2026-07-14T03:04:15.359353+00:00
**HEAD at report time:** `f1e0abb4bb325d7d46867940b620d49e8dae847c`

## Why this continuation

The first overnight session finished in minutes and left three high-value gaps:
1. Methods still claimed retention sensitivity was "not yet performed" while Limitations said otherwise.
2. CombMNZ exploratory log was empty (wrong qrels paths).
3. Anonymous artifact still contained `/home/soroush/` identity leak.

## Priorities executed

1. **Methods/Limitations consistency** for retention-target sensitivity.
2. **Hardcoded home-path leak removed** from `src/.../processor.py`.
3. **CombMNZ exploratory recomputed** — decision: `n/a`.
4. **Anonymous artifact rebuilt** + identity scan.
5. **Validation / compile**.

## Validation

```json
{
  "pages": 28,
  "fail": [],
  "cite_count": 24,
  "leak_fail": false,
  "methods_claim_ok": true
}
```

## Identity leak scan (artifact)

```
NO IDENTITY LEAKS FOUND
```

## CombMNZ (exploratory; not added as table)

```json
{}
```

## Remaining human/submission steps

1. Upload scrubbed zip to anonymous.4open.science (or equivalent).
2. Insert verified anonymous URL into Data Availability only after URL exists.
3. Do not include author GitHub URL in the anonymous PDF.

## CombMNZ addendum (hard-fail rerun)

**Decision:** DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous definition; expanding baselines would add volume without strengthening the repair thesis.

- scidocs: CombSUM=0.1866, CombMNZ=0.1884, Δ=+0.0018 (n=120)
- fiqa: CombSUM=0.0492, CombMNZ=0.0462, Δ=-0.0031 (n=120)
- hotpotqa: CombSUM=0.3320, CombMNZ=0.3320, Δ=+0.0000 (n=52)
- bright: CombSUM=0.1606, CombMNZ=0.1606, Δ=+0.0000 (n=50)

Numbers exploratory only; no baseline table added.

## Numeric audit
# Numeric Consistency Audit

**Mismatch count:** 0

- PASS: seeds_in_tex — bootstrap seed 13 / perm seed 17 / B=10000 present in TeX
- PASS: seeds_in_pdf_proxy — seed values reachable from compiled sources
- PASS: hotpotqa_exclusion_count — 18/70 exclusion stated
- PASS: hotpotqa_n52 — HotpotQA n=52 present
- PASS: holm_narrative_present — Holm zero-survivor narrative present
- PASS: scidocs_ms1_cycle_literals — 99.2 and 10.8 present
- PASS: delta_scidocs_ms1_copeland_hybrid — expected~0.009, got=0.008526038099271938
- PASS: delta_hotpotqa_ms1_copeland_hybrid — expected~0.012, got=0.01226673280326149
- PASS: delta_fiqa_ms1_copeland_hybrid — expected~-0.005, got=-0.004569149185585735
- PASS: retention_exec_holm0 — executive conclusion mentions Holm survivors 0
- PASS: no_identity_SoroushVahidi — absent from main.tex
- PASS: no_identity_/home/soroush/ — absent from main.tex
- PASS: no_identity_sv96@ — absent from main.tex
- PASS: combmnz_do_not_add — DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous definition; expanding baselines would add vo
- PASS: combmnz_max_abs_delta — max_abs=0.0031

## Deep table reconciliation
# Deep Numeric Reconciliation

Elapsed: 0.0s
Tabular blocks: 10
Numeric literals in tabulars: 151
Checked CSV highlight rows: 9
Mismatches: 0
Unpublished nonzero bootstrap means (info): 1

- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': 0.008526038099271938, 'tex_display': 0.009, 'ok': True, 'p': 0.011998800119988001, 'ci': [0.0018086563430457683, 0.017274600486808924]}
- PASS: {'dataset': 'fiqa', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': -0.004569149185585735, 'tex_display': -0.005, 'ok': True, 'p': 0.30086991300869914, 'ci': [-0.013271197026379595, 0.0017783080447936904]}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': 0.01226673280326149, 'tex_display': 0.012, 'ok': True, 'p': 0.25317468253174685, 'ci': [0.0, 0.030813557387646136]}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'pair': 'copeland_graph', 'csv_mean': 0.01550607117753817, 'tex_display': 0.016, 'ok': True, 'p': 0.3143685631436856, 'ci': [-0.01013825814585691, 0.044450754997660796]}
- PASS: {'dataset': 'bright', 'regime': 'ms1', 'pair': 'copeland_graph', 'csv_mean': -0.014041497577935986, 'tex_display': -0.014, 'ok': True, 'p': 0.26687331266873315, 'ci': [-0.040018839398353656, 0.006119613848628893]}
- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'col': 'cyclic_query_pct', 'csv': 99.16666666666667, 'tex': 99.2, 'ok': True}
- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'col': 'cyclic_query_pct_after_mutual_deletion', 'csv': 10.833333333333334, 'tex': 10.8, 'ok': True}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'col': 'cyclic_query_pct', 'csv': 63.46153846153846, 'tex': 63.5, 'ok': True}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'col': 'cyclic_query_pct_after_mutual_deletion', 'csv': 1.9230769230769231, 'tex': 1.9, 'ok': True}

## Deep table reconciliation
# Deep Numeric Reconciliation

Elapsed: 0.0s
Tabular blocks: 10
Numeric literals in tabulars: 151
Checked CSV highlight rows: 9
Mismatches: 0
Unpublished nonzero bootstrap means (info): 1

- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': 0.008526038099271938, 'tex_display': 0.009, 'ok': True, 'p': 0.011998800119988001, 'ci': [0.0018086563430457683, 0.017274600486808924]}
- PASS: {'dataset': 'fiqa', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': -0.004569149185585735, 'tex_display': -0.005, 'ok': True, 'p': 0.30086991300869914, 'ci': [-0.013271197026379595, 0.0017783080447936904]}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'pair': 'copeland_hybrid', 'csv_mean': 0.01226673280326149, 'tex_display': 0.012, 'ok': True, 'p': 0.25317468253174685, 'ci': [0.0, 0.030813557387646136]}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'pair': 'copeland_graph', 'csv_mean': 0.01550607117753817, 'tex_display': 0.016, 'ok': True, 'p': 0.3143685631436856, 'ci': [-0.01013825814585691, 0.044450754997660796]}
- PASS: {'dataset': 'bright', 'regime': 'ms1', 'pair': 'copeland_graph', 'csv_mean': -0.014041497577935986, 'tex_display': -0.014, 'ok': True, 'p': 0.26687331266873315, 'ci': [-0.040018839398353656, 0.006119613848628893]}
- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'col': 'cyclic_query_pct', 'csv': 99.16666666666667, 'tex': 99.2, 'ok': True}
- PASS: {'dataset': 'scidocs', 'regime': 'ms1', 'col': 'cyclic_query_pct_after_mutual_deletion', 'csv': 10.833333333333334, 'tex': 10.8, 'ok': True}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'col': 'cyclic_query_pct', 'csv': 63.46153846153846, 'tex': 63.5, 'ok': True}
- PASS: {'dataset': 'hotpotqa', 'regime': 'ms1', 'col': 'cyclic_query_pct_after_mutual_deletion', 'csv': 1.9230769230769231, 'tex': 1.9, 'ok': True}
