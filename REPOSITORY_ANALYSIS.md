# Repository Analysis: consistency-aware-llm-rankin

> Structured analysis for the "Consistency-Aware Ranking and Reasoning in AI Systems" research direction.

**Important note:** The `main` branch of this repository is an empty skeleton (only `README.md`, `LICENSE`, `.gitignore`). All substantive code lives on the `copilot/setup-python-research-repo` branch. This analysis covers the code on that branch, which is the only branch with implementation work.

---

## 1. High-Level Repository Summary

### What is this repo mainly about?

This repository implements a research framework for **consistency-aware ranking using pairwise preference graphs and feedback arc set (FAS) optimization**. The core idea:

- Items (documents, answers, etc.) are compared pairwise to produce preference judgments.
- These preferences form a weighted directed graph that may contain cycles (inconsistencies).
- The **Minimum Weighted Feedback Arc Set (MWFAS)** problem is solved to remove the minimum-weight set of cycle-forming edges, producing a DAG.
- A topological sort of the DAG yields a globally consistent ranking.
- The resulting ranking is evaluated against ground truth using Kendall τ and other metrics.

### Major subprojects / pipelines

| Pipeline | Description |
|----------|-------------|
| **Synthetic experiment** | End-to-end pipeline: generate items → noisy pairwise prefs → graph → FAS → rank → evaluate |
| **Real-data experiment** | Load BEIR/HotpotQA/BRIGHT datasets → derive pairwise prefs from qrels → graph → FAS → rank → evaluate per query |
| **Dataset download & preparation** | Scripts to download from HuggingFace and convert to unified JSONL format |
| **Timing & profiling** | Instrumented pipeline stages with CSV/JSON export and plotting |

### Research directions supported

1. Measuring inconsistency in pairwise preference graphs (cycle detection, SCC analysis)
2. Comparing ranking methods (score-sum, Borda, PageRank, greedy-FAS + topological sort)
3. Evaluating ranking quality under controlled noise levels (synthetic experiments)
4. Benchmarking on real retrieval datasets (BEIR SciDocs, BEIR FiQA, HotpotQA, BRIGHT)
5. Runtime profiling and scalability analysis

---

## 2. Code Inventory

### Core ranking / graph modules

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/graph_construction.py` | Builds `networkx.DiGraph` from pairwise preferences; supports sum/mean/max aggregation | **Mature** — clean API, well-documented |
| `src/consistency_ranker/cycle_detection.py` | Cycle detection: `has_cycle`, `find_simple_cycles` (Johnson's), `count_cycles`, `nodes_in_cycles`, `cycle_edge_set`, `cycle_summary` | **Mature** — complete, with complexity warnings |
| `src/consistency_ranker/greedy_fas.py` | Greedy MWFAS heuristic: iteratively find cycle, remove min-weight edge | **Mature** — functional, O(C·(n+e)) complexity documented |
| `src/consistency_ranker/mwfas_solver.py` | Unified solver interface dispatching to `greedy` or `ilp` (ILP is a **stub** — `NotImplementedError`) | **Partial** — ILP not implemented |
| `src/consistency_ranker/baseline_ranking.py` | Baselines: `score_sum_ranking`, `topological_ranking`, `borda_ranking`, `pagerank_ranking` | **Mature** — 4 methods implemented and working |
| `src/consistency_ranker/pairwise_prefs.py` | Generate noisy pairwise preferences from quality scores; supports `uniform` and `margin` weight schemes | **Mature** — clean, well-tested |
| `src/consistency_ranker/evaluation.py` | Metrics: `kendall_tau`, `ranking_agreement`, `n_violations`, `pairwise_inconsistency_count` | **Mature** but **incomplete** — missing NDCG, Spearman ρ, MRR |

### Data loading / preprocessing

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/data/schema.py` | Dataclasses: `Query`, `Document`, `QrelEntry`, `CandidateRanking`, `PairwisePreference` | **Mature** — clean schema with serialization |
| `src/consistency_ranker/data/dataset_registry.py` | Central registry of dataset configs (scidocs, fiqa, hotpotqa, bright) | **Mature** — extensible |
| `src/consistency_ranker/data/unified_loader.py` | `load_dataset_splits()`, `preferences_from_qrels()`, `save_pairwise_preferences()` | **Mature** — key integration point |
| `src/consistency_ranker/data/beir_loader.py` | BEIR dataset loader (HuggingFace download + local JSONL) | **Mature** |
| `src/consistency_ranker/data/hotpotqa_loader.py` | HotpotQA loader (fullwiki validation split) | **Mature** |
| `src/consistency_ranker/data/bright_loader.py` | BRIGHT loader with fallback to manual download instructions | **Mature** — handles failure gracefully |
| `src/consistency_ranker/data_loader.py` | Legacy generic file loader (JSONL, CSV, TXT) | **Mature** but **legacy** — superseded by `data/` subpackage |

