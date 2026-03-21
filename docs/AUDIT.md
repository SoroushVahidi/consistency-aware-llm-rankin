# Repository Audit — consistency-aware-llm-rankin

> **Full systematic audit** of every file, module, pipeline, dataset, and
> output in this repository.  Use this document as a complete reference for
> understanding and reproducing all experiments without additional help.

---

## 1. REPOSITORY OVERVIEW

### Purpose

This is a **PhD research repository** that investigates **consistency-aware
retrieval and ranking in LLM-powered systems**.  The core insight is that
large language models, when asked to compare pairs of documents or answers
("Is A better than B?"), frequently produce *cyclically inconsistent*
preferences — e.g. A > B, B > C, yet C > A.  This repository studies:

1. How frequently such cycles arise in pairwise preference graphs.
2. Whether graph-theoretic cycle repair (Minimum Weighted Feedback Arc Set,
   **MWFAS**) produces higher-quality rankings than naïve baselines.
3. How the repaired ranking compares to score-sum, Borda count, PageRank,
   topological sort, and hybrid methods across controlled (synthetic) and
   real retrieval benchmarks.

### Problem Solved

Given a set of items V = {v₁, …, vₙ} and a weighted directed graph
G = (V, E, w) where edge (vᵢ → vⱼ, wᵢⱼ) encodes "item i is preferred over
item j with confidence wᵢⱼ":

- **Detect cycles** — identify inconsistencies in the preference graph.
- **Remove a minimum-weight set of edges** (MWFAS) to produce a DAG.
- **Rank items** via topological ordering of the resulting DAG.
- **Evaluate** ranking quality against a ground truth.

### Project Type

Research prototype / benchmark suite.  No production deployment component.

### Main Contributions

| Contribution | Location |
|---|---|
| Greedy MWFAS heuristic | `src/consistency_ranker/greedy_fas.py` |
| Synthetic controlled experiments | `scripts/run_synthetic.py` |
| Real-data pipeline (BEIR, HotpotQA, BRIGHT) | `scripts/run_real_experiment.py` |
| Multi-ranker vote aggregation | `scripts/build_votes_file.py` |
| Hybrid graph+score ranking methods | `scripts/run_real_experiment.py` |
| Bootstrapped statistical significance testing | `scripts/bootstrap_method_deltas.py` |
| Wall-clock timing instrumentation | `src/consistency_ranker/utils/timing.py` |

---

## 2. DIRECTORY STRUCTURE

```
consistency-aware-llm-rankin/
├── src/
│   └── consistency_ranker/           # Installable Python package (pip install -e .)
│       ├── __init__.py               # Package init; exposes __version__
│       ├── synthetic_data.py         # Item generation with latent quality scores
│       ├── pairwise_prefs.py         # Noisy pairwise preference generation
│       ├── graph_construction.py     # Build NetworkX DiGraph from preferences
│       ├── cycle_detection.py        # Cycle detection / enumeration utilities
│       ├── baseline_ranking.py       # Score-sum, Borda, topological, PageRank
│       ├── greedy_fas.py             # Greedy MWFAS heuristic (core algorithm)
│       ├── mwfas_solver.py           # Solver interface (greedy + ILP stub)
│       ├── evaluation.py             # Kendall τ, n_violations, pairwise inconsistency
│       ├── data_loader.py            # Generic JSONL/CSV/TXT file I/O utilities
│       ├── data/
│       │   ├── __init__.py
│       │   ├── schema.py             # Shared dataclasses: Query, Document, QrelEntry,
│       │   │                         #   CandidateRanking, PairwisePreference
│       │   ├── dataset_registry.py   # DatasetConfig registry (scidocs, fiqa, hotpotqa, bright)
│       │   ├── beir_loader.py        # BEIR corpus/queries/qrels loader + HF downloader
│       │   ├── hotpotqa_loader.py    # HotpotQA multi-hop QA loader
│       │   ├── bright_loader.py      # BRIGHT reasoning-intensive retrieval loader
│       │   ├── unified_loader.py     # preferences_from_qrels() + load_dataset_splits()
│       │   └── query_ids.py          # eligible_query_ids(), save/load query-id files
│       └── utils/
│           ├── __init__.py
│           └── timing.py             # Timer context manager, timed() decorator,
│                                     #   TimingAccumulator with CSV/JSON export
├── tests/                            # pytest test suite (149 tests, all passing)
│   ├── __init__.py
│   ├── test_baseline_ranking.py
│   ├── test_bootstrap_method_deltas.py
│   ├── test_bright_loader.py
│   ├── test_cycle_detection.py
│   ├── test_data_pairwise.py
│   ├── test_data_registry.py
│   ├── test_data_schema.py
│   ├── test_evaluation.py
│   ├── test_external_preference_generation.py
│   ├── test_greedy_fas.py
│   ├── test_real_experiment_modes.py
│   └── test_timing.py
├── scripts/                          # Runnable CLI entry points
│   ├── __init__.py                   # Makes scripts/ a package (enables imports in tests)
│   ├── run_synthetic.py              # End-to-end synthetic experiment
│   ├── run_real_experiment.py        # Real-data experiment (2087 lines)
│   ├── download_datasets.py          # Download from HuggingFace
│   ├── prepare_datasets.py           # Convert raw data to unified JSONL
│   ├── generate_score_file.py        # Score documents with BM25/TF-IDF/MiniLM
│   ├── build_votes_file.py           # Aggregate multi-ranker votes to pairwise edges
│   ├── bootstrap_method_deltas.py    # Bootstrap confidence intervals for method comparisons
│   └── plot_timings.py               # Generate timing plots from saved JSON files
├── data/
│   ├── raw/                          # Raw downloaded files (populated by download_datasets.py)
│   │   ├── beir/scidocs/             # BEIR SciDocs corpus/queries/qrels JSONL
│   │   ├── beir/fiqa/                # BEIR FiQA corpus/queries/qrels JSONL
│   │   ├── hotpotqa/                 # HotpotQA JSONL
│   │   └── bright/                   # BRIGHT JSONL (or README with manual instructions)
│   └── processed/                    # Normalised JSONL (populated by prepare_datasets.py)
│       ├── beir/scidocs/
│       │   ├── queries.jsonl
│       │   ├── documents.jsonl
│       │   ├── qrels.jsonl
│       │   └── pairwise/preferences.jsonl
│       ├── beir/fiqa/  (same layout)
│       ├── hotpotqa/   (same layout)
│       └── bright/     (same layout)
├── outputs/                          # Experiment results (written at runtime)
│   ├── synthetic_results.json
│   ├── <dataset>_per_query.csv
│   ├── <dataset>_summary.csv
│   ├── real_signal/<dataset>/        # Multi-ranker vote experiment outputs
│   │   ├── scores_bm25.jsonl
│   │   ├── scores_tfidf.jsonl
│   │   ├── scores_minilm.jsonl
│   │   ├── votes.jsonl
│   │   └── query_ids.txt
│   ├── timings/
│   │   ├── synthetic_timings.csv
│   │   ├── synthetic_timings.json
│   │   └── <dataset>_timings.*
│   └── plots/
│       ├── runtime_by_stage.png
│       ├── runtime_breakdown_pie.png
│       ├── runtime_by_method.png
│       └── runtime_vs_n_items.png
├── docs/                             # Extended documentation (this file lives here)
│   └── AUDIT.md                      # ← you are here
├── notebooks/                        # Jupyter notebooks (placeholder; no .ipynb files yet)
├── pyproject.toml                    # Build system, project metadata, ruff / pytest config
├── requirements.txt                  # Pinned dependency list
├── README.md                         # User-facing documentation
├── TODO.md                           # Living task list
└── LICENSE                           # MIT licence
```

