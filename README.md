# consistency-aware-llm-rankin

> **Research Repository** — Consistency-Aware Retrieval Ranking via Graph Repair  
> Using Minimum Weighted Feedback Arc Set (MWFAS) Optimisation

---

## Key Finding

> *Repairing cyclic preference graphs improves structural consistency, but does
> not uniformly improve retrieval effectiveness; outcomes depend on vote
> construction, graph regime, and extraction strategy.*

The **canonical evidence package** is `outputs/pub_vote_cmp_all4/paper_package/`
(four datasets). An earlier two-dataset package lives at
`outputs/pub_vote_cmp_v2/paper_package/` and is **historical**; do not mix its numbers
with the all4 package in manuscripts. Both packages show that FAS repair is
**neutral/inactive** under near-acyclic vote constructions and can be **significantly
harmful** (nDCG, bootstrap 95% CI strictly negative) under high-cyclicity construction
on some benchmarks (e.g. SciDocs in the committed bundles). See
[`docs/Q1_POSITIONING_AND_CLAIMS.md`](docs/Q1_POSITIONING_AND_CLAIMS.md) and
[`docs/SAFE_Q1_CLAIMS.md`](docs/SAFE_Q1_CLAIMS.md) for conservative claim wording.

**Scope caveat (important):**
- Canonical **paper-package** tables/plots for the vote-comparison manuscript live under
  `outputs/pub_vote_cmp_all4/paper_package/` (four datasets). The bundle under
  `outputs/pub_vote_cmp_v2/paper_package/` is **historical** and should be cited only
  as such (e.g., ablation lineage), not mixed with the all4 package.
- Preference edges in the committed publication package are generated from
  multi-ranker score votes (BM25/TF-IDF/MiniLM), not direct human annotation.
- Additional experiment trees (including per-dataset runs) may appear under `outputs/real_full/`.

---

## Quickstart (No Network Required)

```bash
# 1. Install
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin
pip install -r requirements.txt && pip install -e ".[dev]"

# 2. Verify the repository is ready
python scripts/check_repo_ready.py

# 3. Run tests
pytest

# 4. Run a synthetic experiment (no network needed)
python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42

# 5. Regenerate the Q1 journal tables from the historical two-dataset package (no network needed)
python scripts/generate_q1_tables.py
#  → outputs/q1_journal_package/  (7 tables + summary_report.md; derived from pub_vote_cmp_v2)

# Alternative: use make targets
make help          # list all available targets
make smoke-test    # quick single synthetic run
make q1-tables     # regenerate Q1 tables
```

See [`docs/REPRODUCTION_Q1.md`](docs/REPRODUCTION_Q1.md) for the full
reproduction guide including real-data experiments.

---

## Documentation Index

| Document | Description |
|---|---|
| [`docs/READ_ME_FIRST_FOR_AI.md`](docs/READ_ME_FIRST_FOR_AI.md) | **Start here** — orientation for humans and AI assistants |
| [`docs/REPRODUCTION_Q1.md`](docs/REPRODUCTION_Q1.md) | Exact commands to reproduce all tables and figures |
| [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) | Quick-reference script index |
| [`docs/Q1_POSITIONING_AND_CLAIMS.md`](docs/Q1_POSITIONING_AND_CLAIMS.md) | Safe claims, unsafe claims, reviewer objections, abstract framing |
| [`docs/SAFE_CLAIMS_FOR_PAPER.md`](docs/SAFE_CLAIMS_FOR_PAPER.md) | Conservative claim set for manuscript writing |
| [`docs/SAFE_Q1_CLAIMS.md`](docs/SAFE_Q1_CLAIMS.md) | Conservative wording guardrails for manuscript claims |
| [`docs/EVIDENCE_MAP.md`](docs/EVIDENCE_MAP.md) | Claim-to-evidence mapping with support levels |
| [`docs/JOURNAL_READY_CONTRIBUTIONS.md`](docs/JOURNAL_READY_CONTRIBUTIONS.md) | Candidate journal-style contribution statements |
| [`docs/RESULTS_FOR_PAPER.md`](docs/RESULTS_FOR_PAPER.md) | What to include vs avoid in manuscript results section |
| [`docs/THREATS_TO_VALIDITY.md`](docs/THREATS_TO_VALIDITY.md) | Structured threats-to-validity section draft |
| [`docs/PAPER_TABLES_GENERATION.md`](docs/PAPER_TABLES_GENERATION.md) | Guide for generating `reports/paper_tables/` |
| [`docs/experiment_inventory.md`](docs/experiment_inventory.md) | Summary of every experiment family |
| [`reports/repo_publication_audit.md`](reports/repo_publication_audit.md) | **Evidence audit** — canonical result package, claim support, v2 vs all4 |
| [`outputs/pub_vote_cmp_all4/paper_package/MANUSCRIPT_SUMMARY.md`](outputs/pub_vote_cmp_all4/paper_package/MANUSCRIPT_SUMMARY.md) | Latest four-dataset manuscript summary (SciDocs, FiQA, HotpotQA, BRIGHT) |
| [`outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md`](outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md) | Earlier two-dataset manuscript findings (historical) |
| [`figures/manuscript/README.md`](figures/manuscript/README.md) | Curated manuscript figures + graphical abstract pointer |

