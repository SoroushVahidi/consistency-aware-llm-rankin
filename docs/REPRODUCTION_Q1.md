# Reproduction Guide (Q1 Journal Package)

> **Purpose:** Exact commands to reproduce every result referenced in the
> journal manuscript, from environment setup through final tables and figures.
> The guide is self-contained and uses only standard shell commands.
> Canonical publication evidence for the vote-comparison paper is committed under
> `outputs/pub_vote_cmp_all4/paper_package/` (four datasets). This guide rebuilds the
> **historical** Q1 journal bundle derived from the earlier two-dataset
> `outputs/pub_vote_cmp_v2/` package; keep those numbers separate from the all4 package.

---

## 1. Environment Setup

### 1.1 Prerequisites

- **Python 3.11 or 3.12** (repo uses 3.12 in CI).
- Git and a Unix-like shell (tested on Ubuntu 22.04).
- Network access to PyPI for package installation.
- For real-data experiments: network access to Hugging Face Hub (may be blocked
  in restricted environments — see §5).

### 1.2 Clone and Install

```bash
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install package and dev dependencies
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 1.3 Verify Environment

```bash
python scripts/check_repo_ready.py
```

Expected output: all checks pass (import, key files, test discovery, output
directories).

### 1.4 Run Tests

```bash
pytest
```

Expected: 186 tests pass in < 5 seconds.

---

## 2. Synthetic Experiments

Synthetic experiments require no downloaded data.

### 2.1 Single Synthetic Run (quick smoke test)

```bash
python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42
```

Output: `outputs/noise_sweep_n0.20/` (JSON result file).

### 2.2 Full Noise Sweep

```bash
for NOISE in 0.05 0.10 0.15 0.20 0.25 0.30; do
  python scripts/run_synthetic.py --n-items 20 --noise $NOISE --seed 42 \
    --output-dir outputs/noise_sweep_n${NOISE}
done
```

### 2.3 Multi-Seed Replication (n=20, noise=0.20)

```bash
for SEED in 42 123 456 789 1234; do
  python scripts/run_synthetic.py --n-items 20 --noise 0.20 --seed $SEED \
    --weight-scheme margin \
    --output-dir outputs/margin_multiseed_n20_noise0.20/seed_$SEED
  python scripts/run_synthetic.py --n-items 20 --noise 0.20 --seed $SEED \
    --weight-scheme uniform \
    --output-dir outputs/uniform_multiseed_n20_noise0.20/seed_$SEED
done
```

### 2.4 Scale Sweep

```bash
for N in 10 20 50 100; do
  python scripts/run_synthetic.py --n-items $N --noise 0.10 --seed 42 \
    --output-dir outputs/scale_sweep_n$N
done
```

### 2.5 Expected Output Paths

| Experiment | Output location |
|---|---|
| Noise sweep | `outputs/noise_sweep_n{noise}/` |
| Multi-seed margin | `outputs/margin_multiseed_n20_noise0.20/seed_{seed}/` |
| Multi-seed uniform | `outputs/uniform_multiseed_n20_noise0.20/seed_{seed}/` |
| Scale sweep | `outputs/scale_sweep_n{n}/` |

### 2.6 Approximate Runtime

- Single run (n=20, noise=0.20): < 0.1 s.
- Full noise sweep (6 points): < 1 s.
- Scale sweep n=100: ~1.5 s.
- Multi-seed (5×2 runs): < 5 s.

---

## 3. Real-Data Experiments

### 3.1 Download Datasets

Requires Hugging Face Hub network access.

```bash
python scripts/download_datasets.py --dataset scidocs
python scripts/download_datasets.py --dataset hotpotqa
# Optional (extend paper package to more datasets):
python scripts/download_datasets.py --dataset fiqa
python scripts/download_datasets.py --dataset bright
```

Downloaded files land in `data/raw/beir/scidocs/`, `data/raw/hotpotqa/`,
`data/raw/beir/fiqa/`, `data/raw/bright/` respectively.

### 3.2 Prepare Datasets

```bash
python scripts/prepare_datasets.py --dataset scidocs
python scripts/prepare_datasets.py --dataset hotpotqa
# Optional:
python scripts/prepare_datasets.py --dataset fiqa
python scripts/prepare_datasets.py --dataset bright
```

Output: `data/processed/beir/scidocs/`, `data/processed/hotpotqa/`, etc.

### 3.3 Run Publication Vote Suite (SciDocs + HotpotQA)

```bash
python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2
```

This script orchestrates the full pipeline for both datasets across the three
vote constructions (ms2, ms1, ms1_drop_mutual):

1. Generates score files (BM25, TF-IDF, MiniLM).
2. Builds vote files for each construction.
3. Runs the ranking experiment (`run_real_experiment.py`) for each combination.

**Approximate runtime:** 15–45 min per dataset depending on hardware.

### 3.4 Optional: Extend to FiQA and BRIGHT

Edit `scripts/run_publication_vote_suite.py`: add `"fiqa"` and/or `"bright"`
to the `DATASETS` list, then re-run with `--root outputs/pub_vote_cmp_v2`.

### 3.5 Bootstrap ΔnDCG Analyses

```bash
ROOT="outputs/pub_vote_cmp_v2"
mkdir -p "${ROOT}/analysis"

