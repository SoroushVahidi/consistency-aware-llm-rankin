# Release Candidate Plan (`sncs-2026-submission-v1`)

**Date:** 2026-08-01  
**Branch:** `papers/sncs-2026-foundation`  
**Action status:** prepared only — **no Git tag, GitHub Release, Zenodo DOI, or journal submission is created by this document.**

## Proposed tag

| Field | Value |
|---|---|
| Tag name | `sncs-2026-submission-v1` |
| Tag type | Annotated Git tag (when authorized) |
| Commit to tag | `f42ad47f66fe73c14f4cac52b23876b264c10739` (see `SUBMISSION_FREEZE.md`) |
| Proposed release title | SN Computer Science 2026 submission package v1 |
| Create tag before vs after portal submit | Prefer **immediately before** portal submit, after author confirms upload files; do not push a public GitHub Release until authorized |

## Proposed release notes (copy-ready draft)

```text
SN Computer Science 2026 submission package v1

Manuscript: "Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic
Audit of Preference-Graph Repair for Multi-Ranker Retrieval"

This release candidate freezes the exact manuscript PDF, LaTeX source archive,
and repository commit corresponding to the SN Computer Science submission
package on branch papers/sncs-2026-foundation.

Principal result (unchanged): preference-graph repair is structurally real
but does not yield a Holm-surviving retrieval-quality improvement under the
reported protocols.

Artifacts:
- papers/SNCS_2026/manuscript/main.pdf
- papers/SNCS_2026/submission/SNCS_2026_latex_source.zip
- Canonical evidence under reports/full_calibrated_core/ and
  reports/exact_open_source_ilp_repair_investigation/

Exclusions:
- API keys and credentials
- Raw provider request/response payloads
- Internal reviewer/audit working notes not needed for reproduction
- Gurobi-only internal validation reports as manuscript evidence

License: MIT (repository code). Benchmark datasets remain under their
original licenses and are not redistributed here.

Reproduction: see papers/SNCS_2026/REPRODUCIBILITY_QUICKSTART.md
Citation: see below; DOI intentionally omitted until an authorized archive deposit.
```

## Commit to tag

Tag only the commit recorded in `SUBMISSION_FREEZE.md` after:

1. smoke-test PASS (`RELEASE_CANDIDATE_SMOKE_TEST.md`);
2. upload manifest reviewed (`UPLOAD_MANIFEST.md`);
3. author confirmation of portal-specific fields (`PORTAL_DRY_RUN.md`).

Do **not** tag an intermediate WIP commit.

## Included artifacts

### Always include in a future GitHub/Zenodo code archive

- `src/`, `scripts/`, `tests/`, `configs/`
- `README.md`, `CONTRIBUTING.md`, `LICENSE`, `pyproject.toml`, `requirements.txt`, `Makefile`
- `docs/CONTRIBUTIONS.md`, `docs/PROJECT_STATUS.md`, `docs/AGENT_GUIDE.md`, `docs/EXPERIMENT_ARTIFACT_POLICY.md`, `docs/claim_evidence_registry.yaml`, `docs/REPRODUCTION_CANONICAL.md`
- Canonical evidence directories listed in `SUBMISSION_FREEZE.md`
- `papers/SNCS_2026/manuscript/{main.tex,main.pdf,references.bib}`
- `papers/SNCS_2026/figures/*.pdf` (+ generators)
- `papers/SNCS_2026/template/sn-jnl.cls`, `template/bst/sn-basic.bst`
- `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip`
- `papers/SNCS_2026/{SUBMISSION_FREEZE,REPRODUCIBILITY_QUICKSTART,SUBMISSION_METADATA,COVER_LETTER}.md`

### Journal portal upload set (separate from Git tag)

See `UPLOAD_MANIFEST.md`. Portal uploads are a subset: PDF, source ZIP, cover letter / metadata text, reviewer suggestions.

## Excluded artifacts

Explicitly exclude from any public tag/release/archive:

- API keys, `.env`, credentials, service-account JSON, SSH keys, `gurobi.lic`, WLS tokens
- Personal email exports and private correspondence
- Raw provider transcripts / `raw_calls/` payloads containing prompts or completions
- Internal reviewer notes and rejected-manuscript correspondence under `papers/_archive/` that are not needed for SNCS reproduction
- Private legal or personal files
- Unnecessary build artifacts: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, editor state
- Large raw corpora under `data/raw/` / `data/processed/` (reproduce via documented download scripts; do not redistribute third-party corpora unless license-cleared)
- Treating Gurobi cross-validation/scaling report directories as manuscript evidence

## Licensing status

| Item | Status |
|---|---|
| Repository code | MIT (`LICENSE`) |
| Springer Nature `sn-jnl` template files | Vendored for author submission use; redistributed in the LaTeX source ZIP as required for compilation — see `LICENSE_AND_DISTRIBUTION_AUDIT.md` |
| Benchmark datasets | Original upstream licenses; cite, do not blanket-redistribute |
| Model outputs / provider payloads | Compact parsed judgments may be present; raw transcripts excluded |
| SCIP / PySCIPOpt | Open-source solver path used for manuscript exact repair; Gurobi optional and non-canonical |

Full audit: `LICENSE_AND_DISTRIBUTION_AUDIT.md`.

## Citation instructions

Until a DOI exists:

> Vahidi, S. (2026). Code and artifacts for “Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval” (SN Computer Science submission package). GitHub: https://github.com/SoroushVahidi/consistency-aware-llm-rankin (commit `f42ad47f66fe73c14f4cac52b23876b264c10739`; proposed tag `sncs-2026-submission-v1`).

After an authorized Zenodo (or equivalent) deposit, append the DOI and update this file and `SUBMISSION_METADATA.md`.

## Reproducibility instructions

1. Fast verification and local-only paths: `papers/SNCS_2026/REPRODUCIBILITY_QUICKSTART.md`
2. Full classical pipeline map: `docs/REPRODUCTION_CANONICAL.md`
3. Smoke-test record: `RELEASE_CANDIDATE_SMOKE_TEST.md`

There is **no** single command that regenerates the entire empirical study; do not claim one-command full reproduction.

## Known limitations

- Exact SCIP repair is part of the methodological control; greedy repair is the primary structural procedure in the classical multi-ranker study.
- The six-query real-LLM pilot is directional only (`n=6` clusters), not a primary retrieval claim.
- GitHub Actions CI is not authoritative due to account billing limits; use `scripts/run_cloud_validation.py`.
- Dependency pins are install constraints (`pyproject.toml` / `requirements.txt`), not a full lockfile; report manifests record environment detail where present.

## Provider-data limitations

- Re-querying paid LLM APIs will **not** byte-reproduce historical judgments.
- Raw provider request/response payloads are **not** publicly available and must not be described as such in portal text.
- Compact clustered reanalysis artifacts are the public pilot evidence surface.
- Any future API reproduction requires explicit, scoped authorization and credentials that are never committed.
