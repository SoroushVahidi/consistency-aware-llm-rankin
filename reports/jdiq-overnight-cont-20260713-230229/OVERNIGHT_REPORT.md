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