for DS in scidocs hotpotqa; do
  for VAR in ms2 ms1 ms1_drop_mutual; do
    CSV="${ROOT}/${DS}/${VAR}/${DS}/votes_file/${DS}_per_query.csv"
    if [ ! -f "${CSV}" ]; then
      echo "Skipping missing ${CSV}"; continue
    fi
    python scripts/analyze_publication_vote_deltas.py \
      --per-query-csv "${CSV}" \
      --dataset "${DS}" \
      --variant "${VAR}" \
      --outdir "${ROOT}/analysis"
  done
done
```

### 3.6 Build Paper Evidence Package

```bash
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
```

Output: `outputs/pub_vote_cmp_v2/paper_package/` containing:

| File | Description |
|---|---|
| `tables/table_graph_ndcg_and_consistency.csv` | Main results: nDCG + structural metrics per dataset × vote construction |
| `tables/table_bootstrap_delta_ndcg.csv` | Bootstrap ΔnDCG (repaired − unrepaired) per method pair |
| `tables/table_consistency_qrels_bew.csv` | BEW pre/post repair per dataset × vote construction |
| `plots/fig_cyclicity_and_scc.png` | Bar charts: % cyclic and avg SCC by construction |
| `plots/fig_mean_ndcg_hybrids.png` | nDCG@k means across methods and constructions |
| `plots/fig_graph_qrels_bew_pre_post.png` | BEW pre vs post FAS repair |
| `plots/fig_delta_ndcg_bootstrap.png` | Bootstrap CI plots for ΔnDCG |
| `MANUSCRIPT_SUMMARY.md` | Human-readable interpretation of all tables |

---

## 4. Q1 Journal Package (Aggregated Tables)

The following command regenerates the aggregated Q1 journal package from all
available committed and freshly computed outputs:

```bash
python scripts/generate_q1_tables.py \
  --pub-root outputs/pub_vote_cmp_v2 \
  --synth-results docs/tables/main_results.csv \
  --out-dir outputs/q1_journal_package
```

Output structure under `outputs/q1_journal_package/`:

| File | Description |
|---|---|
| `table_main_performance.csv` | Per-dataset × vote construction mean nDCG for all methods |
| `table_structural_consistency.csv` | BEW/PIC pre/post FAS repair |
| `table_per_dataset_summary.csv` | One row per dataset: best method, ΔnDCG, significance |
| `table_significance.csv` | Bootstrap CI + significance labels (✓ / − / ✗) |
| `table_regime_analysis.csv` | SCC-stratified ΔnDCG (high vs low cyclicity) |
| `table_failure_cases.csv` | Cases where repair yields ΔnDCG < −0.005 |
| `summary_report.md` | Human-readable narrative of all table findings |

---

## 4.1 Manuscript-Support CSV Bundle (`reports/paper_tables/`)

Generate additional machine-readable tables for manuscript drafting:

```bash
python scripts/generate_paper_tables.py --out-dir reports/paper_tables
```

This produces:
- `table_01_repair_effects.csv`
- `table_02_proxy_baseline_leaderboard.csv`
- `table_03_synthetic_multiseed_stability.csv`
- `table_04_synthetic_noise_sweep.csv`
- `table_05_failure_context.csv`
- `table_06_artifact_inventory.csv`

---

## 5. Notes on Restricted Environments

If Hugging Face Hub access is blocked (e.g. sandbox environments):

- **Synthetic experiments** run fully offline — no network required.
- **Pre-computed real-data results** are committed under
  `outputs/pub_vote_cmp_v2/paper_package/` and can be used to regenerate the
  paper package tables without re-running the full pipeline:

  ```bash
  python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
  ```

  This only requires the `paper_package/` subdirectory to already exist (it
  is committed to git).

- The `scripts/generate_q1_tables.py` script reads from the committed
  `docs/tables/main_results.csv` and the pre-committed
  `outputs/pub_vote_cmp_v2/paper_package/tables/` files and can run fully
  offline.

---

## 6. Verification

After running the commands above, verify outputs exist:

```bash
python scripts/check_repo_ready.py
```

Key files checked:

- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/q1_journal_package/table_main_performance.csv` (after generate_q1_tables)
- `docs/tables/main_results.csv`

---

## 7. Citing Pre-Committed Results

The following outputs are committed directly in the repository and require no
re-computation to read or cite:

| Path | Contents |
|---|---|
| `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv` | Main real-data results (SciDocs, HotpotQA; 3 vote constructions) |
| `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` | Bootstrap ΔnDCG, 2000 reps, per method pair |
| `docs/tables/main_results.csv` | Synthetic sweep summary (all noise levels, seeds, scale points) |
| `docs/tables/regime_analysis.csv` | SCC-stratified regime analysis (synthetic) |
| `docs/tables/bootstrap_results_combined_summary.csv` | Legacy bootstrap summary (cross-method comparisons) |

---

*See also: `docs/EXPERIMENTS.md` for a quick-reference script index.*