### Summary

| Category | Paths |
|---|---|
| Source code | `src/consistency_ranker/` |
| Scripts (CLI) | `scripts/` |
| Tests | `tests/` |
| Configuration | `pyproject.toml`, `requirements.txt` |
| Raw datasets | `data/raw/` |
| Processed datasets | `data/processed/` |
| Outputs / results | `outputs/` |
| Logs / timing | `outputs/timings/` |
| Plots | `outputs/plots/` |

---

## 3. CODEBASE ANALYSIS

### Package: `consistency_ranker`

Installed with `pip install -e .`; importable as `import consistency_ranker`.

---

#### `synthetic_data.py`

Generates synthetic ranked item sets for controlled experiments.

| Symbol | Role |
|---|---|
| `SyntheticItem` | Dataclass: `item_id: str`, `quality: float`, `metadata: dict` |
| `generate_items(n, seed, id_prefix)` | Returns `n` items with uniform-random quality scores |
| `ground_truth_ranking(items)` | Sorts items by descending quality → ground-truth ranking |
| `quality_map(items)` | `{item_id → quality}` lookup dict |

**Entry point**: called from `scripts/run_synthetic.py`.

---

#### `pairwise_prefs.py`

Generates (possibly noisy) pairwise preference observations.

| Symbol | Role |
|---|---|
| `Preference` | NamedTuple: `winner: str`, `loser: str`, `weight: float` |
| `generate_preferences(quality_map, noise, weight_scheme, seed)` | All pairs (i, j) → noisy preference; `noise` ∈ [0,1) is flip probability |
| `preferences_to_dict(preferences)` | Converts list of `Preference` to `{(winner, loser): weight}` |

**Weight schemes**: `"uniform"` (all 1.0) or `"margin"` (absolute quality difference).

---

#### `graph_construction.py`

Builds a `networkx.DiGraph` from pairwise preferences.

| Symbol | Role |
|---|---|
| `build_graph(preferences, aggregation)` | Aggregates repeated edges; default aggregation: `"sum"` |
| `build_graph_from_dict(edge_weight_dict)` | Builds graph from `{(u,v): weight}` |
| `graph_summary(graph)` | Returns `{n_nodes, n_edges, is_dag, total_weight, n_sccs}` |

**Aggregation options**: `"sum"` (default), `"mean"`, `"max"`, or any `list[float] → float` callable.

---

#### `cycle_detection.py`

Utilities for detecting and characterising cycles.

| Symbol | Role |
|---|---|
| `has_cycle(graph)` | Fast `bool` check via `nx.is_directed_acyclic_graph` |
| `find_simple_cycles(graph)` | Johnson's algorithm — all elementary cycles (exponential worst-case) |
| `count_cycles(graph)` | Count of simple cycles |
| `nodes_in_cycles(graph)` | Set of node ids in at least one cycle |
| `cycle_edge_set(graph)` | Set of `(u,v)` edges in at least one cycle |
| `cycle_summary(graph)` | `{n_cycles, n_nodes_in_cycles, n_edges_in_cycles}` |

⚠️ `find_simple_cycles` is exponential; avoid on graphs with n > ~30.
The `run_synthetic.py` pipeline uses SCC counting as a proxy instead.

---

#### `baseline_ranking.py`

Simple ranking baselines (all work on cyclic graphs except `topological_ranking`).

| Symbol | Role |
|---|---|
| `score_sum_ranking(graph)` | Sum of outgoing edge weights per node; descending sort |
| `borda_ranking(graph)` | Out-degree count per node; descending sort |
| `topological_ranking(graph)` | `nx.topological_sort` — requires DAG |
| `pagerank_ranking(graph, alpha, max_iter, tol)` | PageRank on reversed graph; descending score sort |

---

#### `greedy_fas.py` — Core Algorithm

Greedy MWFAS heuristic: iteratively find a cycle, remove the minimum-weight
edge in that cycle, repeat until acyclic.

| Symbol | Role |
|---|---|
| `greedy_fas(graph)` | Returns `(dag, removed_edges)`; does **not** modify input graph |
| `greedy_fas_total_weight(removed_edges)` | Scalar sum of removed edge weights |

**Complexity**: O(C · (n + e)) where C ≤ e is the number of removal iterations.
For dense graphs (e ≈ n²) this becomes O(n⁴) — dominant bottleneck for n > 30.

