# Repository Analysis: consistency-aware-llm-rankin

**Date:** 2026-03-20
**Analyst:** Automated repository inspection
**Branch inspected:** `origin/copilot/setup-python-research-repo` (the `main` branch contains only an initial commit with README, LICENSE, and .gitignore)

---

## 1. High-Level Repository Summary

### What is this repo mainly about?

This repository implements a **Consistency-Aware Ranking** framework for LLM systems. The core idea: when LLMs produce pairwise preference judgements (e.g., "Is answer A better than answer B?"), those preferences can contain **cycles** (A > B > C > A), making a globally consistent ranking impossible. The repo addresses this by modelling preferences as a **weighted directed graph** and solving the **Minimum Weighted Feedback Arc Set (MWFAS)** problem — removing the minimum-weight set of edges to produce a DAG, then ranking via topological sort.

### Major subprojects / pipelines

| Pipeline | Description |
|----------|-------------|
| **Synthetic experiment** | End-to-end pipeline: generate items → noisy pairwise prefs → graph → cycle detection → FAS removal → ranking → evaluation |
| **Real-data experiment** | Loads BEIR/HotpotQA/BRIGHT datasets → derives pairwise preferences from qrels → runs the same graph-based ranking pipeline per query |
| **Dataset download & preparation** | Scripts to download from HuggingFace and convert to unified JSONL format |
| **Timing & profiling** | Instrumented timing across all pipeline stages with CSV/JSON export and matplotlib plotting |

### Research directions supported

1. Measuring cycle frequency in pairwise preference graphs
2. Comparing greedy FAS heuristic against baselines (score-sum, Borda, PageRank, topological sort)
3. Evaluating ranking quality via Kendall τ, pairwise inconsistency counts, backward edge weight
4. Scaling analysis (runtime vs. graph size)
5. (Planned) ILP-based exact MWFAS, LLM-based pairwise comparison integration

---

## 2. Code Inventory

### Data Loading / Preprocessing

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/data/schema.py` | Core data classes: `Query`, `Document`, `QrelEntry`, `CandidateRanking`, `PairwisePreference` with JSON serialization | **Mature** — clean, well-documented, fully functional |
| `src/consistency_ranker/data/dataset_registry.py` | Central `DatasetConfig` registry for scidocs, fiqa, hotpotqa, bright with HuggingFace ids and paths | **Mature** — complete for 4 datasets |
| `src/consistency_ranker/data/beir_loader.py` | BEIR corpus/queries/qrels loader from HuggingFace or local JSONL | **Mature** — handles full download + local read |
| `src/consistency_ranker/data/hotpotqa_loader.py` | HotpotQA multi-hop QA loader; treats supporting passages as retrieval candidates | **Mature** — working download + schema conversion |
| `src/consistency_ranker/data/bright_loader.py` | BRIGHT reasoning retrieval loader with graceful fallback + manual instructions | **Mature** — defensive error handling, placeholder if download fails |
| `src/consistency_ranker/data/unified_loader.py` | Unified interface: `load_dataset_splits()`, `preferences_from_qrels()`, pairwise preference I/O | **Mature** — key bridge between raw data and ranking pipeline |
| `src/consistency_ranker/data/__init__.py` | Empty init file | N/A |
| `src/consistency_ranker/data_loader.py` | Legacy generic JSONL/CSV/TXT file loader | **Mature but peripheral** — utility, not used by main pipeline |
| `src/consistency_ranker/synthetic_data.py` | Generate synthetic items with latent quality scores | **Mature** — clean, well-tested |

### Graph Construction

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/graph_construction.py` | Build `nx.DiGraph` from pairwise preferences with configurable aggregation (sum/mean/max) | **Mature** — core component, well-designed |

### Pairwise Comparison / Edge-Weight Generation

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/pairwise_prefs.py` | Generate noisy pairwise preferences from quality scores; supports uniform and margin weight schemes | **Mature** — synthetic noise model only; no LLM integration |
| `src/consistency_ranker/data/unified_loader.py` (function `preferences_from_qrels`) | Derive pairwise preferences from relevance judgements (grade_diff or binary weighting) | **Mature** — works for real datasets |

### Ranking / Ordering Algorithms

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/baseline_ranking.py` | Four baselines: `score_sum_ranking`, `topological_ranking`, `pagerank_ranking`, `borda_ranking` | **Mature** — all implemented and tested |