### Synthetic data generation

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/synthetic_data.py` | `generate_items()`, `ground_truth_ranking()`, `quality_map()` | **Mature** — clean, tested |

### Experiment runners

| File | Description | Maturity |
|------|-------------|----------|
| `scripts/run_synthetic.py` | End-to-end synthetic experiment CLI (321 lines) | **Mature** — fully functional |
| `scripts/run_real_experiment.py` | Real-data experiment CLI with per-query loop (1024 lines) | **Mature** — comprehensive, includes plotting |
| `scripts/download_datasets.py` | Dataset download CLI | **Mature** |
| `scripts/prepare_datasets.py` | Dataset preparation CLI (raw → processed JSONL + pairwise) | **Mature** |

### Utilities / plotting / analysis

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/utils/timing.py` | `Timer`, `TimingAccumulator`, `@timed` decorator, CSV/JSON export | **Mature** — 381 lines, well-engineered |
| `scripts/plot_timings.py` | Timing visualization (bar charts, pie charts, scale sweep plots) | **Mature** — 302 lines |

### Tests

| File | Description | Maturity |
|------|-------------|----------|
| `tests/test_baseline_ranking.py` | Tests for all baseline ranking methods | **Mature** |
| `tests/test_cycle_detection.py` | Tests for cycle detection functions | **Mature** |
| `tests/test_evaluation.py` | Tests for evaluation metrics | **Mature** |
| `tests/test_greedy_fas.py` | Tests for greedy FAS heuristic | **Mature** |
| `tests/test_timing.py` | Tests for timing utilities | **Mature** |
| `tests/test_data_schema.py` | Tests for data schema classes | **Mature** |
| `tests/test_data_registry.py` | Tests for dataset registry | **Mature** |
| `tests/test_data_pairwise.py` | Tests for pairwise preference generation from qrels | **Mature** |

---

## 3. Existing Algorithms Already Implemented

### 3.1 Greedy MWFAS Heuristic

- **Method name:** Greedy Feedback Arc Set removal
- **Implemented in:** `src/consistency_ranker/greedy_fas.py` → `greedy_fas()`
- **Input:** `networkx.DiGraph` with `"weight"` edge attributes
- **Output:** `(dag: DiGraph, removed_edges: list[(u, v, weight)])`
- **Algorithm:** Iteratively finds a cycle via `nx.find_cycle`, removes the minimum-weight edge, repeats until DAG.
- **Complexity:** O(C · (n+e)) where C ≤ e
- **Reusable:** **Yes** — directly applicable to any pairwise preference graph

### 3.2 Score-Sum Ranking

- **Method name:** Score-sum (win aggregation)
- **Implemented in:** `src/consistency_ranker/baseline_ranking.py` → `score_sum_ranking()`
- **Input:** `networkx.DiGraph`
- **Output:** `list[str]` — node IDs sorted by total outgoing edge weight
- **Reusable:** **Yes**

### 3.3 Borda Count Ranking

- **Method name:** Borda count
- **Implemented in:** `src/consistency_ranker/baseline_ranking.py` → `borda_ranking()`
- **Input:** `networkx.DiGraph`
- **Output:** `list[str]` — node IDs sorted by out-degree
- **Reusable:** **Yes**

### 3.4 PageRank Ranking

- **Method name:** Weighted PageRank on reversed graph
- **Implemented in:** `src/consistency_ranker/baseline_ranking.py` → `pagerank_ranking()`
- **Input:** `networkx.DiGraph` with weights
- **Output:** `list[str]` — node IDs sorted by PageRank score
- **Reusable:** **Yes**

### 3.5 Topological Sort Ranking

- **Method name:** Topological sort
- **Implemented in:** `src/consistency_ranker/baseline_ranking.py` → `topological_ranking()`
- **Input:** `networkx.DiGraph` (must be a DAG)
- **Output:** `list[str]` — topological order
- **Reusable:** **Yes** — used after FAS to rank the repaired DAG