---

#### `mwfas_solver.py`

Unified solver interface.

| Symbol | Role |
|---|---|
| `solve(graph, method)` | Dispatches to `greedy_fas` (`method="greedy"`) or ILP stub (`method="ilp"`) |
| `available_methods()` | Returns `["greedy"]`; adds `"ilp"` if `pulp` is installed |

The `"ilp"` method raises `NotImplementedError` — stub for future work.

---

#### `evaluation.py`

Ranking quality and consistency metrics.

| Symbol | Role |
|---|---|
| `kendall_tau(ranking, reference)` | Kendall τ ∈ [-1, +1]; pure-Python O(n²) |
| `ranking_agreement(ranking, reference)` | `(τ + 1) / 2` ∈ [0, 1] |
| `n_violations(ranking, reference)` | Count of discordant pairs |
| `pairwise_inconsistency_count(graph, reference_ranking)` | Count graph edges that contradict the reference ranking |

---

#### `data_loader.py`

Generic file I/O utilities.

| Symbol | Role |
|---|---|
| `load_jsonl(path)` | Reads JSON-lines file → `list[dict]` |
| `load_csv(path, id_col)` | Reads CSV → `list[dict]` |
| `load_txt(path)` | Reads plain-text → `list[str]` |
| `save_jsonl(records, path)` | Writes `list[dict]` to JSONL |

---

#### `data/schema.py`

Shared normalised data types.

| Dataclass | Fields |
|---|---|
| `Query` | `query_id`, `text`, `metadata` |
| `Document` | `doc_id`, `text`, `title`, `metadata` |
| `QrelEntry` | `query_id`, `doc_id`, `relevance` |
| `CandidateRanking` | `query_id`, `ranked_doc_ids`, `scores` |
| `PairwisePreference` | `query_id`, `winner_doc_id`, `loser_doc_id`, `weight` |

All dataclasses provide `.to_dict()` and `.from_dict()` for JSONL serialisation.

---

#### `data/dataset_registry.py`

Central registry mapping short names to `DatasetConfig` objects.

| Symbol | Role |
|---|---|
| `DatasetConfig` | Dataclass: name, HF ids, paths, top_k, max_queries, seed, loader_type |
| `REGISTRY` | `{"scidocs": …, "fiqa": …, "hotpotqa": …, "bright": …}` |
| `DATASET_NAMES` | `["scidocs", "fiqa", "hotpotqa", "bright"]` |
| `get_config(name)` | Returns `DatasetConfig`; raises `KeyError` for unknown name |

Paths are resolved relative to `pyproject.toml` (repo root marker).

---

#### `data/beir_loader.py`

Loads BEIR-format datasets (SciDocs, FiQA) from local JSONL files or HF.

| Symbol | Role |
|---|---|
| `load_queries_from_jsonl(path)` | Reads `queries.jsonl` → `list[Query]` |
| `load_documents_from_jsonl(path)` | Reads `documents.jsonl` → `list[Document]` |
| `load_qrels_from_jsonl(path)` | Reads `qrels.jsonl` → `list[QrelEntry]` |
| `download_beir_dataset(cfg, cache_dir, split)` | Downloads via HF `datasets` library |
| `write_jsonl(records, path)` | Writes any list to JSONL |

---

#### `data/hotpotqa_loader.py`

Loads HotpotQA multi-hop QA dataset.

| Symbol | Role |
|---|---|
| `download_hotpotqa(cfg, cache_dir)` | Downloads `fullwiki` split from HF |
| `load_queries_from_jsonl` / `load_documents_from_jsonl` / `load_qrels_from_jsonl` | Same signatures as BEIR loader |

---

#### `data/bright_loader.py`

Loads BRIGHT reasoning-intensive retrieval dataset.  Most complex loader.

| Symbol | Role |
|---|---|
| `BrightNotAvailableError` / `BrightSchemaError` | Custom exceptions |
| `list_available_bright_tasks()` | Returns tuple of valid task/config names |
| `download_bright(cfg, bright_task, cache_dir, max_examples)` | Downloads from HF; writes manual README on failure |
| `load_raw_bright_splits(raw_path)` | Loads from already-downloaded JSONL |
| `normalize_query_record` / `normalize_document_record` / `normalize_qrel_record` | Key-alias normalisation (many field variants accepted) |
| `_parse_example_row(row)` | Parses one BRIGHT example into Query + Documents + QrelEntries |

---

#### `data/unified_loader.py`

High-level interface used by experiment scripts.

| Symbol | Role |
|---|---|
| `load_dataset_splits(name_or_config)` | Loads `(queries, documents, qrels)` from processed JSONL |
| `preferences_from_qrels(qrels, top_k, max_queries, seed, weight_scheme)` | Derives `PairwisePreference` list from relevance grades |
| `save_pairwise_preferences(preferences, output_dir, filename)` | Writes preferences JSONL |
| `load_pairwise_preferences(path)` | Reads preferences JSONL |

`preferences_from_qrels`: for each query, generates all (a > b) pairs where
`rel(a) > rel(b)`.  Skips equal-relevance pairs.  Supports `"grade_diff"` and
`"binary"` weight schemes.

---

#### `data/query_ids.py`

Utilities for controlling which queries are processed in an experiment.

| Symbol | Role |
|---|---|
| `has_usable_eval_labels(qrels_for_query)` | Returns `True` if ≥2 docs with distinct grades |
| `eligible_query_ids(qrels)` | Filters to queries with usable labels |
| `sample_query_ids(qrels, n, seed)` | Randomly samples eligible query ids |
| `load_query_ids_file(path)` | Reads a `.txt` file of query ids |
| `save_query_ids_file(query_ids, path)` | Writes a `.txt` file of query ids |

---

#### `utils/timing.py`

Wall-clock performance instrumentation.

| Symbol | Role |
|---|---|
| `Timer(name, accumulator)` | Context manager; records elapsed time |
| `timed(name, accumulator)` | Function decorator; wraps any callable |
| `TimingAccumulator` | Collects all timings; computes mean/median/max; exports CSV/JSON |