---

## Research Motivation

Pairwise preferences from rankers, LLM judges, or annotators can be
**inconsistent**: A > B, B > C, yet C > A.  These cycles prevent direct
construction of a globally consistent ranking.

This repository investigates:

1. **How frequently do pairwise preference graphs form cycles under different vote constructions?**
2. **Can graph-based combinatorial optimisation (specifically the Minimum Weighted Feedback Arc Set problem) repair these inconsistencies?**
3. **How does the repaired ranking compare to baselines like score-sum or topological sort?**
4. **Does vote construction mediate the repair effect?**

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
│       ├── data/                   # Dataset loading sub-package
│       │   ├── schema.py           # Query, Document, QrelEntry, PairwisePreference
│       │   ├── dataset_registry.py # DatasetConfig registry (scidocs, fiqa, hotpotqa, bright)
│       │   ├── beir_loader.py      # BEIR corpus/queries/qrels loader
│       │   ├── hotpotqa_loader.py  # HotpotQA loader
│       │   ├── bright_loader.py    # BRIGHT loader (with manual-download fallback)
│       │   └── unified_loader.py   # preferences_from_qrels() + load_dataset_splits()
│       ├── data_loader.py          # Legacy generic file loader
│       ├── synthetic_data.py       # Generate synthetic items + ground-truth ranking
│       ├── pairwise_prefs.py       # Generate noisy pairwise preferences
│       ├── graph_construction.py   # Build weighted directed preference graphs
│       ├── cycle_detection.py      # Detect and enumerate cycles
│       ├── baseline_ranking.py     # Score-sum & topological-sort baselines
│       ├── greedy_fas.py           # Greedy feedback arc removal heuristic
│       ├── metric_aware_repair.py  # Optional LambdaRank-style edge reweighting before FAS
│       ├── mwfas_solver.py         # MWFAS solver interface (greedy + exact Gurobi ILP)
│       ├── rrf_ranking.py          # Reciprocal Rank Fusion (multi-ranker list baseline)
│       ├── combsum_ranking.py      # CombSUM score fusion (min-max per ranker by default)
│       ├── borda_fuse_ranking.py   # Borda count over score-prior lists (partial-list safe)
│       ├── markov_graph_ranking.py # Rank Centrality–style Markov chain on preference graphs
│       └── evaluation.py           # Metrics: Kendall τ, inconsistency count, etc.
├── tests/                          # Unit tests (pytest)
├── scripts/
│   ├── run_synthetic.py            # CLI: end-to-end synthetic experiment
│   ├── generate_q1_tables.py       # Regenerate all Q1 journal tables
│   ├── check_repo_ready.py         # Verify repository setup
│   ├── run_publication_vote_suite.py  # Full real-data publication pipeline
│   ├── build_paper_evidence_package.py # Tables + figures from pub suite output
│   ├── bootstrap_method_deltas.py  # Bootstrap ΔnDCG CIs
│   ├── download_datasets.py        # CLI: download real benchmark datasets
│   └── prepare_datasets.py         # CLI: convert raw data to unified JSONL format
├── data/
│   ├── raw/                        # Downloaded raw dataset files
│   │   ├── beir/scidocs/
│   │   ├── beir/fiqa/
│   │   ├── hotpotqa/
│   │   └── bright/
│   ├── processed/                  # Unified JSONL outputs + pairwise preferences
│   │   ├── beir/scidocs/pairwise/
│   │   ├── beir/fiqa/pairwise/
│   │   ├── hotpotqa/pairwise/
│   │   └── bright/pairwise/
│   ├── interim/                    # Scratch space
│   └── cache/                      # HuggingFace cache
├── outputs/
│   ├── pub_vote_cmp_all4/          # Four-dataset publication vote suite (tables/plots committed)
│   │   └── paper_package/
│   ├── pub_vote_cmp_v2/            # Earlier two-dataset publication bundle (historical)
│   │   └── paper_package/
│   └── q1_journal_package/         # Aggregated Q1 tables (auto-generated)
├── figures/                        # Curated manuscript figures + graphical abstract
├── reports/                        # Publication audit, claim matrix, merged result tables
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

