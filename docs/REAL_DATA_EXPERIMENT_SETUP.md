# Real-Data Experiment Setup Validation

This document is generated from the current repository filesystem and script configuration.

## MANUAL ACTION REQUIRED

At least one dataset is missing required raw and/or processed files in the current checkout. Real-data experiments cannot be run cleanly until those files are populated and `prepare_datasets.py` has been run.

## 1. Dataset access and consistency

### scidocs

- Expected raw data path: `/workspace/consistency-aware-llm-rankin/data/raw/beir/scidocs`.
- Expected processed path: `/workspace/consistency-aware-llm-rankin/data/processed/beir/scidocs`.
- Expected raw filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl']`.
- Expected processed filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl', 'pairwise/preferences.jsonl']`.
- Raw status: `missing`; processed status: `missing`.
- Raw files present: `[]`; processed files present: `[]`.
- Proxy-generated data detected: `False` in the current checkout.
- Real downloaded raw files are **not** present.
- Processed dataset files are **not** complete.
- Download required: `True`; prepare step required: `True`.
- Script expecting raw files: `scripts/prepare_datasets.py`; script consuming processed files: `scripts/run_real_experiment.py`.
- **MANUAL ACTION REQUIRED** before real-data experiments.

### fiqa

- Expected raw data path: `/workspace/consistency-aware-llm-rankin/data/raw/beir/fiqa`.
- Expected processed path: `/workspace/consistency-aware-llm-rankin/data/processed/beir/fiqa`.
- Expected raw filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl']`.
- Expected processed filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl', 'pairwise/preferences.jsonl']`.
- Raw status: `missing`; processed status: `missing`.
- Raw files present: `[]`; processed files present: `[]`.
- Proxy-generated data detected: `False` in the current checkout.
- Real downloaded raw files are **not** present.
- Processed dataset files are **not** complete.
- Download required: `True`; prepare step required: `True`.
- Script expecting raw files: `scripts/prepare_datasets.py`; script consuming processed files: `scripts/run_real_experiment.py`.
- **MANUAL ACTION REQUIRED** before real-data experiments.

### hotpotqa

- Expected raw data path: `/workspace/consistency-aware-llm-rankin/data/raw/hotpotqa`.
- Expected processed path: `/workspace/consistency-aware-llm-rankin/data/processed/hotpotqa`.
- Expected raw filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl']`.
- Expected processed filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl', 'pairwise/preferences.jsonl']`.
- Raw status: `missing`; processed status: `missing`.
- Raw files present: `[]`; processed files present: `[]`.
- Proxy-generated data detected: `False` in the current checkout.
- Real downloaded raw files are **not** present.
- Processed dataset files are **not** complete.
- Download required: `True`; prepare step required: `True`.
- Script expecting raw files: `scripts/prepare_datasets.py`; script consuming processed files: `scripts/run_real_experiment.py`.
- **MANUAL ACTION REQUIRED** before real-data experiments.

### bright

- Expected raw data path: `/workspace/consistency-aware-llm-rankin/data/raw/bright`.
- Expected processed path: `/workspace/consistency-aware-llm-rankin/data/processed/bright`.
- Expected raw filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl']`.
- Expected processed filenames: `['queries.jsonl', 'documents.jsonl', 'qrels.jsonl', 'pairwise/preferences.jsonl']`.
- Raw status: `missing`; processed status: `missing`.
- Raw files present: `[]`; processed files present: `[]`.
- Proxy-generated data detected: `False` in the current checkout.
- Real downloaded raw files are **not** present.
- Processed dataset files are **not** complete.
- Manual-download note: `/workspace/consistency-aware-llm-rankin/data/raw/bright/README.md` is the expected instruction file for BRIGHT-style manual setup.
- Download required: `True`; prepare step required: `True`.
- Script expecting raw files: `scripts/prepare_datasets.py`; script consuming processed files: `scripts/run_real_experiment.py`.
- **MANUAL ACTION REQUIRED** before real-data experiments.

## 2. Minimal real-data experiment design

These runs are meant for low-cost validation, not final paper numbers. Using 50–75 queries is enough to verify data loading, per-query metrics, timing output, and whether the shortlist methods show any real-data signal before launching Wulver-scale jobs.