`TimingAccumulator` methods: `record`, `all_timings`, `total`, `mean_time`,
`median_time`, `max_time`, `grand_total`, `set_metadata`, `summary_rows`,
`print_summary`, `save_csv`, `save_json`.

---

### Execution Flow (Tracing)

#### Synthetic experiment

```
generate_items(n, seed)
  └─→ quality_map(items)
       └─→ generate_preferences(qmap, noise, weight_scheme, seed)
            └─→ build_graph(prefs)
                 ├─→ has_cycle(graph)
                 ├─→ score_sum_ranking(graph)
                 ├─→ borda_ranking(graph)
                 ├─→ greedy_fas(graph) → (dag, removed_edges)
                 │    └─→ topological_ranking(dag)
                 └─→ kendall_tau(*, ground_truth_ranking)
                      └─→ save results to outputs/synthetic_results.json
```

#### Real-data experiment

```
load_dataset_splits(dataset)  [reads processed JSONL]
  └─→ for each query:
       ├─→ _build_query_preferences(...)  [source: qrels | qrels_flip | score_file | votes_file]
       ├─→ build_graph(prefs)
       ├─→ greedy_fas(graph) → dag
       ├─→ score_sum / borda / pagerank / topological / weighted_balance /
       │   copeland / score_augmented_topo / hybrid_rrf_* rankings
       └─→ _ndcg_at_k, _map_at_k, _precision_recall_at_k, _pairwise_accuracy
            └─→ save per_query.csv, summary.csv, timings, plots
```

---

## 4. EXPERIMENT PIPELINE

### Experiment 1 — Synthetic (`scripts/run_synthetic.py`)

**Purpose**: Controlled experiment with known ground truth; tests how well each
ranking method recovers the true latent quality ordering as noise increases.

**Usage**:
```bash
python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42
python scripts/run_synthetic.py --n-items 50 --noise 0.1 --save-timings --profile
```

**Parameters**:

| Flag | Default | Description |
|---|---|---|
| `--n-items` | 20 | Number of synthetic items |
| `--noise` | 0.2 | Edge-flip probability [0, 1) |
| `--seed` | 42 | Random seed |
| `--weight-scheme` | `margin` | `uniform` or `margin` |
| `--output-dir` | `outputs/` | Where to write results |
| `--save-timings` | False | Write per-stage timing CSV/JSON |
| `--profile` | False | Print timing summary + save timings |

**Outputs**: `outputs/synthetic_results.json`, optionally
`outputs/timings/synthetic_timings.{csv,json}`.

**Evaluation metrics**: Kendall τ, pairwise violation count, pairwise
inconsistency count (original graph vs. repaired DAG).

---

### Experiment 2 — Real Data (`scripts/run_real_experiment.py`)

**Purpose**: Evaluates ranking methods on real IR benchmarks using four
preference sources.

**Usage**:
```bash
# Baseline (label-derived preferences)
python scripts/run_real_experiment.py --dataset scidocs \
    --max-queries 50 --top-k 20 --save-timings --profile

# Stress test (synthetic edge flips)
python scripts/run_real_experiment.py --dataset scidocs \
    --preference-source qrels_flip --flip-prob 0.15 \
    --max-queries 50 --top-k 20

# Multi-ranker vote aggregation (main real-signal experiment)
python scripts/run_real_experiment.py --dataset scidocs \
    --preference-source votes_file \
    --pairwise-file outputs/real_signal/scidocs/votes.jsonl \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --score-prior-files \
        outputs/real_signal/scidocs/scores_bm25.jsonl \
        outputs/real_signal/scidocs/scores_tfidf.jsonl \
        outputs/real_signal/scidocs/scores_minilm.jsonl \
    --max-queries 50 --top-k 20 --save-timings --profile --no-plots
```

**Preference sources**:

| Source | Description |
|---|---|
| `qrels` | Label-derived preferences (typically acyclic, weak baseline) |
| `qrels_flip` | Label-derived + random flips (synthetic stress test) |
| `score_file` | Single-ranker score file (usually near-transitive) |
| `llm_pairwise_file` | External LLM pairwise judgements |
| `votes_file` | Aggregated multi-ranker votes **(main real-signal path)** |

**Methods evaluated**:

| Method | Description |
|---|---|
| `score_sum` | Sum of outgoing edge weights |
| `borda` | Out-degree count |
| `pagerank` | PageRank on reversed graph |
| `greedy_fas_topological` | Greedy MWFAS + topological sort |
| `greedy_fas_weighted_balance` | Greedy MWFAS + weighted out-minus-in score sort |
| `greedy_fas_copeland` | Greedy MWFAS + Copeland score sort |
| `greedy_fas_score_augmented_topological` | Greedy MWFAS + score-augmented topological |
| `hybrid_rrf_fas_regularized` | RRF(balance, score_prior, α=0.2) |
| `hybrid_rrf_balance_a05` | RRF(balance, score_prior, α=0.5) |
| `hybrid_rrf_copeland_a03` | RRF(copeland, score_prior, α=0.3) |
| `hybrid_rrf_priority_topo_a03` | Priority topological + RRF prior |

**Evaluation metrics (all candidate-aligned)**:

| Metric | Description |
|---|---|
| `ndcg_at_k` | Normalised Discounted Cumulative Gain at k (primary) |
| `map_at_k` | Mean Average Precision at k |
| `precision_at_k` | Precision at k |
| `recall_at_k` | Recall at k |
| `pairwise_accuracy` | Fraction of document pairs ranked consistently with relevance labels |
| `kendall_tau` | Kendall τ vs. label-derived reference (secondary) |
| `backward_edge_weight` | Total weight of backward edges vs. predicted ranking |
| `pairwise_inconsistency` | Count of graph edges contradicting the reference |

**Outputs**: `<dataset>_per_query.csv`, `<dataset>_summary.csv`,
`timings/<dataset>_timings.{csv,json}`, optionally plots.

---

### Experiment 3 — Multi-Ranker Vote Aggregation

Uses three sub-scripts to build pairwise vote files from multiple rankers.

