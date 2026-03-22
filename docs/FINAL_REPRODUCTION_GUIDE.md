# Final reproduction guide

Exact commands to regenerate the **publication vote suite**, **bootstrap ΔnDCG analyses**, and **paper evidence package**. Assumes repository root `/workspace` (adjust paths if needed).

**Environment (required):**

```bash
cd /workspace
source /workspace/.venv/bin/activate
pip install -r requirements.txt && pip install -e ".[dev]"
```

**Python:** 3.11+ (see `pyproject.toml`). The reference VM used 3.12.

---

## 1. Data: download and prepare

Publication suite uses **SciDocs** and **HotpotQA** processed JSONL under `data/processed/`.

```bash
python scripts/download_datasets.py --dataset scidocs
python scripts/download_datasets.py --dataset hotpotqa

python scripts/prepare_datasets.py --dataset scidocs
python scripts/prepare_datasets.py --dataset hotpotqa
```

- **FiQA / BRIGHT** (not in the default publication suite): same pattern with `--dataset fiqa` or `--dataset bright` after download. See `docs/DATASET_ACCESS_AUDIT.md` for Hub access notes.

---

## 2. Regenerate the publication vote suite

Writes under **`outputs/pub_vote_cmp_v2/`** (per-dataset subdirs with scores, votes, and experiment outputs):

```bash
python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2
```

Defaults (from `scripts/run_publication_vote_suite.py`):

- SciDocs: **120** queries, top-**50** candidates for scoring, top-**k** **20** for votes/experiment.
- HotpotQA: **70** query IDs requested from processed file → **52** processed after **eligibility** filter in `run_real_experiment.py`.
- Seed **42**; rankers **bm25**, **tfidf**, **minilm**; vote variants **ms2**, **ms1**, **ms1_drop_mutual**.

**Per-run layout (example SciDocs ms1):**

- `outputs/pub_vote_cmp_v2/scidocs/ms1/scidocs/votes_file/scidocs_per_query.csv`
- `outputs/pub_vote_cmp_v2/scidocs/ms1/scidocs/votes_file/scidocs_experiment_summary.json`

**Optional markdown summary (stdout):**

```bash
python scripts/summarize_publication_vote_suite.py --root outputs/pub_vote_cmp_v2
```

---

## 3. Bootstrap ΔnDCG analyses

`scripts/build_paper_evidence_package.py` expects JSON files under:

**`outputs/pub_vote_cmp_v2/analysis/`**

Naming: `{dataset}_{variant}_delta_{kind}.json` with `kind` ∈ `copeland`, `balance`.

Generate them with `scripts/analyze_publication_vote_deltas.py` (mean **repaired − unrepaired** per query, bootstrap CIs). Example loop:

```bash
ROOT="outputs/pub_vote_cmp_v2"
mkdir -p "${ROOT}/analysis"

for ds in scidocs hotpotqa; do
  for var in ms2 ms1 ms1_drop_mutual; do
    CSV="${ROOT}/${ds}/${var}/${ds}/votes_file/${ds}_per_query.csv"
    if [[ ! -f "${CSV}" ]]; then
      echo "skip missing ${CSV}"; continue
    fi
    python scripts/analyze_publication_vote_deltas.py \
      --per-query-csv "${CSV}" \
      --method-a hybrid_rrf_unrepaired_copeland_a03 \
      --method-b hybrid_rrf_repaired_copeland_a03 \
      --json-out "${ROOT}/analysis/${ds}_${var}_delta_copeland.json"
    python scripts/analyze_publication_vote_deltas.py \
      --per-query-csv "${CSV}" \
      --method-a hybrid_rrf_unrepaired_balance_a03 \
      --method-b hybrid_rrf_repaired_balance_a03 \
      --json-out "${ROOT}/analysis/${ds}_${var}_delta_balance.json"
  done
done
```

Defaults: `--bootstrap 2000`, `--seed 42`, `--alpha 0.05`. Optional stratified stats are **inside** each JSON under `strata`.

---

## 4. Paper evidence package (tables + figures + summary)

```bash
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
```

**Outputs (tracked in git for this repo):**

| Artifact | Path |
|----------|------|
| Combined graph / nDCG / consistency | `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv` |
| Bootstrap ΔnDCG table | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` |
| BEW/PIC / FAS slim table | `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv` |
| Figures | `outputs/pub_vote_cmp_v2/paper_package/plots/*.png` |
| Narrative summary | `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md` |
| Short README | `outputs/pub_vote_cmp_v2/paper_package/README.md` |

---

## 5. Auxiliary scripts (diagnosis and votes)

```bash
# Directed-cycle summary for any votes / pairwise JSONL
python scripts/diagnose_vote_graph_cycles.py --pairwise-file path/to/votes.jsonl

# Build ms1 then mutual-pair drop (also invoked inside run_publication_vote_suite)
python scripts/postprocess_votes_drop_mutual_pairs.py --input votes_ms1.jsonl --output votes_ms1_drop_mutual.jsonl
```

---

## 6. Other bootstrap tooling (not the paper table path)

For older / alternate paired bootstrap reports over arbitrary `*_per_query.csv`:

- `scripts/bootstrap_method_deltas.py`
- `scripts/run_bootstrap.py` → default `docs/tables/bootstrap_results.csv`

These are **not** what populates `table_bootstrap_delta_ndcg.csv`; that table is driven by **`analyze_publication_vote_deltas.py`** JSON outputs.

---

## 7. Eligibility behavior

Queries are filtered to **eligible** ids via `eligible_query_ids()` in `src/consistency_ranker/data/query_ids.py` (usable qrels: multi-grade with enough diversity, or positive-only BEIR-style pools). When using `--query-id-file`, `run_real_experiment.py` keeps only ids in that set **and** eligible, then takes the first **`--max-queries`**. That is why HotpotQA can end up with **52** rows though **70** ids were written in the suite.

---

## 8. Verification

```bash
ruff check .
pytest
```

See `docs/FINAL_PROJECT_STATE.md` for scientific interpretation and caveats.
