# Dataset Access Diagnosis: FiQA and BRIGHT

> **Purpose:** Evidence-based, environment-specific diagnosis of why FiQA and BRIGHT
> are not currently usable in this repository.  Every conclusion is grounded in
> tested commands and committed file paths — not guesses.
>
> **Environment probed:** CI/sandbox runner, 2026-03-22.
> Python 3.12.3 (`/usr/bin/python3`).

---

## 1. Summary Table

| Criterion | FiQA | BRIGHT |
|---|---|---|
| Code support implemented | ✅ Yes | ✅ Yes |
| `datasets` / `huggingface-hub` **installed in this env** | ❌ No | ❌ No |
| HuggingFace network reachable from this env | ❌ No | ❌ No |
| Raw files present (`data/raw/…`) | ❌ No | ❌ No |
| Processed files present (`data/processed/…`) | ❌ No | ❌ No |
| Publication outputs present | ⚠️ Partial / see §10 | ⚠️ Partial / see §10 |
| Dataset gated / requires login | ❓ Unknown (cannot check without network) | ❓ Unknown (code assumes possible gating) |
| Blocking issue #1 | `ModuleNotFoundError: No module named 'datasets'` | `ModuleNotFoundError: No module named 'datasets'` |
| Blocking issue #2 | DNS resolution failure for `huggingface.co` | DNS resolution failure for `huggingface.co` |
| Blocking issue #3 | No raw or processed JSONL files | No raw or processed JSONL files |
| Issue side | Environment + data | Environment + data |
| Repository code correct | ✅ Yes (with one gap — see §7) | ✅ Yes |

---

## 2. Current Accessibility Status

### State definitions

| State | Meaning |
|---|---|
| **Code supports** | Loader, download script, registry entry, and experiment script all exist |
| **Raw data can be obtained** | `pip install datasets && python scripts/download_datasets.py --dataset X` would succeed |
| **Publication outputs exist** | Pre-committed per-query / summary CSV files in `outputs/` |

| Dataset | Code supports | Raw data obtainable here | Publication outputs exist |
|---|---|---|---|
| FiQA | ✅ Yes | ❌ No | ⚠️ See §9–10 (`pub_vote_cmp_all4` may be on `main`) |
| BRIGHT | ✅ Yes | ❌ No | ⚠️ See §9–10 (`pub_vote_cmp_all4` may be on `main`) |

---

## 3. Root Cause of Inaccessibility

Both datasets share the same two root causes.

### Root Cause A — Missing Python packages

**Evidence (tested 2026-03-22):**
```bash
$ python3 -c "import datasets"
ModuleNotFoundError: No module named 'datasets'

$ python3 -c "import huggingface_hub"
ModuleNotFoundError: No module named 'huggingface_hub'

$ pip show datasets huggingface-hub
WARNING: Package(s) not found: datasets
WARNING: Package(s) not found: huggingface-hub
```

`datasets` and `huggingface-hub` are listed in `requirements.txt` and `pyproject.toml`
(`datasets>=2.18,<4.0`, `huggingface-hub>=0.21`) but are **not installed** in the current
system Python 3.12 environment.

**What this means:**
- `python scripts/download_datasets.py --dataset fiqa` exits immediately with:
  ```
  ERROR: The 'datasets' library is not installed.
  Install it with:  pip install datasets huggingface-hub
  ```

---

### Root Cause B — HuggingFace network blocked (DNS failure)

**Evidence (tested 2026-03-22):**
```bash
$ python3 -c "import socket; socket.gethostbyname('huggingface.co')"
OSError: [Errno -3] Temporary failure in name resolution

$ python3 -c "import socket; socket.gethostbyname('github.com')"
# → 140.82.116.4  (github.com resolves fine)
```

HuggingFace's domain `huggingface.co` is **DNS-blocked** in this environment.
GitHub and general internet are reachable; the block is specific to `huggingface.co`.

**Confirmed with `datasets` installed (in a temporary venv):**
```
# FiQA attempt
RuntimeError: Cannot send a request, as the client has been closed.
# Error chain: [Errno -5] No address associated with hostname → datasets RuntimeError

# BRIGHT attempt
BrightNotAvailableError: Unexpected error downloading BRIGHT (RuntimeError):
  Cannot send a request, as the client has been closed.
```

---

### Root Cause C — No local data files exist

**Evidence:**
```bash
$ ls data/raw/beir/fiqa/
.gitkeep    # placeholder only

$ ls data/raw/bright/
.gitkeep  README.md    # placeholder + manual instructions only

$ ls data/processed/beir/fiqa/
.gitkeep  pairwise/   # placeholder + empty pairwise dir

$ ls data/processed/bright/
.gitkeep  pairwise/   # same
```

