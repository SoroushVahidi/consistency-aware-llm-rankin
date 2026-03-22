# Full Dataset Access Status

This report is an evidence-based audit of dataset usability in the current checkout and current Python environment.

It separates four different questions:

- whether code support exists,
- whether local raw/processed data is present,
- whether the normal experiment pipeline can run now,
- whether the publication-vote / paper-evidence pipeline is included and runnable now.

## Paper-Relevant Dataset Set

Datasets relevant to the current repo paths are:

- Main experiment pipeline: `scidocs`, `fiqa`, `hotpotqa`, `bright`
  - evidence: `src/consistency_ranker/data/dataset_registry.py`
  - evidence: `scripts/run_all_real_experiments.py` uses `DATASET_NAMES`
- Publication-vote pipeline:
  - `scidocs`, `hotpotqa`
  - optional `bright` via `--include-bright`
  - `fiqa` is not included there
  - evidence: `scripts/run_publication_vote_suite.py`
- Paper evidence package:
  - `scidocs`, `hotpotqa`, `bright`
  - `fiqa` is not included there
  - evidence: `scripts/build_paper_evidence_package.py`
- Paper summary script:
  - `scidocs`, `hotpotqa`, `bright`
  - `fiqa` is not included there
  - evidence: `scripts/summarize_publication_vote_suite.py`

No additional dataset names beyond these four appeared in the current main/paper-facing dataset lists.

## Status Table

| dataset | code support | raw data present | processed data present | pairwise present | included in publication pipeline | publication outputs present | current status | exact blocker if any | exact next command |
|---|---|---|---|---|---|---|---|---|---|
| `scidocs` | Yes | Yes | Yes | Yes | Yes | Partial: `outputs/real_full/scidocs/...` and stale rows in `outputs/pub_vote_cmp_v2/paper_package/...`; current per-variant pub-vote outputs are not complete | Accessible but not fully publication-regeneration-ready | `run_publication_vote_suite.py` fails in current env when `generate_score_file.py --ranker minilm` hits missing `torch` | `python -m pip install torch` |
| `hotpotqa` | Yes | Yes | Yes | Yes | Yes | Partial: `outputs/real_full/hotpotqa/...` and stale rows in `outputs/pub_vote_cmp_v2/paper_package/...`; no current `outputs/pub_vote_cmp_v2/hotpotqa/...` run outputs | Accessible but not fully publication-regeneration-ready | Same publication-suite dependency blocker: `torch` missing for the `minilm` ranker path | `python -m pip install torch` |
| `bright` | Yes | Yes | Yes | Yes | Yes, but optional in `run_publication_vote_suite.py` via `--include-bright` | Real experiment outputs present in `outputs/real_full/bright/...`; no publication-vote outputs in `outputs/pub_vote_cmp_v2/bright/...` | Accessible but not publication-ready | Publication-vote pipeline blocked by missing `torch`; BRIGHT publication outputs have not yet been generated | `python -m pip install torch` |
| `fiqa` | Yes | No | No | No | No | `outputs/real_full/fiqa/...` exists from prior runs, but there are no local processed inputs and no publication-vote / paper-package support | Blocked by dependency/path issue and local files missing | Local `data/raw/beir/fiqa` and `data/processed/beir/fiqa` are missing; `python scripts/download_datasets.py --dataset fiqa` fails because active `datasets` import is broken against current `huggingface_hub` | `python -m pip install \"datasets>=2.18,<4\" \"huggingface-hub>=0.21,<1\"` |

## Exact Inclusion Controls

### Main experiment pipeline

- `src/consistency_ranker/data/dataset_registry.py`
  - registry contains `scidocs`, `fiqa`, `hotpotqa`, `bright`
- `scripts/run_all_real_experiments.py`
  - uses `DATASET_NAMES`
- `scripts/prepare_datasets.py`
  - uses `DATASET_NAMES`
- `scripts/download_datasets.py`
  - uses `DATASET_NAMES`
- `scripts/generate_bootstrap_tables.py`
  - `ALL_DATASETS = ["scidocs", "fiqa", "hotpotqa", "bright"]`

Conclusion:

- all four datasets are included in the main experiment pipeline

### Publication-vote pipeline

- `scripts/run_publication_vote_suite.py`
  - always includes `scidocs`
  - always includes `hotpotqa`
  - includes `bright` only when `--include-bright` is passed
  - does not include `fiqa`

Conclusion:

- `scidocs`: included
- `hotpotqa`: included
- `bright`: partially included / optional
- `fiqa`: excluded

### Paper evidence package

- `scripts/build_paper_evidence_package.py`
  - `DATASETS = ("scidocs", "hotpotqa", "bright")`

Conclusion:

- `scidocs`: included
- `hotpotqa`: included
- `bright`: included
- `fiqa`: excluded

### Paper summary helper

- `scripts/summarize_publication_vote_suite.py`
  - loops over `("scidocs", "hotpotqa", "bright")`

Conclusion:

- `scidocs`: included
- `hotpotqa`: included
- `bright`: included
- `fiqa`: excluded

## Exact Paths Checked

### SciDocs