### scidocs
- Subset size: `75` queries.
- Candidate cutoff: `top_k=20`.
- Methods: `score_sum`, `borda`, `greedy_fas_weighted_balance`, `hybrid_rrf_fas_regularized`.
- Preference sources: `qrels` and `qrels_flip`.
- Why this is enough: it gives paired per-query comparisons for bootstrap, validates repaired-vs-unrepaired behavior, and keeps graph sizes small enough for a cheap smoke test.

### fiqa
- Subset size: `75` queries.
- Candidate cutoff: `top_k=20`.
- Methods: `score_sum`, `borda`, `greedy_fas_weighted_balance`, `hybrid_rrf_fas_regularized`.
- Preference sources: `qrels` and `qrels_flip`.
- Why this is enough: it gives paired per-query comparisons for bootstrap, validates repaired-vs-unrepaired behavior, and keeps graph sizes small enough for a cheap smoke test.

### hotpotqa
- Subset size: `50` queries.
- Candidate cutoff: `top_k=10`.
- Methods: `score_sum`, `borda`, `greedy_fas_weighted_balance`, `hybrid_rrf_fas_regularized`.
- Preference sources: `qrels` and `qrels_flip`.
- Why this is enough: it gives paired per-query comparisons for bootstrap, validates repaired-vs-unrepaired behavior, and keeps graph sizes small enough for a cheap smoke test.

### bright
- Subset size: `50` queries.
- Candidate cutoff: `top_k=20`.
- Methods: `score_sum`, `borda`, `greedy_fas_weighted_balance`, `hybrid_rrf_fas_regularized`.
- Preference sources: `qrels` and `qrels_flip`.
- Why this is enough: it gives paired per-query comparisons for bootstrap, validates repaired-vs-unrepaired behavior, and keeps graph sizes small enough for a cheap smoke test.

## 3. Exact commands (do not execute here)

### scidocs
```bash
python scripts/download_datasets.py --dataset scidocs --max-queries 75
python scripts/prepare_datasets.py --dataset scidocs --max-queries 75 --top-k 20 --weight-scheme grade_diff --force
python scripts/run_real_experiment.py --dataset scidocs --max-queries 75 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/scidocs --save-timings --no-plots --preference-source qrels --seed 42
python scripts/run_real_experiment.py --dataset scidocs --max-queries 75 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/scidocs --save-timings --no-plots --preference-source qrels_flip --flip-prob 0.15 --seed 42
```

### fiqa
```bash
python scripts/download_datasets.py --dataset fiqa --max-queries 75
python scripts/prepare_datasets.py --dataset fiqa --max-queries 75 --top-k 20 --weight-scheme grade_diff --force
python scripts/run_real_experiment.py --dataset fiqa --max-queries 75 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/fiqa --save-timings --no-plots --preference-source qrels --seed 42
python scripts/run_real_experiment.py --dataset fiqa --max-queries 75 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/fiqa --save-timings --no-plots --preference-source qrels_flip --flip-prob 0.15 --seed 42
```

### hotpotqa
```bash
python scripts/download_datasets.py --dataset hotpotqa --max-queries 50
python scripts/prepare_datasets.py --dataset hotpotqa --max-queries 50 --top-k 10 --weight-scheme grade_diff --force
python scripts/run_real_experiment.py --dataset hotpotqa --max-queries 50 --top-k 10 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/hotpotqa --save-timings --no-plots --preference-source qrels --seed 42
python scripts/run_real_experiment.py --dataset hotpotqa --max-queries 50 --top-k 10 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/hotpotqa --save-timings --no-plots --preference-source qrels_flip --flip-prob 0.15 --seed 42
```

### bright
```bash
python scripts/download_datasets.py --dataset bright --bright-task examples --max-queries 50
python scripts/prepare_datasets.py --dataset bright --max-queries 50 --top-k 20 --weight-scheme grade_diff --force
python scripts/run_real_experiment.py --dataset bright --max-queries 50 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/bright --save-timings --no-plots --preference-source qrels --seed 42
python scripts/run_real_experiment.py --dataset bright --max-queries 50 --top-k 20 --weight-scheme grade_diff --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --output-dir outputs/real_small_validation/bright --save-timings --no-plots --preference-source qrels_flip --flip-prob 0.15 --seed 42
```
If the BRIGHT download command does not populate `queries.jsonl`, `documents.jsonl`, and `qrels.jsonl`, follow the manual instructions in `data/raw/bright/README.md` and rerun `prepare_datasets.py`.