# 3. Install package + dev dependencies (pytest, ruff)
pip install -r requirements.txt
pip install -e ".[dev]"

# 4. Verify everything is ready
python scripts/check_repo_ready.py
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

For a concise index of experiment and publication scripts (vote graphs, bootstrap ΔnDCG, paper tables), see [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).

---

## Real Benchmark Datasets

This project supports multiple real retrieval benchmarks.  Most are downloaded
from Hugging Face (or via optional ``ir-datasets`` for TREC-style collections)
and normalised into a common JSONL format.

### Dataset Overview

| Name | Short ID | Source | Description |
|------|----------|--------|-------------|
| BEIR / SciDocs | `scidocs` | [BeIR/scidocs](https://huggingface.co/BeIR/scidocs) | Citation recommendation and scientific document retrieval |
| BEIR / FiQA-2018 | `fiqa` | [BeIR/fiqa](https://huggingface.co/BeIR/fiqa) | Financial opinion QA and retrieval |
| HotpotQA | `hotpotqa` | [hotpot_qa](https://huggingface.co/datasets/hotpot_qa) | Multi-hop question answering over Wikipedia |
| BRIGHT | `bright` | [xlangai/BRIGHT](https://huggingface.co/datasets/xlangai/BRIGHT) | Reasoning-intensive retrieval (may need manual download) |
| BEIR / NFCorpus | `nfcorpus` | [BeIR/nfcorpus](https://huggingface.co/datasets/BeIR/nfcorpus) | Biomedical narrative retrieval (BEIR) |
| MS MARCO passage | `msmarco_passage` | [BeIR/msmarco](https://huggingface.co/datasets/BeIR/msmarco) | Large passage ranking; **streamed** export — use ``--max-docs`` (see raw README) |
| TREC DL passage | `trec_dl_passage` | [ir-datasets](https://ir-datasets.com/) ``msmarco-passage/trec-dl-*`` | Judged DL topics/qrels over MS MARCO passages; requires ``pip install 'consistency-ranker[ir]'`` |
| TREC Robust 2004 | `robust04` | [ir-datasets robust04](https://huggingface.co/datasets/irds/trec-robust04) | Classic ad hoc/news retrieval; requires ``ir-datasets`` (TREC / disk terms) |

### Where Files Are Stored

```
data/
├── raw/
│   ├── beir/scidocs/        # Raw downloaded files (queries, docs, qrels JSONL)
│   ├── beir/fiqa/
│   ├── beir/nfcorpus/
│   ├── msmarco_passage/     # Streamed passage export; see README.md
│   ├── trec_dl_passage/     # ir-datasets export or manual JSONL
│   ├── robust04/            # ir-datasets export or manual JSONL
│   ├── hotpotqa/
│   └── bright/              # Contains README.md with manual instructions if needed
├── processed/
│   ├── beir/scidocs/        # Unified queries.jsonl, documents.jsonl, qrels.jsonl
│   │   └── pairwise/        # preferences.jsonl derived from qrels
│   ├── beir/fiqa/
│   │   └── pairwise/
│   ├── beir/nfcorpus/
│   │   └── pairwise/
│   ├── msmarco_passage/
│   │   └── pairwise/
│   ├── trec_dl_passage/
│   │   └── pairwise/
│   ├── robust04/
│   │   └── pairwise/
│   ├── hotpotqa/
│   │   └── pairwise/
│   └── bright/
│       └── pairwise/
├── interim/                 # Scratch space for intermediate processing
└── cache/                   # HuggingFace dataset cache
```

### Step 1 — Install Dataset Dependencies

```bash
pip install datasets huggingface-hub
```

For **TREC Deep Learning passage** and **Robust04** automatic export, also install::

```bash
pip install 'consistency-ranker[ir]'
# or: pip install ir-datasets
```

### Step 2 — Download Datasets

```bash
# Download a single dataset
python scripts/download_datasets.py --dataset scidocs
python scripts/download_datasets.py --dataset fiqa
python scripts/download_datasets.py --dataset hotpotqa
python scripts/download_datasets.py --dataset bright
python scripts/download_datasets.py --dataset nfcorpus

# MS MARCO passage (always cap corpus size; default max_docs=100k if omitted)
python scripts/download_datasets.py --dataset msmarco_passage --max-docs 50000 --max-queries 5000

# TREC DL 2019 passage (requires ir-datasets)
python scripts/download_datasets.py --dataset trec_dl_passage --trec-dl-year 2019

# TREC Robust 2004 (requires ir-datasets; first run may download large shards)
python scripts/download_datasets.py --dataset robust04 --max-queries 250 --max-docs 50000

# Download a specific BRIGHT task/domain
python scripts/download_datasets.py --dataset bright --bright-task examples

# Download all datasets at once
python scripts/download_datasets.py --dataset all

# Limit size for quick experiments
python scripts/download_datasets.py --dataset hotpotqa --max-queries 200
```

> **Note on BRIGHT:** If BRIGHT cannot be downloaded automatically (authentication
> required or dataset not yet public), the script will create
> `data/raw/bright/README.md` with exact manual download steps.
>
> Current live configs (subject to upstream change) include:
> `examples`, `documents`, `long_documents`, `gpt4_reason`,
> `claude-3-opus_reason`, `llama3-70b_reason`, `Gemini-1.0_reason`, `grit_reason`.

### Step 3 — Prepare Datasets (Unified Format + Pairwise Preferences)

```bash
# Prepare a single dataset
python scripts/prepare_datasets.py --dataset scidocs
python scripts/prepare_datasets.py --dataset fiqa
python scripts/prepare_datasets.py --dataset hotpotqa
python scripts/prepare_datasets.py --dataset bright
python scripts/prepare_datasets.py --dataset nfcorpus
python scripts/prepare_datasets.py --dataset msmarco_passage
python scripts/prepare_datasets.py --dataset trec_dl_passage
python scripts/prepare_datasets.py --dataset robust04

# Prepare all datasets
python scripts/prepare_datasets.py --dataset all

# Customise preprocessing
python scripts/prepare_datasets.py --dataset scidocs --top-k 50 --max-queries 200 --seed 123
python scripts/prepare_datasets.py --dataset fiqa --weight-scheme binary
```

Each prepared dataset produces:
- `queries.jsonl`  — one `{"query_id": "...", "text": "..."}` per line
- `documents.jsonl` — one `{"doc_id": "...", "text": "...", "title": "..."}` per line
- `qrels.jsonl`    — one `{"query_id": "...", "doc_id": "...", "relevance": 0|1}` per line
- `pairwise/preferences.jsonl` — pairwise preferences derived from relevance grades

### Step 4 — Run Real-Data Experiments

```bash
# Baseline mode (label-derived pairwise DAG)
python scripts/run_real_experiment.py --dataset scidocs --max-queries 50 --top-k 20 --save-timings --profile

# Stress-test mode (synthetic conflict injection)
python scripts/run_real_experiment.py --dataset scidocs --preference-source qrels_flip --flip-prob 0.15 \
  --max-queries 50 --top-k 20 --save-timings --profile
```

**Metric-aware repair (optional):** by default FAS uses raw edge weights only. To bias removal toward a training-free DCG surrogate built from the same **score prior** as hybrid methods, use `--repair-weighting metric_aware`, or `--repair-weighting both` to also emit `*_ma` methods (e.g. `hybrid_rrf_copeland_a03` vs `hybrid_rrf_copeland_a03_ma`) for side-by-side CSV columns. Formula: `w_new = w_conf × (1 + β × u)` with `u ≈ |gain_i − gain_j| × |discount(pos_i) − discount(pos_j)|`. See `src/consistency_ranker/metric_aware_repair.py` and `--metric-aware-*` CLI flags.

```bash
# Plain vs metric-aware hybrids in one run (adds *_ma method names)
python scripts/run_real_experiment.py --dataset scidocs --max-queries 30 --top-k 20 \
  --repair-weighting both --include-hybrid-ablation --overwrite-existing
```

### Main real-signal experiment (recommended): `votes_file`

1) Generate score files from multiple free rankers (`bm25`, `tfidf`, `minilm`) using a shared query-id file:

```bash
python scripts/generate_score_file.py --dataset scidocs --ranker bm25 \
  --max-queries 50 --top-n 50 --seed 42 \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --output outputs/real_signal/scidocs/scores_bm25.jsonl

python scripts/generate_score_file.py --dataset scidocs --ranker tfidf \
  --max-queries 50 --top-n 50 --seed 42 \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --output outputs/real_signal/scidocs/scores_tfidf.jsonl

python scripts/generate_score_file.py --dataset scidocs --ranker minilm \
  --max-queries 50 --top-n 50 --seed 42 \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --output outputs/real_signal/scidocs/scores_minilm.jsonl
```

2) Build ranker-vote pairwise edges (Votes v2 recommended):

```bash
python scripts/build_votes_file.py --dataset scidocs \
  --score-files \
    outputs/real_signal/scidocs/scores_bm25.jsonl \
    outputs/real_signal/scidocs/scores_tfidf.jsonl \
    outputs/real_signal/scidocs/scores_minilm.jsonl \
  --top-k 20 \
  --vote-weight-scheme margin \
  --min-vote-margin 0.05 \
  --abstain-missing \
  --min-support 2 \
  --min-aggregate-margin 0.1 \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --output outputs/real_signal/scidocs/votes.jsonl
```

Votes v2 knobs:
- `--vote-weight-scheme {binary,margin}` (default `binary`)
- `--min-vote-margin` (abstain below this per-ranker margin)
- `--abstain-missing` (skip comparisons when either doc score is missing)
- `--min-support` (minimum voters supporting a directed edge)
- `--min-aggregate-margin` (minimum summed margin per directed edge)
- `--ranker-weighting {none,auto_ndcg_at_k,auto_precision_at_k,from_file}` (optional ranker reliability weighting)
- `--ranker-weights-file /path/to/weights.json` (required with `from_file`; format: `{"bm25": 0.9, "tfidf": 1.0, "minilm": 1.2}`)

3) Run the experiment with `votes_file` (main real-signal path):

```bash
python scripts/run_real_experiment.py --dataset scidocs --preference-source votes_file \
  --pairwise-file outputs/real_signal/scidocs/votes.jsonl \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --score-prior-files \
    outputs/real_signal/scidocs/scores_bm25.jsonl \
    outputs/real_signal/scidocs/scores_tfidf.jsonl \
    outputs/real_signal/scidocs/scores_minilm.jsonl \
  --max-queries 50 --top-k 20 --save-timings --profile --no-plots
```

When you pass **one or more** `--score-prior-files`, the pipeline also evaluates three **multi-ranker fusion** baselines that do not use graph repair:

- **RRF** (method id `rrf`): per ranker, sort by score (`doc_id` tie-break); RRF(d) = Σ<sub>s</sub> 1/(k + rank<sub>s</sub>(d)) with default **k = 60** (Cormack, Clarke, Buettcher, SIGIR 2009). Override with `--rrf-k`. Missing documents contribute 0 per ranker.

- **CombSUM** (method id `combsum`): CombSUM(d) = Σ<sub>s</sub> normalized<sub>s</sub>(d). Default **`--combsum-normalization minmax`**: per query and per ranker, min–max scores to [0, 1]; if all scores in that ranker are equal, normalized values are **0** (no discriminative signal from that ranker for that query). Use **`none`** to sum raw scores (only sensible when scales are comparable). Missing documents contribute 0 per ranker. Tie-break: higher CombSUM, then better best rank, then `doc_id` (Fox & Shaw–style combination; see also Lee, SIGIR 1997).

- **Borda list fusion** (method id **`borda_fuse`**): partial-list Borda over the same score JSONLs. Let **U<sub>q</sub>** be the union of `doc_id`s appearing in the score-prior files for that query and **N<sub>q</sub> = |U<sub>q</sub>|**. After the usual per-ranker sort (descending score, `doc_id` tie-break), assign **borda_points<sub>s</sub>(d) = N<sub>q</sub> − rank<sub>s</sub>(d)** if *d* appears in ranker *s*, else **0**; **Borda(d) = Σ<sub>s</sub> borda_points<sub>s</sub>(d)** (Dwork et al., WWW 2001). Tie-break: higher Borda score, then better best rank, then `doc_id`. This uses **rank positions only** (like RRF), not raw score magnitude (unlike CombSUM).

**Naming:** graph **`borda`** in `baseline_ranking` is **tournament / preference-graph** Borda (out-neighbor counts on the vote graph). **`borda_fuse`** is **retrieval-list** Borda on `--score-prior-files` only. They can both appear in one run under different method ids.

**Not** the same as graph **`score_sum`**: the existing `score_sum` method sums **outgoing edge weights** on the pairwise preference graph; **`combsum`** / **`borda_fuse`** fuse **retrieval scores** from `--score-prior-files`. All can appear in the same experiment CSV.

**Graph-native Markov / Rank Centrality** (no score priors): **`markov_graph`** runs a Rank Centrality–style Markov chain on the **raw** query preference graph; **`markov_graph_repaired`** runs the same construction on the **greedy-FAS–repaired DAG**. Edge `u → v` with weight `w` means *u is preferred over v*. Rows of the transition matrix are `P_ij ∝` (weight of `j → i`) for `j ≠ i`, scaled so each row sums to 1 (Negahban, Oh, Shah, OR 2016). Stationary mass is computed by power iteration with **uniform teleportation** **`--markov-damping`** (default **0.15**, same role as PageRank’s restart mass). This is **not** the same as **`pagerank`**, which applies NetworkX PageRank to the **transposed** graph for an “authority” interpretation. Tie-break: higher stationary mass, then lower **weighted in-degree**, then `doc_id`. Unlike **`greedy_fas_copeland`** (Copeland on the repaired DAG) or **`greedy_fas_weighted_balance`**, this is a **global** Markov solution on the full node set, not a local win-count or out-minus-in heuristic.

Optional weaker mode (`score_file`):

```bash
python scripts/run_real_experiment.py --dataset scidocs --preference-source score_file \
  --score-file outputs/real_signal/scidocs/scores_minilm.jsonl \
  --query-id-file outputs/real_signal/scidocs/query_ids.txt \
  --max-queries 50 --top-k 20 --save-timings --profile --no-plots
```

Expected external file formats:
- `scores.jsonl`: `{"query_id": "...", "doc_id": "...", "score": 1.23}`
- `votes.jsonl`: `{"query_id": "...", "winner_doc_id": "...", "loser_doc_id": "...", "weight": 1.0, "voter": "bm25"}`

**Interpretation note (important):**
- `preference-source=qrels_flip` uses **synthetic corruption** (random edge flips).
- `preference-source=votes_file` is the **main real-signal experiment** because it captures disagreement across rankers and can create non-trivial cycles.
- `preference-source=score_file` is typically weaker for consistency analysis because a single score list is often close to transitive.
- Qrels remain evaluation labels in all modes.
- Primary ranking-quality metric in `run_real_experiment.py` is candidate-aligned `nDCG@k` (with MAP@k, Precision@k, Recall@k, and pairwise accuracy also reported). Kendall tau is secondary.
- Hybrid post-repair methods can consume `--score-prior-files` to combine ranker score priors with repaired-graph consistency signals.
- The **`rrf`**, **`combsum`**, and **`borda_fuse`** methods are standard multi-list fusion baselines (same score files as hybrids); they do not use graph repair.
- **`markov_graph`** and **`markov_graph_repaired`** are standalone graph Markov baselines (no `--score-prior-files` required).

### BRIGHT — Manual Download (if needed)

If `python scripts/download_datasets.py --dataset bright` fails, follow these steps:

1. Visit <https://huggingface.co/datasets/xlangai/BRIGHT> and accept any licence terms.
2. Log in to HuggingFace CLI (if the dataset is gated):
   ```bash
   huggingface-cli login
   ```
3. Download the dataset:
   ```python
   from datasets import load_dataset
   ds = load_dataset("xlangai/BRIGHT", "examples")
   ```
4. Export to JSONL and place files in `data/raw/bright/`:
   - `queries.jsonl`
   - `documents.jsonl`
   - `qrels.jsonl`
   - accepted query keys: `query_id` or `id`; text keys: `text` or `query` or `question`
   - accepted document keys: `doc_id` or `id` (plus `text`, optional `title`)
   - accepted qrels keys: `query_id`/`query-id`, `doc_id`/`corpus-id`, `relevance`/`score`
5. Then run:
   ```bash
   python scripts/prepare_datasets.py --dataset bright
   ```

---

## Timing & Profiling

Every pipeline stage is instrumented with wall-clock timers.  Use the flags
below to inspect bottlenecks without changing any source code.

### Timing Utility (`src/consistency_ranker/utils/timing.py`)

```python
from consistency_ranker.utils.timing import Timer, TimingAccumulator, timed

acc = TimingAccumulator()

# Context manager
with Timer("graph_build", accumulator=acc):
    graph = build_graph(prefs)

# Decorator
@timed("greedy_fas", accumulator=acc)
def run_fas(g):
    return greedy_fas(g)

acc.print_summary()
acc.save_csv("outputs/timings/stages.csv")
acc.save_json("outputs/timings/stages.json")
```

### Running a Profiling Experiment

```bash
# Run with timing summary printed to console + saved to disk
python scripts/run_synthetic.py --n-items 50 --noise 0.1 --save-timings --profile

# Scale sweep for runtime-vs-n_items plot
for n in 10 20 50 100; do
    python scripts/run_synthetic.py --n-items $n --save-timings \
        --output-dir outputs/scale_$n
done

# Generate all plots
python scripts/plot_timings.py --input outputs/timings/synthetic_timings.json
python scripts/plot_timings.py \
    --scale-dirs outputs/scale_10 outputs/scale_20 outputs/scale_50 outputs/scale_100
```

### Where Timings Are Saved

```
outputs/
├── timings/
│   ├── synthetic_timings.csv    # summary table (stage, n_calls, total_s, mean_s, median_s, max_s)
│   └── synthetic_timings.json   # summary + raw per-call values + metadata
├── plots/
│   ├── runtime_by_stage.png     # horizontal bar chart of total runtime per stage
│   ├── runtime_breakdown_pie.png  # proportional breakdown by stage
│   ├── runtime_by_method.png    # bar chart: ranking methods + solver
│   └── runtime_vs_n_items.png   # line chart from scale sweep
└── synthetic_results.json       # experiment results include a "timings" key
```

### Expected Bottlenecks

| Stage | Expected cost | Notes |
|-------|--------------|-------|
| `greedy_fas_solver` | **O(C · (n+e))** | Dominant for n > 30; C = removal iterations ≤ e |
| `graph_construction` | O(e) | Linear in edges; fast in practice |
| `cycle_detection` (SCC) | O(n + e) | Very fast; full enumeration is exponential — avoided |
| `ranking_score_sum` | O(n + e) | Fast |
| `ranking_borda` | O(n + e) | Graph tournament Borda (preference graph) |
| `ranking_borda_fuse` | O(n · rankers) | Borda count over score-prior lists per query |
| `ranking_markov_graph` | O(n² · iter) | Rank Centrality–style power iteration (sparse small n) |
| `ranking_markov_graph_repaired` | O(n² · iter) | Same on FAS-repaired DAG |
| `evaluation` | O(n²) | Quadratic in items due to all-pairs Kendall τ |

### Three Concrete Optimization Suggestions

1. **Cache the graph deep-copy in `greedy_fas`:** currently `copy.deepcopy`
   is called once per experiment.  For repeated calls (e.g. sweep over many
   queries) the copy cost dominates.  Use `graph.copy()` (shallow) if edge
   attributes are not mutated, or pass a mutable flag.

2. **Replace full Johnson cycle-enumeration with SCC-based heuristics:**
   `find_simple_cycles` is exponential for dense graphs.  In the pipeline we
   already skip it, but if cycle counts are needed, use the SCC size
   distribution as a proxy — O(n + e) instead of exponential.

3. **Vectorize Kendall τ with scipy or numpy:** the current all-pairs loop in
   `kendall_tau` is O(n²) pure Python.  `scipy.stats.kendalltau` (C
   implementation) is 10–100× faster for n > 100.

---

## Current Status

| Area | Status |
|---|---|
| Core library (`src/consistency_ranker/`) | ✅ Implemented and unit-tested (see `pytest`) |
| Synthetic experiments | ✅ Executed (noise sweep, scale sweep, multi-seed) |
| Real-data pipeline — four benchmarks | ✅ Publication-facing tables/plots in `outputs/pub_vote_cmp_all4/paper_package/` |
| Bootstrap significance analysis | ✅ Executed (2000 reps; tables in paper packages where applicable) |
| Real-data pipeline — per-dataset full trees | ⚙️ Additional runs may live under `outputs/real_full/` (not all committed) |
| Exact ILP MWFAS solver (Gurobi) | ✅ Implemented in `mwfas_solver.py` (optional dependency) |
| LLM pairwise preferences | ⏳ Planned; current publication experiments use score-derived votes |

**Environment note:** Downloading raw benchmarks requires HuggingFace Hub access; some CI/sandboxes block `huggingface.co`. See [`docs/DATASET_ACCESS_DIAGNOSIS.md`](docs/DATASET_ACCESS_DIAGNOSIS.md).

**What is not yet implemented:** Real LLM pairwise comparator; cross-encoder ranker.

---

## Limitations / Honest Interpretation

These limitations must be understood before drawing conclusions from this repository:

1. **Vote source:** All experiments use pairwise votes derived from BM25, TF-IDF, and MiniLM-L6 *scores* — not from actual LLM pairwise judgements. Findings may not transfer directly to LLM-generated preferences.

2. **Dataset breadth:** The committed paper packages summarize multiple benchmarks, but
   query counts and filtering differ per dataset — read `MANUSCRIPT_SUMMARY.md` in the
   relevant `paper_package/` directory.

3. **Direction of effect:** Under the conditions tested, FAS repair *harms* retrieval effectiveness (negative ΔnDCG) when cycles are abundant, and is *inactive* when they are rare. There is no condition in the committed evidence where repair is unconditionally beneficial.

4. **Structural metrics are not independent:** BEW and PIC measure graph–label alignment against the same qrels used to compute nDCG. A decrease in BEW/PIC is expected by construction and does not imply an improvement in retrieval quality.

5. **Exact solver availability:** The Gurobi-backed ILP path in `mwfas_solver.py` requires a
   licensed Gurobi install. Greedy FAS remains the default in many scripts; older CSV notes in
   `docs/tables/` may pre-date the exact path.

6. **Scale:** Only n ≤ 100 items tested in synthetic experiments. Real-world graph densities and sizes may differ substantially.

See [`docs/SAFE_CLAIMS_FOR_PAPER.md`](docs/SAFE_CLAIMS_FOR_PAPER.md) for a full set of safe and unsafe claims, and [`docs/EVIDENCE_MAP.md`](docs/EVIDENCE_MAP.md) for the claim-to-evidence mapping.

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
