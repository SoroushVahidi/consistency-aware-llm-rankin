# Archival Release Plan

Date: 2026-08-01
Repository: https://github.com/SoroushVahidi/consistency-aware-llm-rankin
Current repository visibility from `gh repo view`: **public**.

## Recommendation

The public GitHub repository already satisfies reviewer code access at
submission. Prefer a DOI-backed archival deposit **at acceptance** (or when the
author explicitly authorizes a submission-time archive). See
`RELEASE_CANDIDATE_PLAN.md` and `RELEASE_CANDIDATE_DECISION.md` for the active
release-candidate plan.

Do not create a public GitHub Release or DOI without explicit authorization.

Recommended release tag:

`sncs-2026-submission-v1`

Suggested release title:

`SN Computer Science 2026 submission package v1`

## Include

- `papers/SNCS_2026/manuscript/main.tex`
- `papers/SNCS_2026/manuscript/references.bib`
- `papers/SNCS_2026/manuscript/main.pdf`
- `papers/SNCS_2026/figures/`
- `papers/SNCS_2026/template/sn-jnl.cls`
- `papers/SNCS_2026/template/bst/sn-basic.bst`
- `papers/SNCS_2026/COLD_READ_REPORT.md`
- `papers/SNCS_2026/SUBMISSION_METADATA.md`
- `papers/SNCS_2026/FINAL_SUBMISSION_DECISION.md`
- `src/`
- `scripts/`
- `tests/`
- `configs/`
- `docs/CONTRIBUTIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/AGENT_GUIDE.md`
- `docs/EXPERIMENT_ARTIFACT_POLICY.md`
- `docs/claim_evidence_registry.yaml`
- Canonical compact evidence needed to verify the manuscript:
  `reports/full_calibrated_core/`,
  `reports/exact_open_source_ilp_repair_investigation/`,
  `reports/normalization_protocol_audit_20260714/`,
  `reports/candidate_pool_conditional_audit_20260714/`,
  `reports/final_revision_task1_pool_cutoff_20260715/`,
  `reports/final_revision_task4_exact_baseline_fairness_20260715/`,
  `reports/real_llm_clustered_reanalysis_20260730T023745Z/`, and
  `reports/multi_provider_repair_pilot_20260729T032348Z/` with raw calls
  excluded.
- `README.md`, `requirements.txt`, `pyproject.toml`, `Makefile`, and `LICENSE`.

## Exclude

- Raw provider request/response payloads under any `raw_calls/` directory.
- Any provider cache that contains prompt/completion payloads rather than
  compact parsed judgments.
- `.env`, credential files, API keys, service-account JSON, SSH keys, and
  machine-specific paths.
- `gurobi.lic` and any Gurobi WLS credential material.
- `data/raw/` and `data/processed/`.
- `.venv/`, `.pytest_cache/`, `.ruff_cache/`, build artifacts, and editor state.
- Large historical or superseded archives not needed for the manuscript.
- Internal-validation-only Gurobi reports as manuscript evidence. If the full
  repository snapshot includes them, mark them internal and do not cite them in
  the paper.

## Raw Provider Calls

Raw provider calls must remain excluded from public release and ordinary
submission archives. They may contain prompt/completion content and operational
details, and they are not byte-reproducible by re-querying providers. If exact
raw transcripts are needed for audit, place them in a restricted external
archive with access controls, separate from the public DOI artifact.

## Licensing

The repository currently carries an MIT License. Include `LICENSE` in any code
archive. Benchmark datasets remain under their original licenses and should not
be redistributed unless their licenses explicitly permit it; the archive should
include query lists, processed intermediates, and scripts as stated in the
manuscript, not third-party raw corpora.

## Proposed Citation Text

Vahidi, S. (2026). Code and artifacts for "Structural Consistency Is Not
Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for
Multi-Ranker Retrieval" (SN Computer Science submission). GitHub repository:
https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Archived release:
DOI to be added after Zenodo or equivalent archival deposit.

## DOI-Backed Archive Steps

1. Confirm repository visibility and artifact-access plan with the author.
2. Run the final QA checks listed in `FINAL_SUBMISSION_DECISION.md`.
3. Create an annotated Git tag `sncs-2026-submission-v1` on the exact
   submission commit.
4. Push the tag.
5. Create a GitHub release from that tag only after authorization.
6. Connect the repository/release to Zenodo or an equivalent archive.
7. Verify the DOI landing page, file list, license, and metadata.
8. Update the manuscript and `SUBMISSION_METADATA.md` with the DOI only after it
   exists.