## 4. Wulver / HPC-ready commands (do not execute here)

Parallelize across datasets and across `qrels_flip` seeds. The `qrels` run needs only one seed because it is deterministic once all eligible queries are included; `qrels_flip` should be replicated because edge corruption is stochastic.

### scidocs
```bash
python scripts/run_real_experiment.py --dataset scidocs --top-k 20 --weight-scheme grade_diff --preference-source qrels --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/scidocs --save-timings --no-plots
python scripts/run_real_experiment.py --dataset scidocs --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/scidocs/seed_42 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset scidocs --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 123 --output-dir outputs/real_full/scidocs/seed_123 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset scidocs --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 456 --output-dir outputs/real_full/scidocs/seed_456 --save-timings --no-plots
```

### fiqa
```bash
python scripts/run_real_experiment.py --dataset fiqa --top-k 20 --weight-scheme grade_diff --preference-source qrels --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/fiqa --save-timings --no-plots
python scripts/run_real_experiment.py --dataset fiqa --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/fiqa/seed_42 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset fiqa --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 123 --output-dir outputs/real_full/fiqa/seed_123 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset fiqa --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 456 --output-dir outputs/real_full/fiqa/seed_456 --save-timings --no-plots
```

### hotpotqa
```bash
python scripts/run_real_experiment.py --dataset hotpotqa --top-k 10 --weight-scheme grade_diff --preference-source qrels --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/hotpotqa --save-timings --no-plots
python scripts/run_real_experiment.py --dataset hotpotqa --top-k 10 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/hotpotqa/seed_42 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset hotpotqa --top-k 10 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 123 --output-dir outputs/real_full/hotpotqa/seed_123 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset hotpotqa --top-k 10 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 456 --output-dir outputs/real_full/hotpotqa/seed_456 --save-timings --no-plots
```

### bright
```bash
python scripts/run_real_experiment.py --dataset bright --top-k 20 --weight-scheme grade_diff --preference-source qrels --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/bright --save-timings --no-plots
python scripts/run_real_experiment.py --dataset bright --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 42 --output-dir outputs/real_full/bright/seed_42 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset bright --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 123 --output-dir outputs/real_full/bright/seed_123 --save-timings --no-plots
python scripts/run_real_experiment.py --dataset bright --top-k 20 --weight-scheme grade_diff --preference-source qrels_flip --flip-prob 0.15 --methods score_sum borda greedy_fas_weighted_balance hybrid_rrf_fas_regularized --seed 456 --output-dir outputs/real_full/bright/seed_456 --save-timings --no-plots
```

Dataset-parallel launcher example:

```bash
for dataset in scidocs fiqa hotpotqa bright; do
  bash run_${dataset}_real_jobs.sh &
done
wait
```

## 5. Bootstrap / significance plan

### scidocs
```bash
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/scidocs/qrels/scidocs_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/scidocs/qrels/bootstrap/scidocs_qrels_ndcg_vs_borda.json --output-csv outputs/real_small_validation/scidocs/qrels/bootstrap/scidocs_qrels_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/scidocs/qrels/scidocs_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/scidocs/qrels/bootstrap/scidocs_qrels_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/scidocs/qrels/bootstrap/scidocs_qrels_ndcg_vs_score_sum.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/scidocs/qrels_flip/scidocs_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/scidocs/qrels_flip/bootstrap/scidocs_qrels_flip_ndcg_vs_borda.json --output-csv outputs/real_small_validation/scidocs/qrels_flip/bootstrap/scidocs_qrels_flip_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/scidocs/qrels_flip/scidocs_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/scidocs/qrels_flip/bootstrap/scidocs_qrels_flip_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/scidocs/qrels_flip/bootstrap/scidocs_qrels_flip_ndcg_vs_score_sum.csv
```

### fiqa
```bash
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/fiqa/qrels/fiqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/fiqa/qrels/bootstrap/fiqa_qrels_ndcg_vs_borda.json --output-csv outputs/real_small_validation/fiqa/qrels/bootstrap/fiqa_qrels_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/fiqa/qrels/fiqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/fiqa/qrels/bootstrap/fiqa_qrels_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/fiqa/qrels/bootstrap/fiqa_qrels_ndcg_vs_score_sum.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/fiqa/qrels_flip/fiqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/fiqa/qrels_flip/bootstrap/fiqa_qrels_flip_ndcg_vs_borda.json --output-csv outputs/real_small_validation/fiqa/qrels_flip/bootstrap/fiqa_qrels_flip_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/fiqa/qrels_flip/fiqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/fiqa/qrels_flip/bootstrap/fiqa_qrels_flip_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/fiqa/qrels_flip/bootstrap/fiqa_qrels_flip_ndcg_vs_score_sum.csv
```

