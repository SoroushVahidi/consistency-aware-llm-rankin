# BRIGHT Access And Pipeline Status

This report records the actual BRIGHT materialization and validation work performed in this checkout.

## Summary

- Official source used: `xlangai/BRIGHT` on Hugging Face.
- Repo code path used for acquisition: `scripts/download_datasets.py --dataset bright --bright-task examples`, which calls `src/consistency_ranker/data/bright_loader.py`.
- Repo code path expects:
  - primary examples config: `examples`
  - document hydration configs: `documents`, then `long_documents`
- BRIGHT is now locally accessible in this repo.
- BRIGHT is now prepared for normal experiment runs in this repo.
- BRIGHT is not yet fully publication-package-ready because `outputs/pub_vote_cmp_v2` does not yet contain BRIGHT publication-vote outputs.

## Official Source Used

- Dataset repo: `xlangai/BRIGHT`
- Live checks previously succeeded for:
  - dataset metadata access
  - config-name listing
  - direct example loading
  - direct documents-config loading

The loader path in `src/consistency_ranker/data/bright_loader.py` confirms the repo expects:

1. `load_dataset("xlangai/BRIGHT", "examples", ...)` for the query/example rows
2. `load_dataset("xlangai/BRIGHT", "documents", ...)` to fill missing document text
3. `load_dataset("xlangai/BRIGHT", "long_documents", ...)` as fallback hydration

## Repo Code Path Used

Acquisition path:

- `scripts/download_datasets.py`
- function `download_bright(...)`
- calls `consistency_ranker.data.bright_loader.download_bright(...)`

Prepare path:

- `scripts/prepare_datasets.py`
- function `prepare_bright(...)`
- expected raw files:
  - `data/raw/bright/queries.jsonl`
  - `data/raw/bright/documents.jsonl`
  - `data/raw/bright/qrels.jsonl`
- expected processed files:
  - `data/processed/bright/queries.jsonl`
  - `data/processed/bright/documents.jsonl`
  - `data/processed/bright/qrels.jsonl`
  - `data/processed/bright/pairwise/preferences.jsonl`

Downstream experiment path:

- `scripts/run_real_experiment.py --dataset bright ...`

## Exact Commands Run

These are the commands executed during this work:

```bash
python scripts/download_datasets.py --dataset bright --bright-task examples
python scripts/prepare_datasets.py --dataset bright --force
PYTHONPATH=src python - <<'PY'
from consistency_ranker.data.unified_loader import load_dataset_splits, preferences_from_qrels
queries, docs, qrels = load_dataset_splits('bright')
print('load_ok', len(queries), len(docs), len(qrels))
prefs = preferences_from_qrels(qrels, top_k=100, max_queries=5, seed=42, weight_scheme='grade_diff')
print('prefs_for_5_queries', len(prefs))
PY
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from argparse import Namespace
import scripts.prepare_datasets as prep
args = Namespace(top_k=None, max_queries=None, seed=None, weight_scheme='grade_diff', force=True)
out = Path('data/processed/bright')
prep._generate_preferences('bright', out, args)
PY
python scripts/run_real_experiment.py --dataset bright --preference-source qrels --max-queries 5 --top-k 10 --no-plots --save-timings --output-dir outputs/bright_access_validation
python scripts/run_publication_vote_suite.py --help
python scripts/summarize_publication_vote_suite.py
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
python -m py_compile scripts/run_publication_vote_suite.py scripts/build_paper_evidence_package.py scripts/summarize_publication_vote_suite.py
```

## Exact Raw Files Created

Expected raw files successfully created under `data/raw/bright`:

- `queries.jsonl`
- `documents.jsonl`
- `qrels.jsonl`

Other files present in the same directory after download:

- `.gitkeep`
- `README.md`
- `_mmfs1_home_sv96_consistency-aware-llm-rankin_data_raw_bright_xlangai___bright_documents_0.0.0_3066d29c9651a576c8aba4832d249807b181ecae.lock`
- `_mmfs1_home_sv96_consistency-aware-llm-rankin_data_raw_bright_xlangai___bright_examples_0.0.0_3066d29c9651a576c8aba4832d249807b181ecae.lock`
- `_mmfs1_home_sv96_consistency-aware-llm-rankin_data_raw_bright_xlangai___bright_long_documents_0.0.0_3066d29c9651a576c8aba4832d249807b181ecae.lock`
- `xlangai___bright/` (Hugging Face cache directory)

Observed raw data sizes at inspection time:

- `queries.jsonl`: `1,227,648` bytes
- `documents.jsonl`: `217,116,610` bytes
- `qrels.jsonl`: `143,607,673` bytes

Download result reported by the repo:

- `1384` queries
- `55643` documents
- `1271958` qrels

## Exact Processed Files Created

Created under `data/processed/bright`:

- `queries.jsonl`
- `documents.jsonl`
- `qrels.jsonl`

Created under `data/processed/bright/pairwise`:

- `preferences.jsonl`

Other files present:

- `data/processed/bright/.gitkeep`
- `data/processed/bright/pairwise/.gitkeep`

