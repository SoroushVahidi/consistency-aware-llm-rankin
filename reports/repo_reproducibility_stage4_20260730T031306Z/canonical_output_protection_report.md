# Canonical Output Protection Report

## Problem this addresses

Both canonical analysis workflows (`scripts/run_ir_evidence_audit.py`,
`scripts/run_real_llm_clustered_reanalysis.py`) take `--output-dir` as a
required CLI argument with no prior guard against pointing it at an
already-populated directory. Before this stage, re-running either script
against its own committed canonical output directory (e.g.
`reports/ir_evidence_audit_20260729T182949Z/` or
`reports/real_llm_clustered_reanalysis_20260730T023745Z/`) would silently
overwrite every file in it with no warning, no diff, and no way to tell
after the fact that a "committed" result had actually been regenerated.

## What was added

`consistency_ranker.provenance.protect_canonical_output(path, *,
allow_overwrite=False)` (see `provenance_metadata_schema.md`'s sibling
module for the provenance side of this stage's work):

- Does nothing if `path` does not exist yet, or exists as an **empty**
  directory (a location the caller has reserved but not yet written into).
- Raises `CanonicalOutputExistsError` with an actionable message if `path`
  is an existing file, or a non-empty directory, **unless**
  `allow_overwrite=True` is passed.

Both scripts now call this at the top of their `run()` function, before
creating any output, and both expose it as a CLI flag:

```
scripts/run_ir_evidence_audit.py --output-dir DIR [--allow-overwrite]
scripts/run_real_llm_clustered_reanalysis.py --output-dir DIR [--allow-overwrite]
```

On refusal, both scripts print `ERROR: <message>` to stderr and exit with
status 1 (verified this stage — see below); they do not partially write
output before raising.

## Verification performed this stage

Ran both scripts three times each against a fresh scratch directory:

1. **Fresh directory** (does not exist yet): both scripts ran to completion
   and produced their full output set, including a `reproducibility_manifest.json`.
2. **Re-run against the now-populated directory, no flag**: both scripts
   exited with status 1 and the expected `ERROR: Refusing to write into
   non-empty canonical output directory '...'` message; **no output files
   were modified** (confirmed no output line but the refusal message
   printed before `output_dir.mkdir` / any CSV write in the IR-audit script,
   and before `output_dir.mkdir` in the reanalysis script).
3. **Re-run with `--allow-overwrite`**: both scripts completed successfully
   and regenerated their output, confirming the opt-in path still works.

This is a real, executed verification (commands were run against
`/tmp/.../scratchpad/prov_test_ir` and `.../prov_test_llm`, not asserted from
reading the code), not a claim inferred from source alone.

## Scope and limitations

- This guards the two canonical **analysis-generating** workflows only. It
  does not retroactively protect every script in `scripts/` (e.g.
  `run_synthetic.py`'s `--overwrite-existing` flag already existed
  independently, predating this stage, and was left as-is since it already
  has its own explicit opt-in semantics).
- It protects against **accidental silent overwrite via this repository's
  own tooling**. It is not a filesystem permission lock and does not stop a
  direct `rm -rf` or manual edit outside these two scripts.
- The not-yet-created `scripts/run_offline_validation_workflow.py` (task
  #41 of this stage) will call both scripts with fresh temporary output
  directories by default specifically so that routine reproduction checks
  never risk triggering this guard's refusal path in normal use — the guard
  exists for the case where a user manually points `--output-dir` at a
  committed `reports/...` path, not for the workflow's own internal
  reproduction runs.