Raw path checked:

- `data/raw/beir/scidocs`

Processed path checked:

- `data/processed/beir/scidocs`
- `data/processed/beir/scidocs/pairwise`

Key files checked:

- `data/raw/beir/scidocs/queries.jsonl`
- `data/raw/beir/scidocs/documents.jsonl`
- `data/raw/beir/scidocs/qrels.jsonl`
- `data/processed/beir/scidocs/queries.jsonl`
- `data/processed/beir/scidocs/documents.jsonl`
- `data/processed/beir/scidocs/qrels.jsonl`
- `data/processed/beir/scidocs/pairwise/preferences.jsonl`

Publication/output paths checked:

- `outputs/real_full/scidocs/qrels/scidocs_experiment_summary.json`
- `outputs/real_full/scidocs/qrels_flip/scidocs_experiment_summary.json`
- `outputs/real_small_validation/scidocs/qrels/scidocs_experiment_summary.json`
- `outputs/pub_vote_cmp_v2/scidocs/`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`

Observed local directory contents:

- `data/raw/beir/scidocs` contains raw JSONL plus Hugging Face cache/lock files
- `data/processed/beir/scidocs` contains processed JSONL files
- `data/processed/beir/scidocs/pairwise` contains `preferences.jsonl`

### FiQA

Raw path checked:

- `data/raw/beir/fiqa`

Processed path checked:

- `data/processed/beir/fiqa`
- `data/processed/beir/fiqa/pairwise`

Key files checked:

- `data/raw/beir/fiqa/queries.jsonl`
- `data/raw/beir/fiqa/documents.jsonl`
- `data/raw/beir/fiqa/qrels.jsonl`
- `data/processed/beir/fiqa/queries.jsonl`
- `data/processed/beir/fiqa/documents.jsonl`
- `data/processed/beir/fiqa/qrels.jsonl`
- `data/processed/beir/fiqa/pairwise/preferences.jsonl`

Publication/output paths checked:

- `outputs/real_full/fiqa/qrels/fiqa_experiment_summary.json`
- `outputs/real_full/fiqa/qrels_flip/fiqa_experiment_summary.json`
- `outputs/real_small_validation/fiqa/qrels/fiqa_experiment_summary.json`
- `outputs/pub_vote_cmp_v2/fiqa/`

Observed local directory contents:

- `data/raw/beir/fiqa`: only `.gitkeep`
- `data/processed/beir/fiqa`: only `.gitkeep` and `pairwise/`
- `data/processed/beir/fiqa/pairwise`: only `.gitkeep`

### HotpotQA

Raw path checked:

- `data/raw/hotpotqa`

Processed path checked:

- `data/processed/hotpotqa`
- `data/processed/hotpotqa/pairwise`

Key files checked:

- `data/raw/hotpotqa/queries.jsonl`
- `data/raw/hotpotqa/documents.jsonl`
- `data/raw/hotpotqa/qrels.jsonl`
- `data/processed/hotpotqa/queries.jsonl`
- `data/processed/hotpotqa/documents.jsonl`
- `data/processed/hotpotqa/qrels.jsonl`
- `data/processed/hotpotqa/pairwise/preferences.jsonl`

Publication/output paths checked:

- `outputs/real_full/hotpotqa/qrels/hotpotqa_experiment_summary.json`
- `outputs/real_full/hotpotqa/qrels_flip/hotpotqa_experiment_summary.json`
- `outputs/real_small_validation/hotpotqa/qrels/hotpotqa_experiment_summary.json`
- `outputs/pub_vote_cmp_v2/hotpotqa/`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`

Observed local directory contents:

- `data/raw/hotpotqa` contains raw JSONL plus Hugging Face cache/lock files
- `data/processed/hotpotqa` contains processed JSONL files
- `data/processed/hotpotqa/pairwise` contains `preferences.jsonl`

### BRIGHT

Raw path checked:

- `data/raw/bright`

Processed path checked:

- `data/processed/bright`
- `data/processed/bright/pairwise`

Key files checked:

- `data/raw/bright/queries.jsonl`
- `data/raw/bright/documents.jsonl`
- `data/raw/bright/qrels.jsonl`
- `data/processed/bright/queries.jsonl`
- `data/processed/bright/documents.jsonl`
- `data/processed/bright/qrels.jsonl`
- `data/processed/bright/pairwise/preferences.jsonl`

Publication/output paths checked:

- `outputs/real_full/bright/qrels/bright_experiment_summary.json`
- `outputs/real_full/bright/qrels_flip/bright_experiment_summary.json`
- `outputs/real_small_validation/bright/qrels/bright_experiment_summary.json`
- `outputs/pub_vote_cmp_v2/bright/`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`

Observed local directory contents:

- `data/raw/bright` contains raw JSONL, loader README, Hugging Face cache/lock files
- `data/processed/bright` contains processed JSONL files
- `data/processed/bright/pairwise` contains `preferences.jsonl`

## Light Execution Validation

### Processed-loader checks

Command used:

```bash
PYTHONPATH=src python - <<'PY'
from consistency_ranker.data.unified_loader import load_dataset_splits
for name in ['scidocs','fiqa','hotpotqa','bright']:
    try:
        q,d,r = load_dataset_splits(name)
        print(name, 'LOAD_OK', len(q), len(d), len(r))
    except Exception as exc:
        print(name, 'LOAD_ERR', type(exc).__name__)
        print(str(exc))