Neither raw (`queries.jsonl`, `documents.jsonl`, `qrels.jsonl`) nor processed JSONL
files exist for FiQA or BRIGHT.  No Hugging Face local cache exists either.

---

### Root Cause D — Publication pipeline vs. large per-query outputs

Some **paper-facing** scripts historically defaulted to two datasets, while the
full experiment stack supports four benchmarks. Check the current contents of
`scripts/build_paper_evidence_package.py` and `scripts/summarize_publication_vote_suite.py`.

Aggregated manuscript tables/plots for the four-dataset vote-comparison run may
live under `outputs/pub_vote_cmp_all4/paper_package/` when committed — this is
distinct from huge per-query CSV trees that remain gitignored.

---

## 4. Exact Commands Expected to Work (on a Networked Machine)

### FiQA — full pipeline

```bash
# Step 0: Install required packages (once per environment)
pip install datasets huggingface-hub
# or: pip install -r requirements.txt && pip install -e ".[dev]"

# Step 1: Download raw data from HuggingFace BEIR
python scripts/download_datasets.py --dataset fiqa
# Writes:
#   data/raw/beir/fiqa/queries.jsonl
#   data/raw/beir/fiqa/documents.jsonl
#   data/raw/beir/fiqa/qrels.jsonl

# Step 2: Prepare into processed format + generate pairwise preferences
python scripts/prepare_datasets.py --dataset fiqa
# Writes:
#   data/processed/beir/fiqa/queries.jsonl
#   data/processed/beir/fiqa/documents.jsonl
#   data/processed/beir/fiqa/qrels.jsonl
#   data/processed/beir/fiqa/pairwise/preferences.jsonl
```

### BRIGHT — full pipeline

```bash
# Step 0: Install required packages
pip install datasets huggingface-hub

# Step 1a: Attempt automatic download
python scripts/download_datasets.py --dataset bright --bright-task examples

# Step 1b (if 1a fails — e.g. gated dataset):
# 1. Visit https://huggingface.co/datasets/xlangai/BRIGHT
# 2. Accept licence/terms
# 3. huggingface-cli login
# 4. Export to JSONL: queries.jsonl, documents.jsonl, qrels.jsonl
# 5. Place files in: data/raw/bright/
# (See data/raw/bright/README.md for full instructions)

# Step 2: Prepare
python scripts/prepare_datasets.py --dataset bright
```

---

## 5. Exact Missing Prerequisites

### Environment prerequisites (both datasets)

| Prerequisite | Status | Fix |
|---|---|---|
| `pip install datasets>=2.18,<4.0` | ❌ Not installed | `pip install datasets huggingface-hub` |
| `pip install huggingface-hub>=0.21` | ❌ Not installed | same |
| Network access to `huggingface.co` | ❌ DNS-blocked | Run from a machine with unrestricted internet |
| HuggingFace login (if datasets are gated) | ❓ Unknown | `huggingface-cli login` |

### Data prerequisites (both datasets)

| Prerequisite | Status | Fix |
|---|---|---|
| `data/raw/beir/fiqa/queries.jsonl` | ❌ Missing | Run download step |
| `data/raw/beir/fiqa/documents.jsonl` | ❌ Missing | Run download step |
| `data/raw/beir/fiqa/qrels.jsonl` | ❌ Missing | Run download step |
| `data/raw/bright/queries.jsonl` | ❌ Missing | Run download step or manual export |
| `data/raw/bright/documents.jsonl` | ❌ Missing | Run download step or manual export |
| `data/raw/bright/qrels.jsonl` | ❌ Missing | Run download step or manual export |

---

## 6. Issue Classification

| Issue type | FiQA | BRIGHT |
|---|---|---|
| (a) Missing raw files | ✅ Yes | ✅ Yes |
| (b) Missing processed files | ✅ Yes | ✅ Yes |
| (c) Missing committed outputs | ⚠️ Depends on branch | ⚠️ Depends on branch |
| (d) Missing internet access (DNS-blocked) | ✅ Yes | ✅ Yes |
| (e) Missing Python package | ✅ Yes (`datasets`, `huggingface-hub`) | ✅ Yes |
| (f) Missing HuggingFace authentication | ❓ Unknown | ❓ Possible |
| (g) Gated dataset terms | ❓ Unknown (cannot verify without network) | ❓ Possible |
| (h) Broken script/path bug | ⚠️ Partial (see §7 — fixed in this PR) | ✅ No |
| Repo-side issue | No (code is correct) | No (code is correct) |
| Environment-side issue | ✅ Yes (no packages, no network) | ✅ Yes |
| Data-side issue | ✅ Yes (no files) | ✅ Yes |

---

## 7. Repository Code Gap Discovered and Fixed

### Problem

**`beir_loader.download_beir_dataset` did not catch network errors.**

