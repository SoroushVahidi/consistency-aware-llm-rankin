# Release Candidate Smoke Test

**Date:** 2026-08-01  
**Branch:** `papers/sncs-2026-foundation`  
**Parent commit at test start:** `45e13192b2f9d9f5a018e76a7aa21bd6ce234cff`  
**Environment:** Linux, Python 3.12.3, repository `.venv`  
**Scope:** clean-ish local environment checks of documented entry points.  
**Not run:** full empirical study regeneration; provider API calls; Git tag/release.

## Summary

| Track | Result |
|---|---|
| Dependency / import resolution | PASS |
| CLI help | PASS |
| Fast unit/integration subset | PASS (81 passed) |
| Small deterministic synthetic example | PASS |
| Canonical table row-count checks | PASS |
| Figure generator from stored CSV | PASS (output restored; tree not dirtied) |
| Manuscript compile from source ZIP | PASS (39 pages) |
| Full study regeneration | NOT RUN (by design) |
| API pilot re-query | NOT RUN (by design) |

**Overall smoke verdict:** PASS for release-candidate documentation entry points.

## Commands run and outcomes

### Environment

```text
source .venv/bin/activate
python -V
# Python 3.12.3
python -c "import pyscipopt; print(pyscipopt.__version__)"
# pyscipopt 6.2.1
python -c "import consistency_ranker, numpy, pandas, scipy; print('imports OK')"
# imports OK
```

**Pass.** Solver extra already present in this environment.

### CLI help

```text
python scripts/run_synthetic.py --help
```

**Pass.** Help text printed.

### Repository readiness

```text
python scripts/check_repo_ready.py
```

**Pass with warnings:** Summary `58 OK, 5 warnings, 0 failures`.  
Notable warning: optional `ir-datasets` not installed.  
**Classification:** infrastructure/optional-dependency warning, not a documentation defect for the SNCS primary (non-IR-export) track.

### Fast tests

```text
pytest -q tests/test_graph_and_solver.py tests/test_baseline_ranking.py
# 81 passed in 0.24s
```

**Pass.**

### Small deterministic example

```text
python scripts/run_synthetic.py --n-items 10 --noise 0.2 --seed 42 \
  --output-dir /tmp/sncs_rc_synthetic_smoke --overwrite-existing
```

**Pass.** Wrote `/tmp/sncs_rc_synthetic_smoke/synthetic_results.json`.

### Canonical tables from existing results

```text
# table_primary_graph_structure.csv -> 12 rows
# table_primary_bootstrap_permutation.csv -> 60 rows
# structural_per_query.csv -> 1025 rows
```

**Pass.** Matches `REPRODUCIBILITY_QUICKSTART.md` expectations.

### Figure generation from stored exact-repair CSV

```text
python papers/SNCS_2026/figures/generate_f5_exact_vs_greedy_gap.py
# printed per-dataset greedy/exact means; wrote f5 PDF/PNG
```

**Pass functionally.** The script rewrote tracked figure files in the working
tree; those changes were **reverted** with `git checkout` so the submission
figures remain the frozen committed binaries.  
**Deviation / note for docs:** regenerating figures dirties `papers/SNCS_2026/figures/`;
reviewers should redirect output or discard diffs unless intentionally refreshing art.

### Manuscript compilation from source ZIP

```text
unzip papers/SNCS_2026/submission/SNCS_2026_latex_source.zip
# flatten tex/bib/cls/bst/pdf figures; set \graphicspath{{./}}
tectonic -X compile main.tex --outdir /tmp/sncs_zip_out
# pdfinfo: Pages 39
```

**Pass.** Only underfull box / duplicate destination warnings (TeX hygiene), no hard errors.  
Committed PDF page count: 39. ZIP was regenerated in this pass so `main.tex`
matches the Funding/Acknowledgments separation on HEAD.

## Deviations from documented instructions

1. Used the existing repository `.venv` rather than creating a brand-new venv
   from scratch (closest available clean project environment).
2. Did not run `pip install` from zero; dependencies were already resolvable.
3. Figure regeneration temporarily modified tracked PDFs; restored afterward.
4. Full `pytest -q` / cloud-validation solver tier not re-run end-to-end in
   this smoke pass (subset + readiness script used instead).

## Failure taxonomy (none blocking)

| Issue | Classification |
|---|---|
| `ir-datasets` optional warning | Infrastructure / optional extra — not required for SNCS primary track |
| TeX underfull box warnings on ZIP compile | Acceptable LaTeX warnings — not a reproducibility failure |
| No lockfile / exact pip freeze | Documentation limitation already acknowledged — not a hard failure |

## Conclusion

Documented fast, local, solver-present, and ZIP-compile entry points work in
this environment. Safe to treat the release candidate as smoke-tested for
submission packaging, contingent on author portal confirmations in
`PORTAL_DRY_RUN.md`.
