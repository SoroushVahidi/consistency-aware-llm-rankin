# Repository Audit and Gap Analysis

> **Created by:** Publication-readiness and evidence-hardening pass  
> **Date:** 2026-03-22  
> **Grounded in:** Actual committed files and outputs only — no projections or invented claims.

---

## 1. Project Purpose

This repository studies whether **graph-theoretic cycle repair** — specifically
the Minimum Weighted Feedback Arc Set (MWFAS) heuristic — improves retrieval
ranking quality when applied to pairwise-vote preference graphs built from
multiple IR rankers (BM25, TF-IDF, MiniLM-L6).  On each query a weighted
directed graph is constructed from multi-ranker votes; edges are then removed
to produce a DAG (directed acyclic graph), and rankings are extracted and
optionally hybridised with a score prior.

The core question is: **does repairing cyclic inconsistencies in a preference
graph improve nDCG@k?**  The answer, as established by the committed evidence,
is *conditionally no*: under majority-style vote aggregation repair is inactive
(near-acyclic graphs), and under per-ranker vote aggregation repair is
measurably harmful for Copeland-based hybrids on SciDocs (bootstrap 95% CI
strictly negative).  Vote construction — not the repair algorithm itself —
is the dominant factor controlling graph cyclicity.

---

## 2. Methods Implemented

All methods live under `src/consistency_ranker/`.

| Module | What it implements |
|---|---|
| `synthetic_data.py` | Synthetic item generation with latent quality scores |
| `pairwise_prefs.py` | Noisy pairwise preference generation (margin or uniform weights) |
| `graph_construction.py` | Build weighted directed preference graphs from pairwise votes |
| `cycle_detection.py` | Cycle detection, SCC analysis, enumeration |
| `greedy_fas.py` | Greedy MWFAS heuristic: iteratively removes minimum-weight cycle edges |
| `mwfas_solver.py` | MWFAS solver interface — **greedy backend only**; ILP stub not yet functional |
| `baseline_ranking.py` | Score-sum, Borda, Copeland, topological sort, balance hybrids, RRF-FAS hybrid |
| `evaluation.py` | Kendall τ, pairwise inconsistency count, ranking agreement, n_violations |
| `data/schema.py` | Typed dataclasses: Query, Document, QrelEntry, PairwisePreference |
| `data/dataset_registry.py` | DatasetConfig registry (scidocs, fiqa, hotpotqa, bright) |
| `data/beir_loader.py` | BEIR corpus/queries/qrels loader |
| `data/hotpotqa_loader.py` | HotpotQA loader |
| `data/bright_loader.py` | BRIGHT loader (with manual-download fallback) |
| `data/unified_loader.py` | `preferences_from_qrels()` and `load_dataset_splits()` |
| `data_loader.py` | Legacy generic file loader |
| `utils/timing.py` | Timer and TimingAccumulator for per-stage profiling |

---

## 3. Datasets Supported

| Dataset | Loader | Data present in repo | Status |
|---|---|---|---|
| SciDocs (BEIR) | `data/beir_loader.py` | Placeholder `.gitkeep` only | Requires HuggingFace download |
| FiQA (BEIR) | `data/beir_loader.py` | Placeholder `.gitkeep` only | Requires HuggingFace download |
| HotpotQA | `data/hotpotqa_loader.py` | Placeholder `.gitkeep` only | Requires HuggingFace download |
| BRIGHT | `data/bright_loader.py` | Placeholder + `data/raw/bright/README.md` | Requires manual download |
| Synthetic | `synthetic_data.py` | Generated at runtime | No download needed |

**Note:** The canonical evidence package (`outputs/pub_vote_cmp_v2/paper_package/`) covers only **SciDocs** and **HotpotQA**.  FiQA and BRIGHT have loader code but are absent from the final published output tables.

---

## 4. Experiments Already Run (Committed Outputs Present)

### 4.1 Synthetic Experiments

| Experiment Family | Output Path | Seeds / Conditions |
|---|---|---|
| Noise sweep (n=20, margin) | `outputs/noise_sweep_n{0.05..0.30}/` | 1 seed (42), 6 noise levels |
| Scale sweep (n=10–100, margin, noise=0.10) | `outputs/scale_sweep_n{10,20,50,100}/` | 1 seed (42), 4 scale points |
| Margin multi-seed (n=20, noise=0.20) | `outputs/margin_multiseed_n20_noise0.20/seed_{42,123,456,789,1234}/` | 5 seeds |
| Uniform multi-seed (n=20, noise=0.20) | `outputs/uniform_multiseed_n20_noise0.20/seed_{42,123,456,789,1234}/` | 5 seeds |
| Variant follow-up | `outputs/noise_sweep_variant_followup/` | Extended method variants |

Aggregated summaries: `docs/tables/main_results.csv`, `docs/tables/runtime_results.csv`.

### 4.2 Real-Data Experiments (Publication Evidence Package)