#### Step 1: Generate score files

```bash
python scripts/generate_score_file.py --dataset scidocs --ranker bm25 \
    --max-queries 50 --top-n 50 --seed 42 \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --output outputs/real_signal/scidocs/scores_bm25.jsonl
```

Supported rankers: `bm25`, `tfidf`, `minilm` (MiniLM sentence transformer).

Output format per line:
```json
{"query_id": "q1", "doc_id": "d1", "score": 1.23}
```

#### Step 2: Build votes file

```bash
python scripts/build_votes_file.py --dataset scidocs \
    --score-files scores_bm25.jsonl scores_tfidf.jsonl scores_minilm.jsonl \
    --top-k 20 --vote-weight-scheme margin --min-vote-margin 0.05 \
    --abstain-missing --min-support 2 --min-aggregate-margin 0.1 \
    --output outputs/real_signal/scidocs/votes.jsonl
```

Output format per line:
```json
{"query_id": "q1", "winner_doc_id": "d1", "loser_doc_id": "d2", "weight": 0.8, "voter": "bm25"}
```

#### Step 3: Run real experiment with `votes_file` source

(See Experiment 2 above.)

---

### Experiment 4 — Bootstrap Significance Testing

```bash
python scripts/bootstrap_method_deltas.py \
    --per-query-csv outputs/scidocs_per_query.csv \
    --metric ndcg_at_k \
    --method-a hybrid_rrf_fas_regularized \
    --method-b greedy_fas_topological \
    --n-bootstrap 2000 --seed 42 \
    --output-json outputs/bootstrap_ci.json \
    --output-csv outputs/bootstrap_ci.csv
```

Computes bootstrap confidence intervals for the pairwise metric delta between
two methods over shared queries.

---

### Timing/Profiling

```bash
python scripts/run_synthetic.py --n-items 50 --save-timings --profile

# Scale sweep
for n in 10 20 50 100; do
    python scripts/run_synthetic.py --n-items $n --save-timings \
        --output-dir outputs/scale_$n
done

# Plot results
python scripts/plot_timings.py --input outputs/timings/synthetic_timings.json
python scripts/plot_timings.py \
    --scale-dirs outputs/scale_10 outputs/scale_20 outputs/scale_50 outputs/scale_100
```

---

## 5. DATASETS

### Dataset Summary

| Name | Short ID | Loader Type | HF Source | Description |
|---|---|---|---|---|
| BEIR / SciDocs | `scidocs` | `beir` | `BeIR/scidocs` + `BeIR/scidocs-qrels` | Scientific document retrieval |
| BEIR / FiQA-2018 | `fiqa` | `beir` | `BeIR/fiqa` + `BeIR/fiqa-qrels` | Financial opinion QA |
| HotpotQA | `hotpotqa` | `hotpotqa` | `hotpot_qa` (fullwiki) | Multi-hop Wikipedia QA |
| BRIGHT | `bright` | `bright` | `xlangai/BRIGHT` | Reasoning-intensive retrieval |

### Location in Repo

```
data/
├── raw/
│   ├── beir/scidocs/   # Raw downloaded JSONL (queries, corpus, qrels)
│   ├── beir/fiqa/
│   ├── hotpotqa/
│   └── bright/         # May contain README.md if manual download required
└── processed/
    ├── beir/scidocs/
    │   ├── queries.jsonl         # {"query_id": "...", "text": "..."}
    │   ├── documents.jsonl       # {"doc_id": "...", "text": "...", "title": "..."}
    │   ├── qrels.jsonl           # {"query_id": "...", "doc_id": "...", "relevance": 0|1}
    │   └── pairwise/
    │       └── preferences.jsonl # {"query_id":…, "winner_doc_id":…, "loser_doc_id":…, "weight":…}
    ├── beir/fiqa/      (same layout)
    ├── hotpotqa/       (same layout)
    └── bright/         (same layout)
```

### Data Formats

All data is stored as **JSON Lines** (`.jsonl`): one JSON object per line, no
outer array.

**queries.jsonl** (one per line):
```json
{"query_id": "1", "text": "What is ...", "metadata": {}}
```

**documents.jsonl** (one per line):
```json
{"doc_id": "2345", "text": "...", "title": "...", "metadata": {}}
```

**qrels.jsonl** (one per line):
```json
{"query_id": "1", "doc_id": "2345", "relevance": 1}
```

**preferences.jsonl** (one per line):
```json
{"query_id": "1", "winner_doc_id": "2345", "loser_doc_id": "6789", "weight": 1.0}
```

### Preprocessing Pipeline

1. `download_datasets.py` — downloads from HuggingFace, writes raw JSONL.
2. `prepare_datasets.py` — normalises field names, applies `top_k` / `max_queries`
   limits, generates `preferences.jsonl` via `preferences_from_qrels()`.

### Data Types

- **Real data**: BEIR (SciDocs, FiQA), HotpotQA, BRIGHT — from public HuggingFace sources.
- **Synthetic data**: generated in-memory by `generate_items()` + `generate_preferences()`.

### Default Configuration

| Dataset | `top_k` | `max_queries` | `seed` |
|---|---|---|---|
| scidocs | 100 | 500 | 42 |
| fiqa | 100 | 500 | 42 |
| hotpotqa | 10 | 500 | 42 |
| bright | 100 | 500 | 42 |

---

## 6. INPUT / OUTPUT CONTRACTS

### Inputs Required to Run Experiments

#### Synthetic experiment

No external files required.  Everything is generated in-memory.

#### Real-data experiments

| File | Required For | Format |
|---|---|---|
| `data/processed/<dataset>/queries.jsonl` | All real-data modes | `{query_id, text}` per line |
| `data/processed/<dataset>/documents.jsonl` | All real-data modes | `{doc_id, text, title}` per line |
| `data/processed/<dataset>/qrels.jsonl` | All real-data modes | `{query_id, doc_id, relevance}` per line |
| `outputs/.../scores_*.jsonl` | `score_file` / `votes_file` modes | `{query_id, doc_id, score}` per line |
| `outputs/.../votes.jsonl` | `votes_file` mode | `{query_id, winner_doc_id, loser_doc_id, weight, voter}` per line |
| `outputs/.../query_ids.txt` | Optional; reproducible query selection | One query id per line |

