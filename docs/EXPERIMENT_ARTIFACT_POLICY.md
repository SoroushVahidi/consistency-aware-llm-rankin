# Experiment Artifact Policy

This policy decides what experiment outputs belong in Git, what stays local or
external, and how future experiment families should document their artifacts.
It complements `docs/ARTIFACT_POLICY.md` by focusing on timestamped experiment
outputs and raw provider caches.

## What Git Tracks

Track artifacts that are compact, interpretable, and needed to verify a
committed claim or rerun an analysis without hidden local state:

| Artifact | Default treatment |
|---|---|
| Source code and configurations | Track when they define an active or frozen protocol. |
| Seeds and model/provider metadata | Track in compact manifests or metadata JSON. |
| Prompts and schemas | Track frozen versions; never edit a frozen version in place. |
| Compact parsed judgments | Track when they are the lowest-level non-sensitive evidence needed for analysis. |
| Figures | Track only curated manuscript/evidence figures; regenerate scratch plots locally. |
| Summary tables | Track canonical or active exploratory tables that support interpretation. |
| `STATUS.md`, `README.md`, `FINAL_REPORT.md` | Track when they classify the run and explain evidence status. |
| Manifests and hashes | Track, using repo-relative paths and deterministic ordering. |
| Canonical evidence | Track the minimal complete bundle needed to verify the cited claim. |

## What Git Excludes

Exclude artifacts that are raw, sensitive, bulky, transient, or strictly more
granular than a tracked summary:

| Artifact | Default treatment |
|---|---|
| Raw API requests/responses | Do not track. Archive externally if scientifically valuable. |
| Provider caches | Track only sanitized parsed judgments when needed; ignore raw payloads. |
| Bulk JSONL outputs | Track only if they are compact lowest-level evidence; otherwise summarize and ignore. |
| Exploratory outputs | Track a status/report only after classification; ignore scratch internals. |
| Superseded outputs | Keep historical if already cited; otherwise leave local or archive externally. |
| Temporary/debug output | Ignore narrowly by exact directory or filename pattern. |
| Large files | Prefer external archival storage or Git LFS; do not add by accident. |

Never add broad ignore rules such as `reports/**`, `*.json`, or `*.jsonl`.
Use narrow rules tied to a named experiment directory.

## Decision Matrix

| Criterion | Track in Git | External archive | Ignore/local |
|---|---|---|---|
| Necessary for claim verification | Yes, if compact and sanitized | Yes, if raw or large | No |
| Regeneration cost | Track if costly or non-deterministic and sanitized | Archive if paid API calls are required | Ignore if deterministic and cheap |
| Determinism | Track seeds/configs and deterministic summaries | Archive exact raw evidence if not byte-reproducible | Ignore regenerated intermediates |
| Size | Prefer small files; document exceptions | Use for large evidence bundles | Use for bulky scratch state |
| Sensitivity/provider restrictions | Track only sanitized derivatives | Archive with restricted access | Ignore transient local copies |
| Long-term value | Track canonical/active compact evidence | Archive raw transcripts and full ledgers | Ignore debug logs |

## Current Real-LLM Pilot Decision

The 2026-07-29 real-LLM pilot outputs were inventoried in
`docs/artifact_inventories/untracked_outputs_20260731.csv`.

The decision is:

- Track compact reports, run configs, summaries, aggregate metrics, parsed
  judgments, provider usage/failure ledgers, and row-level evidence needed by
  the 2026-07-30 clustered reanalysis.
- Exclude raw request/response transcripts under `raw_calls/`.
- Exclude smoke/debug checkpoints and logs that are duplicated by tracked
  smoke reports or aggregate JSON.
- Preserve the local source files in place. A complete byte-for-byte snapshot
  was created outside the repository before ignore rules were added.
- Preserve provider model identity in
  `reports/multi_provider_repair_pilot_20260729T032348Z/PROVIDER_MODELS.json`
  so the reanalysis does not depend on raw transcripts.