### Feedback Arc Set / MWFAS Heuristics

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/greedy_fas.py` | Greedy FAS heuristic: iteratively find cycle, remove minimum-weight edge | **Mature** — working, tested, has known performance limitations noted in comments |
| `src/consistency_ranker/mwfas_solver.py` | Unified solver interface dispatching to greedy or ILP backends | **Partial** — greedy backend works; ILP backend is a **stub** that raises `NotImplementedError` |

### Cycle Detection

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/cycle_detection.py` | `has_cycle`, `find_simple_cycles`, `count_cycles`, `nodes_in_cycles`, `cycle_edge_set`, `cycle_summary` | **Mature** — Johnson's algorithm wrapper; correctly warns about exponential cost for dense graphs |

### Evaluation / Metrics

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/evaluation.py` | Kendall τ, ranking agreement, n_violations, pairwise inconsistency count | **Mature but incomplete** — TODO items note missing Spearman ρ and NDCG |

### Experiment Runners

| File | Description | Maturity |
|------|-------------|----------|
| `scripts/run_synthetic.py` | Full synthetic experiment CLI with timing, JSON output | **Mature** — complete end-to-end pipeline |
| `scripts/run_real_experiment.py` | Real-data experiment: per-query pipeline with CSV/JSON output, aggregate summaries, plots | **Mature** — 1024 lines, comprehensive, well-structured |
| `scripts/download_datasets.py` | Download datasets from HuggingFace | **Mature** |
| `scripts/prepare_datasets.py` | Convert raw downloads to unified JSONL + generate pairwise preferences | **Mature** |

### Plotting / Analysis / Result Aggregation

| File | Description | Maturity |
|------|-------------|----------|
| `scripts/plot_timings.py` | Generate 4 types of timing plots from profiling JSON | **Mature** — stage bar, pie, method bar, runtime-vs-n_items |
| `scripts/run_real_experiment.py` (plotting functions) | Embedded plotting: runtime by method, runtime vs nodes/edges | **Mature** |

### Utilities

| File | Description | Maturity |
|------|-------------|----------|
| `src/consistency_ranker/utils/timing.py` | `Timer` context manager, `timed` decorator, `TimingAccumulator` with CSV/JSON export | **Mature** — ~380 lines, well-designed |

### Tests

| File | Tests for | Maturity |
|------|-----------|----------|
| `tests/test_baseline_ranking.py` | All 4 baseline ranking methods | **Mature** |
| `tests/test_cycle_detection.py` | All cycle detection functions | **Mature** |
| `tests/test_data_pairwise.py` | Preference generation from qrels, save/load | **Mature** |
| `tests/test_data_registry.py` | Dataset registry configuration | **Mature** |
| `tests/test_data_schema.py` | Schema dataclass serialization | **Mature** |
| `tests/test_evaluation.py` | All evaluation metrics | **Mature** |
| `tests/test_greedy_fas.py` | Greedy FAS correctness | **Mature** |
| `tests/test_timing.py` | Timer and accumulator utilities | **Mature** |

### LLM / Retrieval / Reranking

**No files implement LLM integration, cross-encoder reranking, or retrieval pipelines.** This is explicitly noted as future work in `TODO.md`.

---

## 3. Existing Algorithms Already Implemented

### 3.1 Greedy Feedback Arc Set (MWFAS) Heuristic

- **Where:** `src/consistency_ranker/greedy_fas.py` → `greedy_fas()`
- **Input:** `nx.DiGraph` with weighted edges (preference graph)
- **Output:** `(dag: nx.DiGraph, removed_edges: list[(u, v, weight)])`
- **Strategy:** Iteratively find a cycle via `nx.find_cycle`, remove the minimum-weight edge, repeat until DAG
- **Complexity:** O(C × (n+e)) where C = removal iterations
- **Reusable?** **Yes — directly reusable.** This is the core consistency-repair algorithm.

### 3.2 Score-Sum Ranking

- **Where:** `src/consistency_ranker/baseline_ranking.py` → `score_sum_ranking()`
- **Input:** `nx.DiGraph` (preference graph)
- **Output:** `list[str]` — node IDs sorted by total outgoing edge weight
- **Reusable?** **Yes** — simple, fast baseline for any preference graph

### 3.3 Borda Ranking

- **Where:** `src/consistency_ranker/baseline_ranking.py` → `borda_ranking()`
- **Input:** `nx.DiGraph`
- **Output:** `list[str]` — sorted by out-degree (number of wins)
- **Reusable?** **Yes** — classical Borda count baseline

### 3.4 PageRank Ranking

- **Where:** `src/consistency_ranker/baseline_ranking.py` → `pagerank_ranking()`
- **Input:** `nx.DiGraph` (uses reversed graph for authority flow)
- **Output:** `list[str]` — sorted by PageRank score
- **Reusable?** **Yes** — interesting spectral baseline for preference graphs

### 3.5 Topological Sort Ranking

- **Where:** `src/consistency_ranker/baseline_ranking.py` → `topological_ranking()`
- **Input:** `nx.DiGraph` (must be a DAG — typically post-FAS)
- **Output:** `list[str]` — topological order
- **Reusable?** **Yes** — standard post-FAS ranking step

### 3.6 MWFAS Solver Interface (Greedy + ILP Stub)

- **Where:** `src/consistency_ranker/mwfas_solver.py` → `solve()`
- **Input:** `nx.DiGraph`, method name
- **Output:** `(dag, removed_edges)`
- **Status:** Greedy backend works; ILP backend raises `NotImplementedError`
- **Reusable?** **Yes** — clean dispatch interface; ILP needs implementation

### 3.7 Cycle Detection Suite

- **Where:** `src/consistency_ranker/cycle_detection.py`
- **Methods:** `has_cycle`, `find_simple_cycles` (Johnson's), `count_cycles`, `nodes_in_cycles`, `cycle_edge_set`, `cycle_summary`
- **Reusable?** **Yes** — full cycle analysis toolkit

### 3.8 Noisy Pairwise Preference Generator

- **Where:** `src/consistency_ranker/pairwise_prefs.py` → `generate_preferences()`
- **Input:** `dict[str, float]` (quality map), noise level, weight scheme
- **Output:** `list[Preference(winner, loser, weight)]`
- **Reusable?** **Yes** — essential for synthetic experiments with controlled inconsistency

### 3.9 Qrel-to-Preference Converter

- **Where:** `src/consistency_ranker/data/unified_loader.py` → `preferences_from_qrels()`
- **Input:** `list[QrelEntry]`, top_k, weight_scheme
- **Output:** `list[PairwisePreference]`
- **Reusable?** **Yes** — bridges real IR datasets to the preference graph pipeline

### 3.10 Kendall τ and Evaluation Metrics

- **Where:** `src/consistency_ranker/evaluation.py`
- **Methods:** `kendall_tau`, `ranking_agreement`, `n_violations`, `pairwise_inconsistency_count`
- **Reusable?** **Yes** — standard ranking evaluation; would benefit from NDCG and Spearman ρ additions

---

## 4. Dataset Inventory

### 4.1 Registered Datasets

| Short Name | Source | HuggingFace ID | Purpose | Data Present? |
|------------|--------|----------------|---------|---------------|
| `scidocs` | BEIR / SciDocs | `BeIR/scidocs`, `BeIR/scidocs-qrels` | Citation recommendation, scientific document retrieval | **No** — only `.gitkeep` placeholder directories |
| `fiqa` | BEIR / FiQA-2018 | `BeIR/fiqa`, `BeIR/fiqa-qrels` | Financial opinion QA and retrieval | **No** — only `.gitkeep` placeholders |
| `hotpotqa` | HotpotQA | `hotpot_qa` (fullwiki) | Multi-hop question answering over Wikipedia | **No** — only `.gitkeep` placeholders |
| `bright` | BRIGHT | `xlangai/BRIGHT` | Reasoning-intensive retrieval | **No** — only `.gitkeep` placeholders |

### 4.2 Data Directory Structure

```
data/
├── raw/                              # Downloaded raw files (empty, .gitkeep only)
│   ├── beir/scidocs/.gitkeep
│   ├── beir/fiqa/.gitkeep
│   ├── hotpotqa/.gitkeep
│   └── bright/.gitkeep
├── processed/                        # Unified JSONL + pairwise prefs (empty)
│   ├── beir/scidocs/pairwise/.gitkeep
│   ├── beir/fiqa/pairwise/.gitkeep
│   ├── hotpotqa/pairwise/.gitkeep
│   └── bright/pairwise/.gitkeep
└── .gitkeep
```

### 4.3 File Formats

- **Raw:** JSONL files (queries, documents, qrels) downloaded from HuggingFace
- **Processed:** Unified JSONL matching the schema in `schema.py`
- **Pairwise:** `preferences.jsonl` — one `PairwisePreference` per line
- **Results:** JSON (synthetic), CSV (per-query real-data), JSON (experiment summaries)

### 4.4 Benchmark Usage

| Benchmark | Referenced? | Loader Implemented? | Data Present? |
|-----------|-------------|---------------------|---------------|
| BEIR (SciDocs, FiQA) | Yes | Yes | No (download script provided) |
| HotpotQA | Yes | Yes | No (download script provided) |
| BRIGHT | Yes | Yes (with fallback) | No (may require manual download) |
| MS-MARCO | Mentioned in TODO.md | **No** | No |
| TREC-DL | Mentioned in TODO.md | **No** | No |
| DIMACS | Not mentioned | No | No |
| Connectome / Sports | Not mentioned | No | No |

---

## 5. Current Experiment Pipeline

### 5.1 Synthetic Experiment

**Entry point:** `python scripts/run_synthetic.py`

```
CLI args → generate_items() → generate_preferences() → build_graph()
  → has_cycle() → score_sum_ranking() / borda_ranking()
  → greedy_fas() → topological_ranking()
  → kendall_tau() / n_violations() / pairwise_inconsistency_count()
  → save JSON to outputs/synthetic_results.json
  → optionally save timings to outputs/timings/