### Outputs Produced

#### Synthetic experiment output

**File**: `outputs/synthetic_results.json`

```json
{
  "config": {"n_items": 20, "noise": 0.2, "seed": 42, "weight_scheme": "margin"},
  "ground_truth_ranking": ["item_07", "item_13", ...],
  "graph_summary": {"n_nodes": 20, "n_edges": 190, "is_dag": false, "total_weight": ..., "n_sccs": ...},
  "cycle_summary": {"has_cycle": true, "n_sccs": ..., "n_non_trivial_sccs": ..., "note": "..."},
  "rankings": {
    "score_sum": [...],
    "borda": [...],
    "greedy_fas_topological": [...]
  },
  "evaluation": {
    "kendall_tau": {"score_sum": 0.73, "borda": 0.71, "greedy_fas_topological": 0.78},
    "n_violations": {...},
    "pairwise_inconsistency_count": {"original_graph": 12, "after_fas_dag": 0}
  },
  "fas": {
    "n_removed_edges": 5,
    "total_removed_weight": 0.23,
    "removed_edges": [["c", "a", 0.05], ...]
  },
  "timings": {"graph_construction": {"total_s": 0.001, "mean_s": 0.001}, ...}
}
```

#### Real-data experiment outputs

**File**: `outputs/<dataset>_per_query.csv`

Columns: `query_id, method, n_nodes, n_edges, density, n_sccs, largest_scc,
is_cyclic, backward_edge_weight, pairwise_inconsistency, kendall_tau,
kendall_tau_legacy, ndcg_at_k, map_at_k, precision_at_k, recall_at_k,
pairwise_accuracy, fas_weight_removed, graph_ref_bew_pre, graph_ref_bew_post,
graph_ref_pic_pre, graph_ref_pic_post, runtime_total_s`

**File**: `outputs/<dataset>_summary.csv`

Aggregate statistics (mean / median / max / min) per method across all queries.
Columns: `method, n_queries, bew_mean, bew_median, pic_mean, tau_mean,
ndcg_mean, map_mean, precision_at_k_mean, recall_at_k_mean,
pairwise_accuracy_mean, runtime_mean_s, cyclic_pct, ...`

**File**: `outputs/timings/<dataset>_timings.csv` / `.json`

CSV columns: `stage, n_calls, total_s, mean_s, median_s, max_s`.
JSON includes the same plus `raw` per-call values and `metadata`.

---

## 7. CONFIGURATION & REPRODUCIBILITY

### Configuration Locations

| Item | Location |
|---|---|
| Python package metadata | `pyproject.toml` — `[project]` |
| Build system | `pyproject.toml` — `[build-system]` |
| pytest settings | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Ruff linter | `pyproject.toml` — `[tool.ruff]` |
| Dependencies (pinned) | `requirements.txt` |
| Dataset paths and defaults | `src/consistency_ranker/data/dataset_registry.py` |
| Per-experiment parameters | CLI flags on `run_synthetic.py` / `run_real_experiment.py` |

### Reproducing the Synthetic Experiment

```bash
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42
# → outputs/synthetic_results.json
```

### Reproducing the Real-Data Experiment (Full)

```bash
# 1. Install dataset dependencies (already in requirements.txt)
# 2. Download
python scripts/download_datasets.py --dataset scidocs
# 3. Prepare (normalise to JSONL + generate preferences)
python scripts/prepare_datasets.py --dataset scidocs
# 4. Generate score files from multiple rankers
python scripts/generate_score_file.py --dataset scidocs --ranker bm25 \
    --max-queries 50 --top-n 50 --seed 42 \
    --output outputs/real_signal/scidocs/scores_bm25.jsonl
python scripts/generate_score_file.py --dataset scidocs --ranker tfidf \
    --max-queries 50 --top-n 50 --seed 42 \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --output outputs/real_signal/scidocs/scores_tfidf.jsonl
python scripts/generate_score_file.py --dataset scidocs --ranker minilm \
    --max-queries 50 --top-n 50 --seed 42 \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --output outputs/real_signal/scidocs/scores_minilm.jsonl
# 5. Build votes file
python scripts/build_votes_file.py --dataset scidocs \
    --score-files \
        outputs/real_signal/scidocs/scores_bm25.jsonl \
        outputs/real_signal/scidocs/scores_tfidf.jsonl \
        outputs/real_signal/scidocs/scores_minilm.jsonl \
    --top-k 20 --vote-weight-scheme margin --min-vote-margin 0.05 \
    --abstain-missing --min-support 2 --min-aggregate-margin 0.1 \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --output outputs/real_signal/scidocs/votes.jsonl
# 6. Run experiment
python scripts/run_real_experiment.py --dataset scidocs \
    --preference-source votes_file \
    --pairwise-file outputs/real_signal/scidocs/votes.jsonl \
    --query-id-file outputs/real_signal/scidocs/query_ids.txt \
    --score-prior-files \
        outputs/real_signal/scidocs/scores_bm25.jsonl \
        outputs/real_signal/scidocs/scores_tfidf.jsonl \
        outputs/real_signal/scidocs/scores_minilm.jsonl \
    --max-queries 50 --top-k 20 --save-timings --profile --no-plots
```

### Hardcoded Assumptions

| Assumption | Location |
|---|---|
| Repo root detected via `pyproject.toml` marker | `dataset_registry.py:_find_repo_root()` |
| Minimum judged docs per query = 2 | `run_real_experiment.py:MIN_JUDGED_DOCS` |
| Default FAS safety valve: skip if edges > 5000 | `run_real_experiment.py:run_query()` |
| Default HF config for HotpotQA = `fullwiki` | `dataset_registry.py:REGISTRY["hotpotqa"]` |
| Minimum edge weight = 1e-6 | `pairwise_prefs.py:_MIN_EDGE_WEIGHT` |