`bright_loader.download_bright` wraps all `load_dataset` calls in a broad
`except Exception` handler that re-raises as `BrightNotAvailableError` with a helpful
message. `beir_loader.download_beir_dataset` only caught `ImportError`, so if `datasets`
was installed but HuggingFace was unreachable, FiQA download crashed with an unhandled
`RuntimeError` from the `datasets` library.

**Observed error (before fix):**
```
Exception type: RuntimeError
Message: Cannot send a request, as the client has been closed.
```

### Fix Applied

- Added `BeirNotAvailableError(RuntimeError)` class to `beir_loader.py`, mirroring
  `BrightNotAvailableError`.
- Wrapped all three `load_dataset` calls in `download_beir_dataset` with:
  - `except (OSError, ConnectionError, ValueError)` → raises `BeirNotAvailableError`
  - `except Exception` (catch-all) → raises `BeirNotAvailableError`
- Updated `download_datasets.py::download_beir` to catch `BeirNotAvailableError`
  and print a friendly message (matching BRIGHT's behavior).

---

## 8. Exact Manual Steps the Repository Owner Must Take

### Option A — Run from a networked machine (recommended)

1. Clone the repository on a machine with unrestricted internet access.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt && pip install -e ".[dev]"
   ```
3. Download FiQA:
   ```bash
   python scripts/download_datasets.py --dataset fiqa
   python scripts/prepare_datasets.py --dataset fiqa
   ```
4. Download BRIGHT:
   ```bash
   python scripts/download_datasets.py --dataset bright --bright-task examples
   # If gated: follow data/raw/bright/README.md for manual steps
   python scripts/prepare_datasets.py --dataset bright
   ```

### Option B — Copy pre-prepared JSONL files

If the owner has run the download+prepare steps elsewhere:
```bash
# Copy raw files into the repo
cp -r /path/to/prepared/data/raw/beir/fiqa  data/raw/beir/
cp -r /path/to/prepared/data/raw/bright     data/raw/

# Then prepare locally (no network needed):
python scripts/prepare_datasets.py --dataset fiqa
python scripts/prepare_datasets.py --dataset bright
```

---

## 9. Three States Clearly Distinguished

### FiQA

| State | Status | Evidence |
|---|---|---|
| 1. Code supports FiQA | ✅ Yes | `dataset_registry.py` entry; `beir_loader.py`; `download_datasets.py::download_beir`; `prepare_datasets.py::prepare_beir`; `run_real_experiment.py --dataset fiqa` |
| 2. Raw data can be obtained in this environment | ❌ No | `datasets` not installed; `huggingface.co` DNS-blocked |
| 3. Publication outputs exist | ⚠️ See note | Aggregated bundle may exist at `outputs/pub_vote_cmp_all4/paper_package/`; raw per-query CSVs may remain uncommitted. |

### BRIGHT

| State | Status | Evidence |
|---|---|---|
| 1. Code supports BRIGHT | ✅ Yes | `dataset_registry.py` entry; `bright_loader.py`; `download_datasets.py::download_bright`; `prepare_datasets.py::prepare_bright`; `run_real_experiment.py --dataset bright` |
| 2. Raw data can be obtained in this environment | ❌ No | `datasets` not installed; `huggingface.co` DNS-blocked; possible additional gating on `xlangai/BRIGHT` |
| 3. Publication outputs exist | ⚠️ See note | Same as FiQA — check `outputs/pub_vote_cmp_all4/paper_package/` on `main`. |

---

## 10. Alternate environment: networked HPC (e.g. Wulver-class clusters)

Sections 1–9 above describe a **strict offline / DNS-blocked** CI-style environment.
On many research clusters, Hugging Face **is** reachable and `datasets` /
`huggingface-hub` are installed. A separate probe on such a machine (2026-03) found:

- **FiQA:** HF file listings and direct downloads can succeed, but **BEIR script-style**
  loading may fail on `datasets>=4` (e.g. *Dataset scripts are no longer supported*).
  The repo pins `datasets<4` in `pyproject.toml` — use a compatible virtualenv or
  manually materialise `data/raw/beir/fiqa/{queries,documents,qrels}.jsonl`, then run
  `prepare_datasets.py`.
- **BRIGHT:** `bright_loader.download_bright(...)` smoke tests succeeded when HF was
  reachable; populate `data/raw/bright/` then `prepare_datasets.py`.
- **Large `outputs/` trees** (e.g. `outputs/real_full/`) may exist on a developer
  machine but are often **not** committed; the manuscript-facing **aggregated**
  tables/plots may appear under `outputs/pub_vote_cmp_all4/paper_package/` on `main`.

This appendix does **not** contradict §§1–9: it documents different network and
dependency assumptions.