### 3.6 ILP-Based Exact MWFAS (Stub)

- **Method name:** ILP MWFAS solver
- **Implemented in:** `src/consistency_ranker/mwfas_solver.py` → `solve(method="ilp")`
- **Status:** **NOT IMPLEMENTED** — raises `NotImplementedError`
- **Reusable:** **No** — placeholder only

### 3.7 Pairwise Preference Generation (Synthetic)

- **Method name:** Noisy preference generation
- **Implemented in:** `src/consistency_ranker/pairwise_prefs.py` → `generate_preferences()`
- **Input:** `dict[str, float]` quality map, noise level, weight scheme
- **Output:** `list[Preference]` — (winner, loser, weight) triples
- **Reusable:** **Yes** — good for controlled experiments

### 3.8 Pairwise Preference Generation (From Qrels)

- **Method name:** Qrel-derived preferences
- **Implemented in:** `src/consistency_ranker/data/unified_loader.py` → `preferences_from_qrels()`
- **Input:** `list[QrelEntry]`, top_k, weight_scheme (`grade_diff` or `binary`)
- **Output:** `list[PairwisePreference]`
- **Reusable:** **Yes** — key bridge between retrieval labels and preference graphs

---

## 4. Dataset Inventory

### Configured Datasets

| Dataset | Short ID | HuggingFace Source | Loader Type | Data Present in Repo? |
|---------|----------|-------------------|-------------|----------------------|
| BEIR / SciDocs | `scidocs` | `BeIR/scidocs` + `BeIR/scidocs-qrels` | `beir` | **No** — `.gitkeep` placeholders only |
| BEIR / FiQA-2018 | `fiqa` | `BeIR/fiqa` + `BeIR/fiqa-qrels` | `beir` | **No** — `.gitkeep` placeholders only |
| HotpotQA | `hotpotqa` | `hotpot_qa` (fullwiki) | `hotpotqa` | **No** — `.gitkeep` placeholders only |
| BRIGHT | `bright` | `xlangai/BRIGHT` | `bright` | **No** — `.gitkeep` placeholders only |

### Data Directory Structure (placeholders only)

```
data/
├── raw/
│   ├── beir/scidocs/.gitkeep
│   ├── beir/fiqa/.gitkeep
│   ├── hotpotqa/.gitkeep
│   └── bright/.gitkeep
├── processed/
│   ├── beir/scidocs/pairwise/.gitkeep
│   ├── beir/fiqa/pairwise/.gitkeep
│   ├── hotpotqa/pairwise/.gitkeep
│   └── bright/pairwise/.gitkeep
```

### File Formats

- **Raw:** JSONL files (queries.jsonl, documents.jsonl, qrels.jsonl) downloaded from HuggingFace
- **Processed:** Unified JSONL format + `pairwise/preferences.jsonl`
- Schema defined in `src/consistency_ranker/data/schema.py`

### Benchmark Usage

- **BEIR:** SciDocs and FiQA benchmarks — standard IR evaluation
- **HotpotQA:** Multi-hop QA, treated as retrieval (supporting facts = relevant docs)
- **BRIGHT:** Reasoning-intensive retrieval (may require manual download)
- **DIMACS, connectome, sports:** NOT referenced anywhere in the code
- **MS-MARCO, TREC-DL:** Mentioned in `TODO.md` as future integration targets

---

## 5. Current Experiment Pipeline

### Main Entry Points

| Script | Purpose |
|--------|---------|
| `python scripts/run_synthetic.py` | Synthetic end-to-end experiment |
| `python scripts/run_real_experiment.py` | Real-data per-query experiment |
| `python scripts/download_datasets.py` | Download datasets from HuggingFace |
| `python scripts/prepare_datasets.py` | Convert raw data to unified format |
| `python scripts/plot_timings.py` | Generate timing visualization plots |

### Synthetic Experiment Flow

```
generate_items(n, seed)
    → generate_preferences(quality_map, noise, weight_scheme)
        → build_graph(preferences)
            → has_cycle(graph) + SCC analysis
                → score_sum_ranking(graph)
                → borda_ranking(graph)
                → greedy_fas(graph) → topological_ranking(dag)
                    → kendall_tau(ranking, ground_truth)
                    → n_violations(ranking, ground_truth)
                        → save results to outputs/synthetic_results.json
```