---

## 8. DEPENDENCIES & ENVIRONMENT

### Python Version

Python **3.11+** (enforced in `pyproject.toml`).

### Core Dependencies

| Package | Version | Purpose |
|---|---|---|
| `networkx` | ≥3.2 | Graph construction, cycle detection, FAS, PageRank |
| `numpy` | ≥1.26 | Numerical operations |
| `scipy` | ≥1.11 | Statistical utilities (available, not yet used for Kendall τ — pure-Python implementation used) |
| `tqdm` | ≥4.66 | Progress bars in download/prepare scripts |
| `datasets` | ≥2.18 | HuggingFace dataset download |
| `huggingface-hub` | ≥0.21 | HF authentication / file download |
| `sentence-transformers` | ≥5.3.0 | MiniLM ranker in `generate_score_file.py` |
| `matplotlib` | ≥3.8 | Timing plots in `plot_timings.py` |
| `pandas` | ≥2.1 | CSV I/O in experiment scripts |

### Development Dependencies

| Package | Purpose |
|---|---|
| `pytest` ≥7.4 | Test runner |
| `pytest-cov` ≥4.1 | Coverage reporting |
| `ruff` ≥0.3 | Linting (E, F, W, I rules) |

### Optional Dependencies

| Package | Purpose |
|---|---|
| `jupyter` ≥1.0 | Notebook exploration (install separately) |
| `seaborn` ≥0.13 | Enhanced plots in notebooks |
| `pulp` | ILP-based exact MWFAS solver (stub; not yet implemented) |

### HPC / SLURM

No SLURM job scripts present.  The pipeline is designed for single-machine
execution.  For large-scale sweeps, manual parallelism (e.g., launching one
process per dataset) is needed.

### GPU / CPU

No GPU requirements.  All computation is graph-theoretic and CPU-only.
MiniLM sentence encoding (`generate_score_file.py --ranker minilm`) benefits
from a GPU but runs on CPU.

---

## 9. RESULTS & OUTPUTS

### Synthetic Results

**`outputs/synthetic_results.json`**

Contains the complete result of one run of `run_synthetic.py`.
Keys: `config`, `ground_truth_ranking`, `graph_summary`, `cycle_summary`,
`rankings` (score_sum / borda / greedy_fas_topological), `evaluation`
(kendall_tau, n_violations, pairwise_inconsistency_count), `fas`
(removed edges and their weights), `timings` (per-stage wall-clock times).

### Real-Data Results

**`outputs/<dataset>_per_query.csv`**

One row per (query, method) pair.  Used by `bootstrap_method_deltas.py`
to compute statistical significance of method differences.

**`outputs/<dataset>_summary.csv`**

One row per method.  Aggregate statistics (mean, median, max, min) for
all metrics.  This is the primary **leaderboard file**.

### Timing Files

**`outputs/timings/synthetic_timings.csv`**

Columns: `stage, n_calls, total_s, mean_s, median_s, max_s`.
Row per pipeline stage (e.g. `graph_construction`, `greedy_fas_solver`, etc.).

**`outputs/timings/synthetic_timings.json`**

Same content as CSV plus `raw` list of per-call elapsed times and `metadata`
dict (n_items, noise, seed, etc.).

### Timing Plots

**`outputs/plots/runtime_by_stage.png`** — Horizontal bar chart.

**`outputs/plots/runtime_breakdown_pie.png`** — Proportional breakdown.

**`outputs/plots/runtime_by_method.png`** — Per-method runtime comparison.

**`outputs/plots/runtime_vs_n_items.png`** — Scale-sweep line chart.

### Bootstrap CI Results

**`outputs/bootstrap_ci.json`** / **`outputs/bootstrap_ci.csv`**

One row per (method_a, method_b) pair.  Fields: `method_a`, `method_b`,
`n_paired_queries`, `observed_delta`, `ci_lower`, `ci_upper`, `p_value`.

---

## 10. ISSUES, RISKS, AND MISSING PIECES

### Missing / Incomplete Functionality

| Item | Location | Severity |
|---|---|---|
| ILP solver stub raises `NotImplementedError` | `mwfas_solver.py` | Medium — limits exact MWFAS |
| `scipy.stats.kendalltau` not used; pure-Python O(n²) loop | `evaluation.py` | Low — slow for n > 100 |
| Notebooks directory is empty | `notebooks/` | Low — no walkthrough notebooks |
| Docs directory empty before this audit | `docs/` | Low — fixed by this file |
| BRIGHT dataset may require manual download | `bright_loader.py` | Medium — blocks BRIGHT experiments without HF auth |
| No `__all__` in `data/__init__.py` | `src/consistency_ranker/data/__init__.py` | Low |

### Potential Bugs / Risks

| Issue | Location | Notes |
|---|---|---|
| `pagerank_ranking` reverses graph before PageRank but sorts descending; nodes with more wins get lower PageRank authority — semantically unusual. | `baseline_ranking.py:pagerank_ranking` | May need clarification in docstring |
| `greedy_fas` uses `copy.deepcopy` — expensive for repeated calls (e.g. 500 queries × 3 rankers) | `greedy_fas.py` | Noted as TODO in `greedy_fas.py` docstring; use `graph.copy()` for shallow copy |
| Full cycle enumeration (`find_simple_cycles`) is avoided in `run_synthetic.py` but exposed publicly; callers could accidentally call it on large graphs | `cycle_detection.py` | Warning in docstring present but no runtime guard |
| `score_sum_ranking` initialises all nodes to 0.0 but then uses `scores.get(u, 0.0)` which is redundant | `baseline_ranking.py` | Cosmetic inconsistency |
| `available_methods()` in `mwfas_solver.py` reports `"ilp"` if `pulp` is installed, even though the ILP backend raises `NotImplementedError` | `mwfas_solver.py` | Could mislead callers |

### Missing Documentation

| Item | Notes |
|---|---|
| No docstring for `data/__init__.py` | Minor |
| `run_real_experiment.py` is 2087 lines; complex internal functions lack high-level comments explaining the hybrid method design | Major |
| No architectural diagram | Useful for onboarding |
| `TODO.md` items are research TODOs but do not track engineering debt | Should distinguish |

