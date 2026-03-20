# Repository Analysis: consistency-aware-llm-rankin

**Date:** 2026-03-20  
**Branch:** cursor/ranking-repository-analysis-bcf5  
**Analyst:** Cloud Agent  

---

## Overview

This repository is a **freshly initialized Python project skeleton**. It contains only three files:

| File | Contents |
|---|---|
| `README.md` | Single-line title stub (`# consistency-aware-llm-rankin`) |
| `LICENSE` | MIT License, copyright 2026, Soroush Vahidi |
| `.gitignore` | Standard Python gitignore template |

There is **no source code, no data, no configuration, and no experiment infrastructure** of any kind.

---

## Section 1 — High-Level Repository Summary

**What this repo is mainly about:**  
The name signals a research project on *consistency-aware LLM ranking* — enforcing transitivity or global coherence over pairwise LLM-generated preferences to produce consistent total orderings of documents, passages, or outputs.

**Major subprojects / pipelines / scripts:** None implemented.

**Research directions it appears to support:** None implemented. The intended direction, based on the name, is ranking via pairwise preference graphs with consistency enforcement (feedback arc set style optimization, Kemeny ranking, or tournament aggregation).

---

## Section 2 — Code Inventory

**No code files exist in the repository.**

| Category | Status |
|---|---|
| Data loading / preprocessing | Absent |
| Graph construction | Absent |
| Ranking / ordering algorithms | Absent |
| Feedback arc set / MWFAS heuristics | Absent |
| Pairwise comparison / edge-weight generation | Absent |
| Evaluation / metrics | Absent |
| Experiment runners | Absent |
| Plotting / analysis / result aggregation | Absent |
| LLM / retrieval / reranking code | Absent |

---

## Section 3 — Existing Algorithms Already Implemented

**None.** No algorithms of any kind have been implemented.

---

## Section 4 — Dataset Inventory

**No datasets are present or referenced.**

There are no data files, no config paths pointing to datasets, no benchmark references in any code, and no data loading scripts. The repository has no connection to BEIR, BRIGHT, HotpotQA, DIMACS, sports datasets, connectome datasets, or any other benchmark.

---

## Section 5 — Current Experiment Pipeline

**No experiment pipeline exists.** There are no entry points, no config files, no logging infrastructure, no result aggregation scripts, and no HPC/SLURM scripts.

---

## Section 6 — Retrieval / Reranking / LLM Relevance

**Entirely absent.** The repository contains nothing related to:

- Retrieval datasets (BEIR, BRIGHT, HotpotQA, etc.)
- Ranking from pairwise comparisons
- Reranking pipelines
- LLM prompting or judging
- Cross-encoders / transformers
- Evidence ranking
- Query-document scoring

---

## Section 7 — Best Reusable Components for a New Project

Since the repository is empty, there are no reusable components within it. Every component must be built or imported from external libraries. The table below maps the needed components to the best external starting points:

| Component | Recommended External Source |
|---|---|
| Pairwise preference graph construction | `networkx` (graph), custom LLM prompting layer |
| Minimum Weighted Feedback Arc Set (MWFAS) solver | ILP via `pulp`/`scipy`, or greedy heuristic (custom) |
| Tournament sort / Kemeny ranking | `ranky` library or custom |
| BEIR retrieval benchmark loading | `beir` Python package |
| BRIGHT reasoning retrieval | HuggingFace datasets (`xlangai/BRIGHT`) |
| HotpotQA evidence loading | HuggingFace datasets (`hotpot_qa`) |
| LLM pairwise judge prompting | `openai` / `anthropic` / `litellm` |
| Cross-encoder reranking | `sentence-transformers` (`CrossEncoder`) |
| Evaluation metrics (nDCG, MAP, MRR) | `ranx`, `pytrec_eval` |
| Experiment configuration management | `hydra-core` or `omegaconf` |

---

## Section 8 — Gaps / Missing Pieces

Everything is missing. Concretely, to support the four experiment tracks:

### BEIR Reranking
- BEIR dataset loader and corpus/query/qrel parser
- First-stage retrieval (BM25 via `pyserini` or `rank_bm25`, or dense retrieval)
- Pairwise comparison generator (model score pairs or LLM judge)
- Preference graph builder (nodes = passages, directed edges = pairwise preferences)
- MWFAS / consistency enforcement layer
- nDCG@10, MAP evaluation via `pytrec_eval`

### BRIGHT Reasoning Retrieval
- HuggingFace dataset loader for BRIGHT
- Reasoning-aware query representation (chain-of-thought or rationale embedding)
- Edge weighting by semantic + reasoning coherence

### HotpotQA Evidence Ordering
- HotpotQA multi-hop question + supporting facts loader
- Evidence chain graph builder (nodes = sentences/paragraphs)
- Consistency check across supporting facts (cycle detection / arc removal)
- Answer verification scoring

### Pairwise Preference Graph from Model Scores or LLM Judgments
- LLM prompt templates for pairwise judgment ("Which passage is more relevant to query Q?")
- LLM API wrapper with rate limiting and caching
- Score-to-edge-weight converter (Bradley-Terry / Plackett-Luce or direct comparison)
- Graph serialization (edge lists, adjacency matrices)

---

## Section 9 — Recommended Next Steps

A practical bootstrapping plan to convert this skeleton into a working pipeline:

### Step 1 — Project Scaffolding
Create `src/` layout with modules: `data/`, `graph/`, `ranking/`, `llm/`, `eval/`, `experiments/`.  
Add `requirements.txt` (or `pyproject.toml`) and a `configs/` directory using Hydra.

### Step 2 — Data Layer
Implement BEIR dataset loader (wrapping the `beir` package).  
Implement HuggingFace wrappers for BRIGHT and HotpotQA.  
Store corpora and qrels in a unified format (JSON lines or HF datasets).

### Step 3 — Baseline Retrieval
Implement BM25 first-stage retrieval (via `rank_bm25` or `pyserini`).  
Implement dense retrieval baseline (via `sentence-transformers`).  
This provides candidate sets to rerank.

### Step 4 — Pairwise Preference Graph
Implement `build_preference_graph(candidates, query, scorer)` where `scorer` can be a cross-encoder or an LLM judge call.  
Output: `networkx.DiGraph` with edge weights representing preference strengths.

### Step 5 — MWFAS / Consistency Enforcement
Implement a greedy MWFAS heuristic (sort by net-flow or local search) and optionally an ILP exact solver for small graphs.  
Output: a total ordering of candidates consistent with the majority of pairwise preferences.

### Step 6 — Evaluation
Wire the final ordering into `pytrec_eval` to compute nDCG@10, MAP, MRR against BEIR qrels.

### Step 7 — Experiment Runner
Write a single `run_experiment.py` using Hydra configs specifying: dataset, retriever, scorer type (cross-encoder vs. LLM), graph construction method, and ranking algorithm. Log results to CSV.

### Step 8 — LLM Judge Integration
Add an OpenAI/Anthropic-compatible judge module with:
- Prompt templates for pairwise preference elicitation
- Response parsing (A > B, B > A, tie)
- Disk caching to avoid redundant API calls
- Rate limiting and retry logic

---

## Executive Summary

| Dimension | Assessment |
|---|---|
| **Strongest capability** | None yet — empty skeleton |
| **Already useful for new project** | Project name, MIT license, Python `.gitignore` |
| **Missing** | Everything: data loaders, preference graph construction, MWFAS solvers, LLM judge prompting, reranking pipelines, evaluation harnesses, experiment runners |

**Bottom line:** This repository has a clear, well-chosen name for the intended research direction. The implementation work has not begun. All components of a consistency-aware LLM ranking system — from data ingestion through pairwise graph construction, consistency enforcement, reranking, and evaluation — must be built from scratch. The recommended starting sequence is: data layer → baseline retrieval → preference graph → MWFAS solver → evaluation → LLM judge integration.