### Real-Data Experiment Flow

```
load_dataset_splits(dataset_name)
    → for each query:
        → preferences_from_qrels(qrels, top_k, weight_scheme)
            → build_graph(preferences)
                → greedy_fas(graph) → topological_ranking(dag)
                → score_sum_ranking(graph)
                → borda_ranking(graph)
                → pagerank_ranking(graph)
                    → kendall_tau(ranking, reference_ranking)
                    → backward_edge_weight(graph, ranking)
                    → pairwise_inconsistency(graph, ranking)
    → save per-query CSV, summary CSV, timing data, plots
```

### Config Files

- `pyproject.toml` — package metadata, dependencies, pytest config, ruff config
- `requirements.txt` — pip dependencies
- No YAML/JSON config files for experiments (CLI arguments used instead)

### Expected Input/Output Files

| Type | Path | Format |
|------|------|--------|
| Raw data input | `data/raw/<dataset>/*.jsonl` | JSONL |
| Processed data | `data/processed/<dataset>/*.jsonl` | JSONL |
| Pairwise prefs | `data/processed/<dataset>/pairwise/preferences.jsonl` | JSONL |
| Synthetic results | `outputs/synthetic_results.json` | JSON |
| Per-query results | `outputs/<dataset>_per_query.csv` | CSV |
| Summary results | `outputs/<dataset>_summary.csv` | CSV |
| Experiment summary | `outputs/<dataset>_experiment_summary.json` | JSON |
| Timing data | `outputs/timings/*.csv`, `outputs/timings/*.json` | CSV/JSON |
| Plots | `outputs/plots/*.png` | PNG |

### SLURM / HPC Scripts

**None.** No SLURM scripts, job arrays, or HPC configuration files exist.

### Result Aggregation

- `run_real_experiment.py` includes a `_build_summary()` function that aggregates per-query results into per-method statistics (mean/median/max of Kendall τ, BEW, PIC, runtime).
- Results are saved as CSV files suitable for further analysis.
- `plot_timings.py` generates bar charts, pie charts, and scatter plots.

---

## 6. Retrieval / Reranking / LLM Relevance

### Status: Mostly Absent

| Component | Present? | Details |
|-----------|----------|---------|
| **Retrieval datasets** | **Partial** | BEIR, HotpotQA, BRIGHT loaders exist but derive preferences from *qrels labels*, not from actual retrieval runs |
| **Ranking from pairwise comparisons** | **Yes** | Core functionality of the repo — `pairwise_prefs.py`, `graph_construction.py`, `greedy_fas.py` |
| **Reranking pipelines** | **No** | No first-stage retrieval → reranking pipeline exists |
| **LLM prompting / judging** | **No** | `TODO.md` lists "Integrate a real LLM pairwise comparator" as a near-term task; no implementation exists |
| **Cross-encoders / transformers** | **No** | No neural model code; no `transformers` or `sentence-transformers` dependency |
| **Evidence ranking** | **Partial** | HotpotQA supporting facts are used as relevance labels, but no explicit evidence chain reasoning |
| **Query-document scoring** | **No** | No scoring model; preferences derived from ground-truth labels only |
| **RAG pipeline** | **No** | Not present or referenced |

### Key Finding

The repo constructs pairwise preferences **exclusively from ground-truth relevance labels** (qrels). It does not yet generate preferences from:
- LLM pairwise judgments (e.g., "Is document A more relevant than document B for query Q?")
- Cross-encoder scores
- Retrieval model scores
- Any neural or learned scoring function

This is the **single largest gap** for the new research direction.

---

## 7. Best Reusable Components (Top 10)

### 1. `greedy_fas.py` — Greedy MWFAS Heuristic
**Why useful:** Core algorithm for removing inconsistencies from pairwise preference graphs. Directly applicable to any preference graph, regardless of how edges are generated (qrels, LLM judgments, cross-encoder scores).

### 2. `graph_construction.py` — Preference Graph Builder
**Why useful:** Clean interface to build weighted directed graphs from preference triples. Supports multiple aggregation strategies (sum, mean, max, custom). Works with any source of pairwise preferences.

### 3. `data/schema.py` — Unified Data Schema
**Why useful:** Well-designed dataclasses (`Query`, `Document`, `QrelEntry`, `PairwisePreference`, `CandidateRanking`) that can serve as the canonical data model for the new project.

