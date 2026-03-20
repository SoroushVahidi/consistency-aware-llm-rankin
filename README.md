# consistency-aware-llm-rankin

> **PhD Research Repository** — Consistency-Aware Retrieval and Reasoning in LLM Systems  
> Using Combinatorial Optimisation (Minimum Weighted Feedback Arc Set)

---

## Research Motivation

Large language models (LLMs) are increasingly used to rank documents, compare candidate answers, or evaluate action sequences via *pairwise preference judgements*: "Is answer A better than answer B?"  
However, these pairwise preferences are often **inconsistent**: A > B, B > C, yet C > A — a cycle that makes a globally consistent ranking impossible to derive directly.

This repository investigates:

1. **How frequently do LLM pairwise preferences form cycles?**
2. **Can graph-based combinatorial optimisation (specifically the Minimum Weighted Feedback Arc Set problem) repair these inconsistencies?**
3. **How does the repaired ranking compare to baselines like score-sum or topological sort?**

The Minimum Weighted Feedback Arc Set (MWFAS) problem asks: *given a weighted directed graph, remove the minimum-weight set of edges that make the graph a DAG (directed acyclic graph).* This is NP-hard in general, but good heuristics and ILP formulations exist.

---

## Problem Statement

Given a set of items *V* = {v₁, …, vₙ} and a weighted directed graph *G = (V, E, w)* where edge (vᵢ, vⱼ) with weight *wᵢⱼ* means "item i is preferred over item j with confidence wᵢⱼ":

- **Detect cycles** — identify inconsistencies in the preference graph.
- **Remove a minimum-weight set of edges** (MWFAS) to obtain a DAG.
- **Rank items** using a topological ordering of the resulting DAG.
- **Evaluate** the quality of the produced ranking against a ground truth.

---

## Repository Structure

```
consistency-aware-llm-rankin/
├── src/
│   └── consistency_ranker/        # Main Python package
│       ├── __init__.py
│       ├── data_loader.py          # Load datasets from disk
│       ├── synthetic_data.py       # Generate synthetic items + ground-truth ranking
│       ├── pairwise_prefs.py       # Generate noisy pairwise preferences
│       ├── graph_construction.py   # Build weighted directed preference graphs
│       ├── cycle_detection.py      # Detect and enumerate cycles
│       ├── baseline_ranking.py     # Score-sum & topological-sort baselines
│       ├── greedy_fas.py           # Greedy feedback arc removal heuristic
│       ├── mwfas_solver.py         # MWFAS solver interface (greedy + ILP stub)
│       └── evaluation.py           # Metrics: Kendall τ, inconsistency count, etc.
├── tests/                          # Unit tests (pytest)
├── notebooks/                      # Jupyter exploration notebooks
├── scripts/
│   └── run_synthetic.py            # CLI: end-to-end synthetic experiment
├── data/                           # Raw and processed datasets
├── outputs/                        # Experiment results (JSON, CSV)
├── docs/                           # Extended documentation
├── pyproject.toml
├── requirements.txt
├── TODO.md
└── README.md
```

---

## Setup

**Prerequisites:** Python 3.11+

```bash
# 1. Clone the repo
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install the package in editable mode
pip install -e .
```

---

## Running the First Experiment

The first end-to-end synthetic experiment:

1. Generates *N* items with a ground-truth ranking.
2. Generates noisy pairwise comparisons (with configurable noise level).
3. Builds a weighted directed preference graph.
4. Runs baseline ranking methods (score-sum, topological sort on DAG).
5. Runs the greedy feedback arc removal heuristic.
6. Computes Kendall τ correlation and pairwise inconsistency counts.
7. Saves all results to `outputs/`.

```bash
python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42
```

Options:
```
--n-items     Number of items to rank          (default: 20)
--noise       Noise level in pairwise prefs    (default: 0.2)
--seed        Random seed for reproducibility  (default: 42)
--output-dir  Where to save results            (default: outputs/)
```

---

## Running Tests

```bash
pytest
# or with coverage
pytest --cov=consistency_ranker
```

---

## Key Concepts

| Term | Definition |
|------|-----------|
| **Pairwise preference** | A directed edge (i → j) meaning "item i is preferred over j" |
| **Preference graph** | Weighted directed graph of all pairwise preferences |
| **Feedback Arc Set (FAS)** | Set of edges whose removal makes the graph acyclic |
| **MWFAS** | Minimum *weight* FAS — remove as few (confident) preferences as possible |
| **Kendall τ** | Rank correlation metric counting concordant vs. discordant pairs |

---

## Citation

If you use this code in your research, please cite:

```bibtex
@misc{vahidi2024consistency,
  author = {Soroush Vahidi},
  title  = {Consistency-Aware Retrieval and Reasoning in LLM Systems},
  year   = {2024},
  url    = {https://github.com/SoroushVahidi/consistency-aware-llm-rankin}
}
```

---

## License

MIT — see [LICENSE](LICENSE).