```

**Key arguments:** `--n-items`, `--noise`, `--seed`, `--weight-scheme`, `--save-timings`, `--profile`

### 5.2 Real-Data Experiment

**Entry points (3-step):**
1. `python scripts/download_datasets.py --dataset <name>` → downloads to `data/raw/`
2. `python scripts/prepare_datasets.py --dataset <name>` → converts to `data/processed/`
3. `python scripts/run_real_experiment.py --dataset <name>` → runs per-query pipeline

**Per-query pipeline (in `run_real_experiment.py`):**
```
load_dataset_splits() → preferences_from_qrels() → build_graph()
  → has_cycle() → greedy_fas()
  → score_sum / borda / pagerank / topological rankings
  → _kendall_tau() / _backward_edge_weight() / _pairwise_inconsistency()
  → collect per-query CSV rows → aggregate summary CSV
  → optional timing export and plots
```

**Key arguments:** `--dataset`, `--max-queries`, `--top-k`, `--weight-scheme`, `--save-timings`, `--profile`

### 5.3 Config Files

- `pyproject.toml` — package metadata, dependencies, tool config (ruff, pytest)
- `requirements.txt` — pinned dependency versions
- `src/consistency_ranker/data/dataset_registry.py` — dataset configurations

### 5.4 Expected Input/Output

| Type | Location |
|------|----------|
| Raw datasets | `data/raw/<dataset>/` |
| Processed datasets | `data/processed/<dataset>/` |
| Pairwise preferences | `data/processed/<dataset>/pairwise/preferences.jsonl` |
| Synthetic results | `outputs/synthetic_results.json` |
| Per-query CSV | `outputs/<dataset>_per_query.csv` |
| Summary CSV | `outputs/<dataset>_summary.csv` |
| Experiment summary | `outputs/<dataset>_experiment_summary.json` |
| Timing CSV | `outputs/timings/<dataset>_timings.csv` |
| Timing JSON | `outputs/timings/<dataset>_timings.json` |
| Plots | `outputs/plots/` |

### 5.5 SLURM / HPC Scripts

**None.** No SLURM scripts, job submission files, or HPC configuration found.

### 5.6 Result Aggregation

The `run_real_experiment.py` script has built-in aggregation:
- `_build_summary()` — aggregates per-method statistics (mean/median/max of metrics)
- `_build_experiment_summary()` — top-level experiment summary with avg graph size, % cyclic, best method
- `_write_csv()` — CSV export
- `_maybe_plot()` — auto-generates plots if matplotlib available

---

## 6. Retrieval / Reranking / LLM Relevance

### Assessment: Largely Absent

| Capability | Present? | Details |
|------------|----------|---------|
| Retrieval datasets | **Partial** | Dataset configs for BEIR, HotpotQA, BRIGHT exist with download scripts, but no retrieval pipeline (no first-stage retrieval, no BM25, no dense retrieval) |
| Ranking from pairwise comparisons | **Yes** | Core pipeline converts pairwise preferences → graph → ranking |
| Reranking pipelines | **No** | No code for reranking a first-stage retrieval result |
| LLM prompting / judging | **No** | No LLM API calls, no prompt templates, no pairwise comparison prompts. Explicitly listed as near-term TODO |
| Cross-encoders / transformers | **No** | No transformer model code, no HuggingFace model loading for scoring |
| Evidence ranking | **Partial** | HotpotQA loader treats supporting facts as relevant documents, but no multi-hop reasoning logic |
| Query-document scoring | **No** | No scoring models; preferences currently come from qrel labels or synthetic noise |

### Specific Files Relevant to Retrieval

- `src/consistency_ranker/data/beir_loader.py` — loads BEIR corpus/queries/qrels (retrieval benchmark data)
- `src/consistency_ranker/data/hotpotqa_loader.py` — loads multi-hop QA data (evidence retrieval)
- `src/consistency_ranker/data/bright_loader.py` — loads reasoning-intensive retrieval data
- `src/consistency_ranker/data/unified_loader.py` → `preferences_from_qrels()` — converts relevance labels to pairwise preferences

**What is missing:** All pairwise preferences currently come from **ground-truth relevance labels**, not from model predictions or LLM judgements. There is no code to:
- Run a first-stage retriever (BM25, dense)
- Score query-document pairs with a cross-encoder
- Generate pairwise preferences via LLM prompts
- Handle LLM API calls (OpenAI, Anthropic, etc.)

---

## 7. Best Reusable Components for a New Project

Ranked by utility for **"Consistency-Aware Ranking and Reasoning in AI Systems"**:

### 1. Greedy FAS Heuristic (`greedy_fas.py`)
**Why:** Core algorithm for resolving inconsistencies in pairwise preference graphs. Directly applicable to any setting where you have a tournament graph with cycles.

### 2. Graph Construction Module (`graph_construction.py`)
**Why:** Clean, configurable graph builder with multiple aggregation strategies (sum/mean/max). Any preference-based ranking system needs this.

### 3. Pairwise Preference Schema and I/O (`data/schema.py`, `data/unified_loader.py`)
**Why:** Well-designed data classes (`PairwisePreference`, `Query`, `Document`, `QrelEntry`) with JSON serialization. This is the data backbone for any expansion.

### 4. MWFAS Solver Interface (`mwfas_solver.py`)
**Why:** Clean dispatch pattern that can be extended with new backends (ILP, approximation algorithms, spectral methods) without changing downstream code.

### 5. Baseline Ranking Methods (`baseline_ranking.py`)
**Why:** Four baselines (score-sum, Borda, PageRank, topological) already implemented and tested — essential for comparative experiments.

### 6. Real-Data Experiment Runner (`scripts/run_real_experiment.py`)
**Why:** 1024-line production-quality script with per-query pipeline, CSV/JSON output, aggregation, timing, and plotting. Saves substantial development effort.

### 7. Evaluation Metrics (`evaluation.py`)
**Why:** Kendall τ, violation counts, and pairwise inconsistency metrics are exactly what you need for measuring ranking quality under inconsistency.

### 8. Dataset Registry and Loaders (`data/dataset_registry.py`, `beir_loader.py`, `hotpotqa_loader.py`)
**Why:** Pre-built loaders for 4 retrieval benchmarks with unified schema. Adding new datasets requires only a new registry entry and loader.

### 9. Cycle Detection Suite (`cycle_detection.py`)
**Why:** Full toolkit for characterizing inconsistency in preference graphs (SCC analysis, cycle enumeration, node/edge participation). Essential for research analysis.

### 10. Timing/Profiling Framework (`utils/timing.py`)
**Why:** Drop-in instrumentation for any pipeline stage. Context manager + decorator patterns make it trivial to profile new components.

---

## 8. Gaps / Missing Pieces

### 8.1 For BEIR Reranking

| Gap | Description | Effort |
|-----|-------------|--------|
| First-stage retriever | No BM25 or dense retrieval to produce initial candidate lists | Moderate — integrate pyserini or sentence-transformers |
| Cross-encoder scorer | No transformer-based relevance scoring for query-document pairs | Moderate — add HuggingFace cross-encoder wrapper |
| Reranking pipeline | No end-to-end retrieve → score → rerank flow | Moderate — new script needed |
| NDCG@k evaluation | Only Kendall τ implemented; NDCG is standard for BEIR | Low — add to `evaluation.py` |
| MAP, MRR metrics | Not implemented | Low |

### 8.2 For BRIGHT Reasoning Retrieval

| Gap | Description | Effort |
|-----|-------------|--------|
| BRIGHT data validation | Loader exists but is untested with actual data (best-effort parse) | Low — test with real download |
| Reasoning-aware scoring | No chain-of-thought or reasoning prompts for relevance | High — needs LLM integration |
| Multi-task evaluation | BRIGHT has 12+ tasks; current registry only uses `biology` | Low — parameterize task selection |

### 8.3 For HotpotQA Evidence Ordering

| Gap | Description | Effort |
|-----|-------------|--------|
| Multi-hop reasoning | Loader extracts documents but doesn't model reasoning chains | High — new module needed |
| Evidence chain ordering | No code to order evidence passages for multi-hop answers | Moderate — new pipeline component |
| Supporting fact precision | Evaluation doesn't measure supporting-fact-level metrics | Low — extend evaluation |

### 8.4 For Pairwise Preference Graph Construction from Model Scores / LLM Judgments

| Gap | Description | Effort |
|-----|-------------|--------|
| LLM pairwise comparator | No code to prompt an LLM with "Is doc A better than doc B for query Q?" | Moderate — new module with API calls |
| Cross-encoder pairwise scoring | No transformer-based pairwise scoring | Moderate — integrate HuggingFace models |
| Score-to-preference converter | No code to convert continuous scores to pairwise preferences with confidence | Low — extend `pairwise_prefs.py` |
| Batched LLM inference | No infrastructure for batched API calls, rate limiting, caching | Moderate — new utility module |
| Prompt templates | No prompt engineering infrastructure | Low — new module |
| Noise model for LLM judgments | Synthetic noise is random; real LLM noise has structure (position bias, verbosity bias) | Research-level |

### 8.5 General Infrastructure Gaps

| Gap | Description |
|-----|-------------|
| ILP MWFAS solver | Stub exists but not implemented |
| Spearman ρ metric | Listed in TODO, not implemented |
| NDCG metric | Listed in TODO, not implemented |
| SLURM/HPC scripts | No job submission infrastructure |
| Experiment configuration files | No YAML/JSON config system; all via CLI args |
| Results database | No structured storage for experiment tracking |
| Jupyter notebooks | Directory exists but empty |

---

## 9. Recommended Next Steps

### Phase 1: Foundation (minimal changes)

1. **Add NDCG@k and Spearman ρ** to `evaluation.py` — these are essential for IR evaluation and straightforward to implement using scipy.

2. **Implement ILP MWFAS solver** in `mwfas_solver.py` using PuLP — provides an exact optimality baseline for the greedy heuristic comparison.

3. **Run the existing pipeline on real data** — execute `download_datasets.py` + `prepare_datasets.py` + `run_real_experiment.py` on SciDocs and FiQA to validate the full pipeline end-to-end and establish baseline numbers.

### Phase 2: LLM Pairwise Judgments (new module)

4. **Create `src/consistency_ranker/llm_comparator.py`** — a module that:
   - Takes a query + two documents
   - Prompts an LLM (GPT-4, Claude, Llama-3) for a pairwise preference
   - Returns a `PairwisePreference` object with confidence weight
   - Supports batching, caching, and rate limiting

5. **Create `src/consistency_ranker/score_to_preference.py`** — convert continuous model scores (e.g., cross-encoder logits) into pairwise preference graphs, with configurable thresholding and confidence weighting.

### Phase 3: Retrieval Integration (new pipeline)

6. **Add a first-stage retriever** — integrate BM25 (via pyserini or rank_bm25) to produce candidate lists from BEIR corpora.

7. **Add cross-encoder scoring** — wrap a HuggingFace cross-encoder (e.g., `cross-encoder/ms-marco-MiniLM-L-12-v2`) for query-document scoring.

8. **Create `scripts/run_reranking_experiment.py`** — end-to-end pipeline:
   ```
   query → BM25 top-100 → pairwise preferences (from cross-encoder OR LLM)
     → preference graph → FAS repair → consistent ranking
     → evaluate against qrels (NDCG, Kendall τ)
   ```

### Phase 4: Research Experiments

9. **Consistency analysis experiments** — measure cycle density, SCC structure, and FAS cost as a function of:
   - Model type (cross-encoder vs. LLM)
   - Prompt strategy (direct vs. chain-of-thought)
   - Document similarity (close vs. distant candidates)

10. **Adapt for HotpotQA evidence ordering** — extend the pipeline to order evidence passages for multi-hop QA, where the preference graph encodes "which passage should be read first to answer the question."

---

## Executive Summary

### What this repo is strongest at

The repository provides a **well-engineered, fully-tested graph-based ranking pipeline** centered on the MWFAS problem. The core pipeline — from pairwise preferences through graph construction, cycle detection, FAS removal, and evaluation — is **complete and mature**. The code quality is high: consistent docstrings, type hints, clean module boundaries, and comprehensive unit tests (8 test files). The real-data experiment runner is particularly impressive at ~1000 lines with per-query processing, CSV/JSON output, aggregation, timing, and plotting.

### What is already useful for the new project

- **Entire graph-based ranking pipeline** (graph construction → cycle detection → greedy FAS → topological ranking) — directly reusable
- **4 baseline ranking methods** (score-sum, Borda, PageRank, topological sort) — ready for comparison
- **Dataset infrastructure** for BEIR (SciDocs, FiQA), HotpotQA, and BRIGHT — loaders, download scripts, unified schema
- **Evaluation metrics** (Kendall τ, pairwise inconsistency, backward edge weight) — usable immediately
- **Profiling framework** — drop-in timing for any new pipeline stages
- **Experiment runner pattern** — the real-data experiment script is a strong template for new experiments

### What is missing

- **No LLM integration at all** — no pairwise comparison prompts, no API calls, no prompt templates
- **No neural scoring** — no cross-encoders, no transformer models, no embedding-based retrieval
- **No first-stage retrieval** — no BM25 or dense retrieval to produce candidate lists
- **No NDCG/MAP/MRR** — standard IR metrics not yet implemented
- **ILP solver not implemented** — only the greedy heuristic is available
- **No experiment configuration system** — all settings via CLI arguments
- **No SLURM/HPC infrastructure**
- **Actual dataset files are not present** — only empty directory placeholders with download scripts

In summary: the **combinatorial optimization and graph analysis infrastructure is solid and reusable**, but the **information retrieval and LLM components need to be built from scratch**. The repo provides an excellent foundation for the graph-based consistency repair side of the research, while the retrieval/LLM side requires new modules.
