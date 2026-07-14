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