### 4. `data/unified_loader.py` — `preferences_from_qrels()`
**Why useful:** Bridge between standard IR evaluation labels and pairwise preference graphs. Essential for bootstrapping experiments on BEIR/HotpotQA before LLM judging is implemented.

### 5. `baseline_ranking.py` — Ranking Baselines
**Why useful:** Four baselines (score-sum, Borda, PageRank, topological) provide comparison points for any new consistency-aware ranking method.

### 6. `evaluation.py` — Ranking Evaluation Metrics
**Why useful:** Kendall τ, pairwise inconsistency count, and violation count are directly relevant metrics. Needs extension (NDCG, Spearman, MRR) but the foundation is solid.

### 7. `cycle_detection.py` — Cycle Analysis
**Why useful:** Rich cycle characterization (detection, enumeration, node/edge membership, SCC analysis) is essential for understanding inconsistency structure in preference graphs.

### 8. `run_real_experiment.py` — Per-Query Experiment Framework
**Why useful:** Comprehensive per-query experiment loop with timing, aggregation, CSV/JSON output, and plotting. Can be extended to support additional ranking methods and LLM-based preference generation.

### 9. `data/dataset_registry.py` — Dataset Configuration Registry
**Why useful:** Extensible registry pattern that makes adding new datasets straightforward. Just add a new `DatasetConfig` entry.

### 10. `utils/timing.py` — Profiling Infrastructure
**Why useful:** Drop-in timing for any pipeline stage. Essential for benchmarking computational costs of consistency repair algorithms at scale.

---

## 8. Gaps / Missing Pieces

### For BEIR Reranking

| Gap | Description | Effort |
|-----|-------------|--------|
| **First-stage retrieval** | No BM25, dense retrieval, or any first-stage retrieval system. The repo assumes qrels are given. | Significant — need to integrate `pyserini`, `rank_bm25`, or a dense retriever |
| **Reranking pipeline** | No retrieve-then-rerank pipeline. Need to generate candidate lists, then apply consistency-aware reranking. | Moderate |
| **NDCG@k evaluation** | `evaluation.py` lacks NDCG, MRR, MAP — standard IR metrics. | Small |
| **Cross-encoder scoring** | No neural scoring models to generate pairwise preferences from actual document content. | Moderate — integrate `sentence-transformers` CrossEncoder |

### For BRIGHT Reasoning Retrieval

| Gap | Description | Effort |
|-----|-------------|--------|
| **BRIGHT data access** | The loader has graceful fallback, but actual downloading may require HuggingFace authentication. | Small (configuration) |
| **Reasoning-aware features** | No reasoning chain analysis, no chain-of-thought integration, no reasoning-specific metrics. | Significant — research-level |

### For HotpotQA Evidence Ordering

| Gap | Description | Effort |
|-----|-------------|--------|
| **Multi-hop reasoning** | Evidence ordering for multi-hop QA requires understanding dependency chains between evidence pieces. The current approach treats all documents independently. | Significant — research-level |
| **Evidence chain modeling** | No graph structure that captures which evidence pieces support which reasoning steps. | Significant |

### For Pairwise Preference Graph Construction from Model Scores or LLM Judgments

| Gap | Description | Effort |
|-----|-------------|--------|
| **LLM pairwise comparator** | No LLM API integration (OpenAI, Anthropic, etc.) for generating "Is A better than B?" judgments. Listed in `TODO.md` as a near-term task. | Moderate — need API wrappers, prompt templates, response parsing |
| **Cross-encoder preference generation** | No functionality to convert cross-encoder scores into pairwise preferences with confidence weights. | Moderate |
| **Score-to-preference conversion** | No utility to convert pointwise relevance scores (from any model) into pairwise preference graphs. | Small — straightforward extension of `preferences_from_qrels()` |
| **Preference noise modeling** | Synthetic noise is uniform random flips. No model of realistic LLM judgment noise (position bias, verbosity bias, etc.). | Research-level |
| **Batch preference generation** | No batched/async API calls for efficiently generating large numbers of pairwise comparisons. | Moderate |

### General Missing Pieces