| Experiment | Output Path | Datasets | Vote Constructions |
|---|---|---|---|
| Publication vote comparison v2 | `outputs/pub_vote_cmp_v2/paper_package/` | SciDocs, HotpotQA | ms2, ms1, ms1_drop_mutual |

Key output tables:
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv`

### 4.3 Diagnostic / Ablation Experiments (Committed Tables)

| Table | Path | Description |
|---|---|---|
| Exact vs greedy FAS comparison | `docs/tables/exact_vs_greedy_fas.csv` | Synthetic only |
| FAS balance α sweep | `docs/tables/fas_balance_alpha_sweep.csv` | Synthetic only |
| FAS balance α/β grid | `docs/tables/fas_balance_alpha_beta_grid.csv` | Synthetic only |
| Regime analysis | `docs/tables/regime_analysis.csv` | Synthetic only |
| Bootstrap (proxy/real) | `docs/tables/bootstrap_results*.csv` | Intermediate / proxy data |
| Ablation results | `docs/tables/ablation_results.csv` | Synthetic variants |

---

## 5. Existing Output Artifacts and Their Meaning

| Artifact | Meaning |
|---|---|
| `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv` | Per-variant graph stats (% cyclic, avg SCC, avg edges) and mean nDCG for all five ranking methods across SciDocs and HotpotQA |
| `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` | Bootstrap 95% CIs for mean per-query ΔnDCG (repaired − unrepaired), stratified by dataset/variant/method pair and SCC regime |
| `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv` | Pre/post backward-edge weight (BEW) relative to qrels-derived reference ranking |
| `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md` | Human-readable narrative of the manuscript-facing results |
| `docs/tables/main_results.csv` | Full synthetic experiment inventory (noise sweep, scale sweep, multiseed) with Kendall τ and runtime columns |
| `docs/tables/runtime_results.csv` | Per-stage timing breakdown (greedy FAS dominates at large n) |
| `docs/figures/` | Diagnostic/exploratory plots (regime analysis, exact vs greedy, FAS balance sweeps) |
| `outputs/q1_journal_package/` | Auto-generated Q1 summary tables (regenerated by `scripts/generate_q1_tables.py` from above outputs) |

---

## 6. Strongest Supported Conclusions

All conclusions below are grounded in committed artifacts.

1. **Vote construction controls graph cyclicity** (SciDocs ms2: 1.68% cyclic; ms1: 97.5% cyclic) — `table_graph_ndcg_and_consistency.csv`.

2. **FAS repair reduces label-aligned structural inconsistency** (BEW and PIC decrease after repair under ms1) — same table and `table_consistency_qrels_bew.csv`.

3. **Repair harms nDCG under high-cyclicity construction**: SciDocs ms1 Copeland ΔnDCG = −0.0091 with bootstrap 95% CI [−0.017, −0.003] — `table_bootstrap_delta_ndcg.csv`.

4. **Harm concentrates in high-SCC queries**: SciDocs ms1, SCC ≥ median: ΔnDCG = −0.015 [−0.027, −0.006] vs SCC < median: ΔnDCG ≈ 0 — same table.

5. **Repair is inactive under near-acyclic constructions**: ms2 and ms1_drop_mutual all show ΔnDCG = 0, CI [0, 0] — same table.

6. **Balance hybrids are repair-neutral**: all balance rows have CI including 0, |Δ| < 0.0001 — same table.

7. **Synthetic: Borda dominates greedy FAS topological across all noise/scale points** — `docs/tables/main_results.csv`.

8. **Runtime: greedy FAS dominates pipeline time at n ≥ 50 (>94% share)** — `docs/tables/runtime_results.csv`.

---

## 7. Conclusions NOT Yet Supported

| Unsupported Claim | Why |
|---|---|
| FAS repair reliably improves nDCG@k | Bootstrap evidence shows harm (ms1/SciDocs) or neutrality everywhere |
| Method outperforms Borda/score_sum | Neither confirmed on real data; synthetic evidence shows opposite |
| BEW/PIC improvement implies retrieval improvement | BEW/PIC measured against qrels-derived reference, not independent ground truth |
| Results generalise to LLM-generated preferences | All experiments use BM25/TF-IDF/MiniLM score-derived votes, not real LLM judgements |
| Results generalise beyond SciDocs and HotpotQA | FiQA and BRIGHT have code but no committed results |
| Exact ILP MWFAS outperforms greedy on real data | ILP solver is stubbed; exact-vs-greedy only tested on synthetic data |
| α=0.3 hybrid is an optimised parameter | α sweep exists for synthetic only; no validation-set tuning documented on real data |
| Method is efficient for production use | Only n ≤ 100 tested; no batch or real-time analysis |

---

## 8. Reproducibility Gaps

1. **Network dependency for real data**: `scripts/download_datasets.py` requires HuggingFace Hub access; documented workarounds are minimal.  Real-data experiments cannot be reproduced offline.

2. **No single top-level pipeline script**: Reproducing the full evidence package requires running ~6 separate scripts in a specific order (documented in `docs/REPRODUCTION_Q1.md` but not automated).

3. **Environment path assumption**: `docs/FINAL_REPRODUCTION_GUIDE.md` references `/workspace/.venv` — not standard across environments.

4. **No conda/environment.yml**: Only `requirements.txt` and `pyproject.toml`; no lockfile guaranteeing exact dependency versions.

5. **Test count mismatch in docs**: `docs/REPRODUCTION_Q1.md` states "186 tests pass" but the current test suite has 212 tests.

6. **`outputs/q1_journal_package/` may be stale**: depends on pre-committed tables and `generate_q1_tables.py`; a fresh regeneration should be verified.

7. **No CI/CD workflow**: No `.github/workflows/` file; CI status cannot be verified without manual setup.

---

## 9. Documentation Gaps

1. **README test count** references "212 tests" — should be kept current with each test addition.

2. **`TODO.md`** lists items (ILP solver, MS-MARCO, LLM comparator) that were valid early-stage plans but have not been updated to reflect the current advanced state of the publication pipeline.

3. **`docs/FINAL_REPRODUCTION_GUIDE.md`** and **`docs/REPRODUCTION_Q1.md`** overlap substantially; one should be the canonical guide.

4. **No `CONTRIBUTING.md`** for external contributors.

5. **`docs/AUDIT.md`** is a full system audit that overlaps with this file; the two should be cross-referenced.

6. **`docs/METHOD_REPOSITIONING_AUDIT.md`** and **`REPOSITORY_ANALYSIS.md`** (root level) add additional context but are not referenced from the README index.

---

## 10. Testing Gaps

1. **No CLI argument validation tests** for `run_synthetic.py` (invalid noise, negative n_items, invalid weight_scheme).  **Addressed in this audit pass.**

2. **No regression test for the publication evidence tables**: a test that loads the committed CSVs and checks key numerical values against known-correct figures.  **Addressed in this audit pass.**

3. **No edge-case tests for `pairwise_inconsistency_count`** with empty graphs or graphs where nodes are absent from the reference ranking.  **Addressed in this audit pass.**

4. **No test for `greedy_fas_total_weight`** on non-trivial graphs.

5. **No test verifying that `greedy_fas` produces a true DAG** (currently tested implicitly but not via `nx.is_directed_acyclic_graph`).  **Addressed in this audit pass.**

6. **No test for `ms1_drop_mutual` post-filter** (implemented in `scripts/postprocess_votes_drop_mutual_pairs.py` but not unit-tested).

---

## 11. Paper-Readiness Gaps

1. **Dataset breadth**: Only two real datasets in the canonical evidence package; Q1 venues typically expect 3–4.

2. **Ranker breadth**: Three rankers (BM25, TF-IDF, MiniLM-L6); no cross-encoder baseline.

3. **No multiple-comparisons correction** on the bootstrap CIs.

4. **BEW/PIC circularity**: measured against qrels-derived reference — reviewers will flag this.

5. **Small query counts**: SciDocs n≈120, HotpotQA n=52; statistical power is limited.

6. **No effect-size measure** (e.g. Cohen's d) alongside bootstrap CIs.

7. **Synthetic–real evaluation bridge missing**: Kendall τ is reported only for synthetic; no Kendall τ reported for real-data rankings vs qrels-derived reference.

8. **α/β hyperparameter ablation** exists only for synthetic data; no real-data validation-set tuning.

---

## 12. Prioritised Top-10 Improvements

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 1 | Add FiQA and BRIGHT to the canonical evidence package (`DATASETS` in `build_paper_evidence_package.py`) | Medium | High — directly addresses dataset breadth gap |
| 2 | Create a single reproducibility script / Makefile target that runs the full synthetic + Q1-table pipeline with one command | Low | High — dramatically improves reproducibility |
| 3 | Update `TODO.md` to reflect actual project state and open tasks | Low | Medium — prevents reader confusion |
| 4 | Add CLI argument validation and error messages to key scripts (`run_synthetic.py`, `run_real_experiment.py`) | Low | Medium — improves usability and reduces silent errors |
| 5 | Add regression test that verifies committed CSV key values have not changed | Low | Medium — prevents accidental result corruption |
| 6 | Add test for `greedy_fas` DAG guarantee and `ms1_drop_mutual` filter | Low | Medium — hardens core correctness claims |
| 7 | Consolidate `docs/FINAL_REPRODUCTION_GUIDE.md` and `docs/REPRODUCTION_Q1.md` into a single canonical guide | Low | Medium — reduces reader confusion |
| 8 | Add lockfile (`pip-tools` or `uv` lock) for exact reproducibility | Low | Medium — enables byte-for-byte environment recreation |
| 9 | Implement ILP-based exact MWFAS solver (remove stub) | High | Medium — enables exact-vs-greedy comparison on real data |
| 10 | Report Kendall τ between produced ranking and qrels-derived reference on real data | Medium | Medium — bridges synthetic/real evaluation gap |