Observed processed data sizes at inspection time:

- `data/processed/bright/queries.jsonl`: `1,227,558` bytes
- `data/processed/bright/documents.jsonl`: `217,098,651` bytes
- `data/processed/bright/qrels.jsonl`: `143,607,673` bytes
- `data/processed/bright/pairwise/preferences.jsonl`: `9,441,489` bytes

## Preparation And Validation

### Preparation result

The BRIGHT prepare CLI wrote the processed JSONL files successfully:

- `data/processed/bright/queries.jsonl`
- `data/processed/bright/documents.jsonl`
- `data/processed/bright/qrels.jsonl`

Observed prepare-path quirk:

- `python -u scripts/prepare_datasets.py --dataset bright --force` printed the processed-file writes but did not leave behind `data/processed/bright/pairwise/preferences.jsonl`
- direct invocation of the same module's `_generate_preferences("bright", ...)` succeeded immediately afterward and created:
  - `data/processed/bright/pairwise/preferences.jsonl`

Evidence that processed data itself is valid:

- `load_dataset_splits('bright')` succeeded
- loaded counts:
  - `1384` queries
  - `55643` documents
  - `1271958` qrels
- direct preference derivation on the processed qrels succeeded:
  - `prefs_for_5_queries = 2891`

### Downstream validation result

Smoke-test experiment command:

```bash
python scripts/run_real_experiment.py --dataset bright --preference-source qrels --max-queries 5 --top-k 10 --no-plots --save-timings --output-dir outputs/bright_access_validation
```

Observed result:

- command exited successfully
- output directory created: `outputs/bright_access_validation/bright/qrels`
- output files created:
  - `bright_per_query.csv`
  - `bright_summary.csv`
  - `bright_experiment_summary.json`
  - `timings/bright_timings.csv`
  - `timings/bright_timings.json`

Experiment summary showed:

- `n_processed = 1`
- `n_skipped = 4`
- skipped reason for the other 4 sampled queries:
  - `no preferences generated from source='qrels'`

This is enough to prove the normal experiment pipeline can now see and use BRIGHT in this checkout.

## Local Accessibility Status

Is BRIGHT now locally accessible?

- Yes.

Evidence:

- repo-local raw files now exist at `data/raw/bright`
- repo-local processed files now exist at `data/processed/bright`
- processed loader succeeds
- experiment CLI succeeds

## Pipeline-Ready Status

Is BRIGHT now pipeline-ready for normal experiments?

- Yes, for the standard real-data experiment pipeline.

Evidence:

- `scripts/run_real_experiment.py --dataset bright ...` completed successfully
- required processed artifacts exist
- pairwise preferences now exist

Remaining caveat:

- the prepare CLI showed brittle behavior around pairwise generation in this session, so the pairwise artifact was finalized via direct invocation of `_generate_preferences(...)`

## Publication-Pipeline Inclusion

### What was excluding BRIGHT

Before changes in this session, BRIGHT was excluded from publication-facing code in at least these places:

- `scripts/run_publication_vote_suite.py`
  - processed-query path helper only handled `scidocs` and `hotpotqa`
  - dataset loop only ran `scidocs` and `hotpotqa`
- `scripts/build_paper_evidence_package.py`
  - `DATASETS = ("scidocs", "hotpotqa")`
- `scripts/summarize_publication_vote_suite.py`
  - loop only handled `("scidocs", "hotpotqa")`

### What was updated

Updated in this session:

- `scripts/run_publication_vote_suite.py`
  - added `bright` processed-query path support
  - added optional `--include-bright`
  - added `--bright-queries`
  - added `--bright-top-n`
  - added BRIGHT to the dataset loop when `--include-bright` is passed
- `scripts/build_paper_evidence_package.py`
  - updated `DATASETS` to include `bright`
- `scripts/summarize_publication_vote_suite.py`
  - updated dataset loop to include `bright`

Validation of those edits:

- `python scripts/run_publication_vote_suite.py --help` succeeded and showed the new BRIGHT options
- `python scripts/summarize_publication_vote_suite.py` now emits BRIGHT rows
- `python -m py_compile ...` succeeded for all three edited scripts

### Is BRIGHT now included in the publication package?

Code-path inclusion: yes.

Publication outputs already present: no.

Exact blocking reason:

- `outputs/pub_vote_cmp_v2` currently has no data, so the package builder still fails with:
  - `No data under outputs/pub_vote_cmp_v2`

That means BRIGHT is now included in the publication code paths, but the actual publication-vote outputs for BRIGHT still need to be generated.

## Exact Remaining Manual Step

If you want BRIGHT to participate in the publication-vote package, the next manual step is to generate the publication-vote outputs, e.g.:

```bash
python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2 --include-bright
```

After that, rebuild the paper package:

```bash
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
```

## Bottom Line

- BRIGHT is now locally downloaded in the repo.
- BRIGHT is now prepared for normal experiments in the repo.
- BRIGHT is now included in the publication-pipeline code paths.
- BRIGHT is not yet fully publication-package-ready because the publication-vote outputs under `outputs/pub_vote_cmp_v2` have not yet been generated.