PY
```

Observed results:

- `scidocs LOAD_OK 1000 25657 29928`
- `fiqa LOAD_ERR FileNotFoundError`
- `hotpotqa LOAD_OK 7405 66568 73642`
- `bright LOAD_OK 1384 55643 1271958`

### Experiment smoke tests

SciDocs:

- command:
  - `python scripts/run_real_experiment.py --dataset scidocs --preference-source qrels --max-queries 5 --top-k 10 --no-plots --save-timings --output-dir outputs/scidocs_access_validation`
- result:
  - success
  - `outputs/scidocs_access_validation/scidocs/qrels/scidocs_experiment_summary.json`
  - summary reports `n_processed = 5`

HotpotQA:

- command:
  - `python scripts/run_real_experiment.py --dataset hotpotqa --preference-source qrels --max-queries 1 --top-k 5 --no-plots --save-timings --output-dir outputs/dataset_access_smoke`
- result:
  - success
  - `outputs/dataset_access_smoke/hotpotqa/qrels/hotpotqa_experiment_summary.json`
  - summary reports `n_processed = 1`

BRIGHT:

- command previously run in this session:
  - `python scripts/run_real_experiment.py --dataset bright --preference-source qrels --max-queries 5 --top-k 10 --no-plots --save-timings --output-dir outputs/bright_access_validation`
- result:
  - success
  - `outputs/bright_access_validation/bright/qrels/bright_experiment_summary.json`
  - summary reports `n_processed = 1`, `n_skipped = 4`

FiQA:

- command:
  - `python scripts/run_real_experiment.py --dataset fiqa --preference-source qrels --max-queries 1 --top-k 5 --no-plots --save-timings --output-dir outputs/dataset_access_smoke`
- result:
  - failure
  - exact error:
    - `/mmfs1/home/sv96/consistency-aware-llm-rankin/data/processed/beir/fiqa/queries.jsonl does not exist. Run: python scripts/prepare_datasets.py --dataset fiqa`

### Publication-vote pipeline probe

Command used:

```bash
python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2 --include-bright --bright-queries 1 --bright-top-n 5
```

Observed result:

- the script started
- it created partial `scidocs` publication inputs:
  - `outputs/pub_vote_cmp_v2/scidocs/query_ids.txt`
  - `outputs/pub_vote_cmp_v2/scidocs/scores_bm25.jsonl`
  - `outputs/pub_vote_cmp_v2/scidocs/scores_tfidf.jsonl`
- it then failed on the `minilm` ranker step

Exact failure:

- underlying exception:
  - `ModuleNotFoundError: No module named 'torch'`
- surfaced by the script as:
  - `RuntimeError: MiniLM ranker requires sentence-transformers. Install with: python3 -m pip install sentence-transformers`

Conclusion:

- publication-vote regeneration is currently blocked for all datasets that rely on this suite

## Exact Current Blockers

### SciDocs

- No blocker for main experiment runs
- Blocker for publication-vote regeneration:
  - missing `torch` dependency for `minilm` score generation

### HotpotQA

- No blocker for main experiment runs
- Blocker for publication-vote regeneration:
  - missing `torch` dependency for `minilm` score generation

### BRIGHT

- No blocker for main experiment runs
- Blocker for publication-vote readiness:
  - publication-vote suite is blocked by missing `torch`
  - no BRIGHT publication-vote outputs have been generated yet under `outputs/pub_vote_cmp_v2/bright`

### FiQA

- Missing local raw files
- Missing local processed files
- Missing local pairwise preferences
- Excluded from publication-vote and paper-evidence scripts
- Acquisition path currently blocked by dependency/version mismatch in the active Python:
  - `python scripts/download_datasets.py --dataset fiqa --max-docs 1 --max-queries 1`
  - reported `ERROR: The 'datasets' library is not installed.`
  - direct import check showed the real issue:
    - `ImportError: cannot import name 'HfFolder' from 'huggingface_hub'`

## Practical Classification

- `scidocs`: fully accessible and experiment-ready, but not publication-regeneration-ready in the current environment
- `hotpotqa`: fully accessible and experiment-ready, but not publication-regeneration-ready in the current environment
- `bright`: accessible and experiment-ready, but not publication-ready because publication-vote outputs are missing and the publication suite is blocked by `torch`
- `fiqa`: code-supported but local files missing; also blocked by dependency/version issues; not publication-pipeline-supported

## Bottom Line

- Datasets fully ready for normal experiments right now:
  - `scidocs`
  - `hotpotqa`
  - `bright`
- Dataset still blocked:
  - `fiqa`
- Datasets still blocked for publication-vote regeneration in the current environment:
  - `scidocs`
  - `hotpotqa`
  - `bright`
  - root cause: missing `torch` for the `minilm` ranker step in `run_publication_vote_suite.py`