The current tracked compact evidence is sufficient for the committed
cluster-aware reanalysis. Re-running the raw provider collection from scratch
would require paid/provider calls and is not byte-deterministic because provider
outputs may change over time even under frozen prompts and schemas.

### Raw Transcript Storage Classes

| Class | Examples | Git status | Use |
|---|---|---|---|
| Git-tracked compact evidence | Parsed judgment JSONL, provider usage/failure ledgers, `PROVIDER_MODELS.json`, run configs, summaries, clustered reanalysis tables. | Tracked. | Supports current repository claims without exposing raw payloads. |
| Locally retained ignored raw transcripts | `reports/*/raw_calls/` and `*_calls.jsonl` entries listed in `docs/artifact_inventories/untracked_outputs_20260731.csv`. | Ignored by narrow `.gitignore` rules. | Allows the original operator to audit exact provider exchanges locally. |
| Externally archived raw evidence | A tarball or object-store bundle created from the ignored raw transcript paths plus inventory/checksums. | Not in Git. | Durable restricted-access preservation if exact raw exchanges become necessary for review or public artifact release. |
| Regenerable debug/smoke caches | Smoke `cache/`, `checkpoint/`, and log directories classified as duplicate or temporary in the inventory. | Ignored by narrow `.gitignore` rules. | Local debugging only; regenerate from the tracked scripts/configs if needed. |

### External Archive Procedure

Before deleting any local raw transcript, first create and verify an external
archive. The archive must not be committed to Git and must not be printed in
logs or documentation beyond its filename, checksum, and storage handle.

1. Create a new archive version named
   `raw-provider-transcripts-YYYYMMDDTHHMMSSZ`.
2. Include only the ignored raw-transcript paths whose inventory category is
   `raw provider request/response cache`; keep smoke/debug duplicates separate.
3. Include a manifest with repo-relative paths, byte sizes, SHA-256 checksums,
   source experiment directory, provider/model metadata file, generating script,
   and the Git commit used for the inventory.
4. Verify every archived file against the manifest after packaging and again
   after upload or copy to external storage.
5. Store the archive in a restricted-access research artifact location selected
   by the project owner. No destination is currently configured in this
   repository.
6. Record the archive version, external storage handle, top-level archive
   SHA-256, manifest SHA-256, access restrictions, and deletion authorization in
   a tracked status note. Do not include raw request/response contents in that
   note.
7. Delete local raw transcripts only after the tracked status note records
   successful verification and explicit human authorization for deletion.

Selecting and populating a durable external archive destination is a
**public-release condition** for any release that promises exact raw-provider
transcript availability. It is not a merge blocker for code or documentation
integration because the current claims are supported by tracked compact
evidence and the ignored local raw files remain untouched.

## Adding a New Experiment Family

Before running:

1. Create or identify the entry-point script, config, prompt/schema version,
   seed policy, and output directory naming convention.
2. Decide whether the run is canonical, exploratory, superseded, or
   historical.
3. Set the output directory explicitly; do not rely on a machine-specific
   absolute path.
4. For provider-backed runs, document the exact call ceiling authorized by the
   user before any API call is made.

Before committing:

1. Inventory all outputs with path, size, type, SHA-256, category, and storage
   decision.
2. Track only compact, sanitized evidence needed for interpretation or
   reproducibility.
3. Add narrow `.gitignore` rules for raw payloads, debug logs, and bulky
   intermediates.
4. Add a `README.md` or `STATUS.md` in the experiment directory describing
   what is tracked, what is excluded, and how to regenerate summaries.
5. Run the portability check, secret scan, link/evidence validators, focused
   tests, and the full test suite before pushing.

## Historical Artifacts

Historical reports may contain original execution paths, timestamps, and
environment details. Do not rewrite them merely to make old provenance look
portable. Instead, keep them classified as historical and ensure active
documentation points readers to portable commands and current evidence.
