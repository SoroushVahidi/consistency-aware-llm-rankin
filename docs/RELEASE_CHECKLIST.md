# Release Checklist

Three distinct bars, not one. Confusing them is the most common way a
"ready" repository turns out not to be. See `docs/RELEASE_READINESS.md` for
the detailed CI/local validation contract this checklist summarizes, and
`docs/PROJECT_STATUS.md` for current status against every item below.

## Required before merging an ordinary change

- [ ] Clean worktree (`git status --short` empty before and after).
- [ ] Focused tests pass for the changed code.
- [ ] `python scripts/run_cloud_validation.py --tier core` passes (mirrors
      `ci.yml`'s `tests` job — GitHub Actions itself is not currently
      authoritative, see "External/non-code conditions" below).
- [ ] Relevant documentation updated (`docs/PROJECT_STATUS.md` if
      completion state changed; `docs/CONTRIBUTIONS.md` if a claim changed;
      `docs/EXPERIMENTS.md` if an experiment family changed).
- [ ] `docs/claim_evidence_registry.yaml` updated and re-validated
      (`python scripts/validate_claim_evidence_registry.py`) if a canonical
      claim changed.
- [ ] Artifact-policy compliance (`docs/EXPERIMENT_ARTIFACT_POLICY.md`) —
      no raw transcripts, no bulky regenerable intermediates staged.
- [ ] `python scripts/run_secret_scan.py` passes.
- [ ] `python scripts/validate_repo_clarity.py` passes.

This is the bar enforced by `.github/pull_request_template.md`'s checklist.

## Required before a public release

Everything above, plus:

- [ ] `python scripts/run_cloud_validation.py --tier solver` passes (the
      full zero-skip contract, including the Gurobi smoke test if a license
      is available on the validating machine).
- [ ] Package builds and installs cleanly from a wheel in a separate fresh
      venv (`--tier core`/`--tier solver` already include this step).
- [ ] Fresh-checkout verification from a genuinely clean clone, not just
      the working directory (`docs/PROJECT_STATUS.md` "Fresh-checkout
      reproducibility" documents the last time this was done and found/fixed
      a real issue — repeat it, don't just trust the note).
- [ ] Real-data (`real_data` pytest tier) status explicitly documented —
      either "passes on prepared datasets" (with the run recorded) or an
      explicit statement that it was not run this cycle and why.
- [ ] Raw-provider-transcript external archive decision resolved (issue
      #46) — or explicitly deferred with a stated reason, not silently
      skipped.
- [ ] License review: `LICENSE` (MIT) is present and unmodified; confirm no
      newly-added dependency changes the effective license obligations.
- [ ] Manuscript/reference status confirmed current — does
      `papers/JDIQ_2026/manuscript/main.tex` match what a public release
      would imply is "the result"? Is the manuscript still under
      double-blind review (in which case identity-linked material,
      including this repository's own GitHub identity if the account name
      is not anonymized, is a real deanonymization risk — see
      `papers/JDIQ_2026/manuscript/integrity_audit/`)?
- [ ] `python scripts/run_secret_scan.py` passes on the full tracked tree
      (not just the diff).
- [ ] `python scripts/check_active_portability.py` passes (no
      machine-specific paths in active code/docs).
- [ ] Release notes drafted, covering what changed since the last tagged
      state (there is currently no prior tag — see "Current release/version
      state" below).
- [ ] Package version (`pyproject.toml`) and any Git tag agree.

## External / non-code conditions

These cannot be satisfied by a commit:

- **GitHub Actions billing restoration** (issue #45) — recommended before
  public release so hosted CI is available going forward, but **not
  strictly blocking**: per existing repository policy
  (`docs/PROJECT_STATUS.md`, `docs/EXPERIMENTS.md` "Cloud Validation"),
  `scripts/run_cloud_validation.py` is the accepted substitute for the
  code-correctness gate while Actions is unavailable. A release made while
  Actions is still blocked is acceptable **provided** both cloud-validation
  tiers have passed and been independently re-verified from a fresh clone
  (see `docs/PROJECT_STATUS.md`'s validation history for the standard this
  should meet).
- **Durable external transcript archive**, if the release's claims depend
  on being able to produce exact raw provider transcripts on request
  (issue #46) — otherwise a stated limitation, not a blocker.
- **Repository visibility.** This repository is currently **private**. No
  release conditions in this document change that; making the repository
  public is a separate decision from tagging a release, and should account
  for the double-blind-review anonymity considerations noted above before
  either happens.

## Current release/version state (as of `2a5d2b4`, 2026-07-31)

- Package version: `0.1.0` (`pyproject.toml`) — pre-1.0, no stable API
  guarantee implied or intended.
- Git tags: none.
- GitHub releases: none.
- This is correct for the repository's actual state: an active research
  repository with a submitted-but-not-yet-accepted manuscript, several
  concluded negative-result research threads, and one paused engineering
  thread. **No release should be created until the "Required before a
  public release" section above is satisfied and a human decides the
  manuscript/anonymity considerations are resolved** — this document does
  not itself authorize creating one.
