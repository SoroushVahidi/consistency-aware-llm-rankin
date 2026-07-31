# Provenance Metadata Schema

Implemented in `src/consistency_ranker/provenance.py` (`collect_provenance()`),
tested in `tests/test_provenance.py` (13 tests), wired into the two canonical
analysis workflows this repository currently has:
`scripts/run_ir_evidence_audit.py` and
`scripts/run_real_llm_clustered_reanalysis.py`. Both now write a
`reproducibility_manifest.json` using this one shared schema instead of each
maintaining its own ad-hoc, partial manifest (the real-LLM re-analysis script
previously wrote a manifest with a subset of these fields; the IR evidence
audit script wrote no manifest at all before this stage).

## Schema (version "1.0")

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"1.0"`. Bump on any breaking field change. |
| `generated_utc` | string (ISO-8601) | Wall-clock time the manifest was written. |
| `generator_script` | string | Repo-relative path of the script that produced this manifest. |
| `git.commit` | string | Full 40-char commit hash of `HEAD`, or `"UNKNOWN"` if not run inside a git repo. |
| `git.dirty` | bool or null | `True` if `git status --porcelain` is non-empty (uncommitted changes present); `null` if commit info was unavailable. |
| `python_version` | string | `sys.version` of the interpreter that ran the workflow. |
| `platform` | string | `platform.platform()` (OS + architecture). |
| `dependency_versions` | object | `{package_name: installed_version}` for a caller-specified list (default: numpy/scipy/pandas/scikit-learn/networkx); `"NOT_INSTALLED"` if a named package is absent. |
| `solver_version` | string | Installed `PySCIPOpt` version (via `verify_canonical_solver_version(allow_mismatch=True)`), or `"NOT_INSTALLED"`. Recorded even for workflows that do not use the exact-repair solver, since it costs nothing and documents environment completeness. |
| `seeds` | object | `{seed_name: value}` for every random seed the workflow used (e.g. `{"bootstrap_seed": 13}`). Empty object if the workflow is fully deterministic with no randomness. |
| `independence_cluster_count` | int or null | Number of independence clusters (e.g. unique queries) the analysis's statistical inference was conditioned on. `null` for workflows where this concept does not apply. |
| `config` | object | Free-form, workflow-specific configuration (thresholds, method names, replicate counts). |
| `input_file_hashes` | object | `{file_path: sha256_hex}` for every file under each declared input path (directories are expanded recursively, file-by-file, not combined into one directory digest). |
| `output_file_hashes` | object | Same shape as `input_file_hashes`, for the workflow's declared output files. |
| `extra` | object | Anything workflow-specific that doesn't fit the fields above (e.g. the real-LLM re-analysis's `population_summary` and its three `no_new_*` boolean claims). |

## Design decisions

- **Never raises.** Every sub-collector (`git_commit_info`, `dependency_versions`,
  `solver_version`) degrades to a documented sentinel (`"UNKNOWN"`,
  `"NOT_INSTALLED"`, `null`) rather than raising, so that provenance
  collection itself can never become a new reason a canonical workflow fails.
  This was a deliberate choice: a manifest that is present but honestly
  reports "solver not installed" is more useful than a workflow that crashes
  trying to produce one.
- **Directories hash per-file, not combined.** A single combined directory
  digest would tell you *that* something changed but not *what* — expanding
  to one entry per contained file means a future diff against a stored
  manifest can point at the exact file that changed.
- **`git.dirty` is recorded, not enforced.** This stage does not block a
  workflow from running with uncommitted changes (that would be too
  disruptive for iterative research use); it only makes the fact visible in
  the manifest, so a reviewer comparing two runs' manifests can see if one
  was generated from a dirty tree.
- **Not a new mandatory gate.** `collect_provenance()` is opt-in per workflow;
  it was added to the two existing canonical workflows this stage but nothing
  in the repository requires every script to adopt it. Extending it further
  (e.g. to `scripts/run_synthetic.py`) is left to future work if desired, not
  assumed necessary by this stage's scope.

## Known limitation

`dependency_versions` defaults to a fixed short list (numpy/scipy/pandas/
scikit-learn/networkx) rather than every installed package — callers that
depend on more (e.g. the real-LLM re-analysis passing no override still uses
this default, since it needs nothing beyond those five for its own
computation) can pass `dependency_names=[...]` explicitly. `requirements-lock.txt`
remains the source of truth for the complete installed-package set; this
field is a convenience cross-check, not a substitute for it.