### hotpotqa
```bash
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/hotpotqa/qrels/hotpotqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/hotpotqa/qrels/bootstrap/hotpotqa_qrels_ndcg_vs_borda.json --output-csv outputs/real_small_validation/hotpotqa/qrels/bootstrap/hotpotqa_qrels_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/hotpotqa/qrels/hotpotqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/hotpotqa/qrels/bootstrap/hotpotqa_qrels_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/hotpotqa/qrels/bootstrap/hotpotqa_qrels_ndcg_vs_score_sum.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/hotpotqa/qrels_flip/hotpotqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/hotpotqa/qrels_flip/bootstrap/hotpotqa_qrels_flip_ndcg_vs_borda.json --output-csv outputs/real_small_validation/hotpotqa/qrels_flip/bootstrap/hotpotqa_qrels_flip_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/hotpotqa/qrels_flip/hotpotqa_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/hotpotqa/qrels_flip/bootstrap/hotpotqa_qrels_flip_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/hotpotqa/qrels_flip/bootstrap/hotpotqa_qrels_flip_ndcg_vs_score_sum.csv
```

### bright
```bash
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/bright/qrels/bright_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/bright/qrels/bootstrap/bright_qrels_ndcg_vs_borda.json --output-csv outputs/real_small_validation/bright/qrels/bootstrap/bright_qrels_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/bright/qrels/bright_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/bright/qrels/bootstrap/bright_qrels_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/bright/qrels/bootstrap/bright_qrels_ndcg_vs_score_sum.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/bright/qrels_flip/bright_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b borda --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/bright/qrels_flip/bootstrap/bright_qrels_flip_ndcg_vs_borda.json --output-csv outputs/real_small_validation/bright/qrels_flip/bootstrap/bright_qrels_flip_ndcg_vs_borda.csv
python scripts/bootstrap_method_deltas.py --per-query-csv outputs/real_small_validation/bright/qrels_flip/bright_per_query.csv --metric ndcg_at_k --method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized --method-b score_sum --n-bootstrap 1000 --seed 42 --output-json outputs/real_small_validation/bright/qrels_flip/bootstrap/bright_qrels_flip_ndcg_vs_score_sum.json --output-csv outputs/real_small_validation/bright/qrels_flip/bootstrap/bright_qrels_flip_ndcg_vs_score_sum.csv
```

## 6. Expected output files

For each dataset `<dataset>` and preference source `<preference_source>`, `scripts/run_real_experiment.py` should create the following files under `<base-output-dir>/<preference_source>/`:

- `<dataset>_per_query.csv`: one row per query × method with graph statistics, FAS diagnostics, ranking metrics, and per-query runtime.
- `<dataset>_summary.csv`: method-level aggregate means/medians/maxima for ranking quality, inconsistency, graph size, and runtime.
- `<dataset>_experiment_summary.json`: structured experiment overview with processed/skipped counts, best method by primary metric, and global timing totals.
- `timings/<dataset>_timings.csv`: stage-level wall-clock totals/means across the run.
- `timings/<dataset>_timings.json`: machine-readable timing metadata mirroring the CSV.
- `plots/`: preference-source-specific figures when plotting is enabled.

## 7. Final checklist for the user

- Can be run immediately: lightweight script validation, command generation, and local/HPC launch planning.
- Requires manual dataset setup: **all datasets in the current checkout**, because required raw and processed files are absent or incomplete.
- Should be run locally first: the small validation commands under `outputs/real_small_validation/<dataset>/<preference_source>/`.
- Should be run on Wulver: the full-dataset commands under `outputs/real_full/<dataset>/<preference_source>/`, especially multi-seed `qrels_flip/seed_<seed>/` jobs.
- Extra note: `hybrid_rrf_fas_regularized` now has a self-contained score-sum fallback prior when no external score-prior files are supplied, so the shortlist commands are meaningful even before adding reranker score files.