| Gap | Description |
|-----|-------------|
| **ILP MWFAS solver** | Stub only — no exact solver for comparison with greedy heuristic |
| **Additional FAS heuristics** | No 2-approximation, no simulated annealing, no spectral methods |
| **Spearman ρ and NDCG** | Listed in `TODO.md`, not implemented |
| **Jupyter notebooks** | `notebooks/` directory exists but is empty |
| **SLURM/HPC support** | No job scripts for cluster computing |
| **Sinkhorn ranking baseline** | Listed in `TODO.md`, not implemented |
| **Confidence/uncertainty estimates** | Listed in `TODO.md`, not implemented |

---

## 9. Recommended Next Steps

### Phase 1: Foundation (merge + extend)

1. **Merge the `copilot/setup-python-research-repo` branch into `main`** — all the useful code lives there.

2. **Add NDCG@k and Spearman ρ** to `evaluation.py` — these are standard IR metrics and straightforward to implement.

3. **Add a pointwise-score-to-preference converter** — create a function `preferences_from_scores(query_id, doc_scores: dict[str, float]) → list[PairwisePreference]` that converts any set of pointwise relevance scores into pairwise preferences. This is the minimal bridge needed to connect any scoring model.

### Phase 2: LLM Integration

4. **Implement an LLM pairwise comparator** — create `src/consistency_ranker/llm_comparator.py` with:
   - Prompt templates for pairwise document comparison
   - API wrappers for OpenAI/Anthropic
   - Response parsing (winner extraction + confidence)
   - Conversion to `PairwisePreference` objects
   - Rate limiting and caching

5. **Create a cross-encoder preference generator** — use `sentence-transformers` CrossEncoder to score (query, doc) pairs, then convert scores to pairwise preferences.

### Phase 3: End-to-End Reranking Pipeline

6. **Build a retrieve-then-rerank pipeline** — integrate BM25 (via `rank_bm25` or `pyserini`) as a first-stage retriever, then apply consistency-aware reranking on the top-k candidates.

7. **Run the first BEIR reranking experiment** using the existing `run_real_experiment.py` framework:
   - Download SciDocs/FiQA
   - Generate pairwise preferences (initially from qrels, then from cross-encoder scores, then from LLM judgments)
   - Compare greedy-FAS ranking vs. baselines
   - Report NDCG@10, Kendall τ

### Phase 4: Reasoning & Evidence

8. **Extend the HotpotQA pipeline** to model evidence ordering — the preference graph should encode dependencies between evidence pieces, not just independent relevance.

9. **Investigate LLM self-consistency** — generate multiple LLM judgments per pair, measure how often cycles arise, and study whether chain-of-thought prompting reduces preference cycles. This is the research question stated in the README.

---

## Executive Summary

### What this repo is strongest at

The repository has a **solid, well-engineered core pipeline** for consistency-aware ranking using pairwise preference graphs and feedback arc set optimization. The code is clean, well-documented, fully tested, and follows good software engineering practices. The pipeline from "pairwise preferences → weighted directed graph → cycle detection → greedy FAS → DAG → topological ranking → evaluation" is **complete and functional** for both synthetic and real data experiments.

### What is already useful for the new project

- **Directly reusable:** The entire graph-based ranking pipeline (`graph_construction.py`, `greedy_fas.py`, `baseline_ranking.py`, `cycle_detection.py`, `evaluation.py`), the data schema, dataset loaders for BEIR/HotpotQA/BRIGHT, the experiment runner framework, and the timing/profiling infrastructure.
- **Immediately runnable:** The synthetic experiment (`run_synthetic.py`) works out of the box. The real-data experiment (`run_real_experiment.py`) works after downloading datasets.
- **Well-structured for extension:** The modular architecture makes it straightforward to add new ranking methods, new preference generators, and new evaluation metrics.

### What is missing

The **critical gap** is the preference generation layer. Currently, all pairwise preferences are derived from ground-truth relevance labels (qrels) or synthetic noise. For the "Consistency-Aware Ranking and Reasoning in AI Systems" research direction, the following are needed but absent:

1. **LLM-based pairwise judgment generation** (the core research driver)
2. **Cross-encoder / neural scoring** for realistic preference generation
3. **First-stage retrieval** (BM25 or dense) for a complete reranking pipeline
4. **Standard IR metrics** (NDCG@k, MRR, MAP)
5. **ILP exact solver** for benchmarking against the greedy heuristic
6. **Reasoning-specific components** for BRIGHT and HotpotQA evidence ordering

In short: the **graph optimization and ranking evaluation infrastructure is ready**; the **preference input layer and retrieval integration need to be built**.