### Inconsistencies in Pipeline

| Issue | Location |
|---|---|
| `scripts/run_synthetic.py` uses `sys.path.insert` to find the `src/` package; this could be avoided if the package is always installed with `pip install -e .` | `run_synthetic.py:line 28` |
| The `votes_file` format uses `winner_doc_id` / `loser_doc_id` (matching `PairwisePreference` schema) but also has a `voter` field that is not in the schema | `build_votes_file.py` |
| `prepare_datasets.py` and `download_datasets.py` are separate scripts; a combined `--download-and-prepare` mode would reduce friction | `scripts/` |

### Suggested Improvements

1. **Implement the ILP MWFAS solver** using `pulp` or `gurobipy` for exact solutions on small graphs (n ≤ 30).
2. **Replace pure-Python Kendall τ** with `scipy.stats.kendalltau` for 10–100× speedup at n > 100.
3. **Cache graph copies** in `greedy_fas`: use `graph.copy()` (shallow) instead of `copy.deepcopy`.
4. **Add a Jupyter notebook** demonstrating the synthetic experiment end-to-end with plots.
5. **Add SCC-based cycle count as a fast proxy** in `cycle_detection.py` for large graphs, guarded by size check.
6. **Fix `available_methods()`** to not advertise `"ilp"` until the ILP backend is implemented.
7. **Add integration test** that runs `run_synthetic.py` end-to-end with n=10 in a temp directory.

---

## 11. END-TO-END EXECUTION SUMMARY

### Step 1 — Data Preparation

```
download_datasets.py
  Uses HuggingFace `datasets` library to pull raw files
  Writes to data/raw/<dataset>/  (queries.jsonl, documents.jsonl, qrels.jsonl)

prepare_datasets.py
  Reads raw JSONL files via beir_loader / hotpotqa_loader / bright_loader
  Normalises field names to unified schema (Query, Document, QrelEntry)
  Limits to max_queries and top_k candidates
  Calls preferences_from_qrels() to generate pairwise preferences
  Writes to data/processed/<dataset>/:
    queries.jsonl, documents.jsonl, qrels.jsonl
    pairwise/preferences.jsonl
```

### Step 2 — Ranker Score Generation (for multi-ranker experiments)

```
generate_score_file.py
  Loads processed dataset splits via load_dataset_splits()
  Builds a sparse text index (BM25 / TF-IDF / MiniLM)
  For each query in the shared query-id file:
    Retrieves top-N scored documents
    Writes {query_id, doc_id, score} lines to scores_<ranker>.jsonl
  Saves query_ids.txt on first run

build_votes_file.py
  Reads multiple score files (one per ranker)
  For each query × each ordered doc pair:
    Counts how many rankers prefer doc_a over doc_b (and by how much)
    Applies filters: --min-vote-margin, --abstain-missing, --min-support,
      --min-aggregate-margin
    Assigns final directed edge weight (binary or margin)
  Writes {query_id, winner_doc_id, loser_doc_id, weight, voter} lines
  to votes.jsonl
```

### Step 3 — Experiment Run

```
run_real_experiment.py  (or run_synthetic.py for synthetic)
  Loads dataset splits from data/processed/
  Loads pairwise source file (votes.jsonl / scores.jsonl / in-memory qrels)
  For each sampled query:
    _build_query_preferences() → list[Preference]
      Sources: qrels | qrels_flip | score_file | llm_pairwise_file | votes_file
    build_graph(prefs) → nx.DiGraph with edge weights
    [Optionally: greedy_fas(graph) → (dag, removed_edges)]
    Apply all ranking methods to graph / dag
    Compute evaluation metrics for each method:
      _ndcg_at_k(), _map_at_k(), _precision_recall_at_k(), _pairwise_accuracy()
      _kendall_tau(), _backward_edge_weight(), _pairwise_inconsistency()
    Append one row per method to all_rows list
  Aggregate per_query rows → summary stats per method (_build_summary())
  Write outputs:
    <dataset>_per_query.csv
    <dataset>_summary.csv
    timings/<dataset>_timings.{csv,json}  [if --save-timings]
    plots/  [if matplotlib available and --no-plots not set]
```

### Step 4 — Statistical Analysis

```
bootstrap_method_deltas.py
  Reads <dataset>_per_query.csv
  For a specified (method_a, method_b) pair and metric:
    Extracts per-query metric values for both methods
    Computes observed delta = mean(method_a) - mean(method_b)
    Resamples query pairs with replacement N times (default 2000)
    Computes bootstrap CI and p-value for H₀: delta = 0
  Writes bootstrap_ci.json and bootstrap_ci.csv
```

### Step 5 — Plot and Inspect Results

```
plot_timings.py
  Reads timings JSON files from one or more output directories
  Generates:
    runtime_by_stage.png      (bar chart of stage totals)
    runtime_breakdown_pie.png (proportional breakdown)
    runtime_by_method.png     (per-method ranking runtime)
    runtime_vs_n_items.png    (scale-sweep line chart)
  Writes to outputs/plots/
```

### Summary of Artifacts

| Artifact | Where | What it Tells You |
|---|---|---|
| `outputs/synthetic_results.json` | After step 3 (synthetic) | Full ranking quality + FAS stats for one controlled run |
| `outputs/<ds>_per_query.csv` | After step 3 (real) | Per-query metric for every method — raw data for analysis |
| `outputs/<ds>_summary.csv` | After step 3 (real) | **Leaderboard** — aggregate method comparison |
| `outputs/bootstrap_ci.{json,csv}` | After step 4 | Statistical significance of method differences |
| `outputs/timings/*.{csv,json}` | After step 3 (with `--save-timings`) | Stage-by-stage runtime breakdown |
| `outputs/plots/*.png` | After step 5 | Visual runtime analysis |

---

*This audit was generated by systematic review of all source, script, test,
and configuration files in the repository.  All file paths and function names
are exact.*
