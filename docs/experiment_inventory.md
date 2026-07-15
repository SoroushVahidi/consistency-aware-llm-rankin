# Experiment Inventory

> Machine-readable summary of every experiment family in the repository.  
> Status definitions: **executed** = output files committed; **implemented** = code exists, no committed output; **partial** = some output committed, not the full run; **planned** = mentioned in docs/TODO but not yet coded.

---

## Synthetic Experiments

### SYN-1: Noise Sweep

| Field | Value |
|---|---|
| Name | Noise sweep (n=20, margin weights) |
| Script | `scripts/run_synthetic.py` |
| Datasets | Synthetic (no external data) |
| Key args | `--n-items 20 --weight-scheme margin --seed 42 --noise {0.05,0.10,0.15,0.20,0.25,0.30}` |
| Output paths | `outputs/noise_sweep_n{0.05..0.30}/synthetic_results.json` |
| Status | **executed** |
| Results present | Yes — 6 runs, individual JSON files |
| Aggregated table | `docs/tables/main_results.csv` (rows `noise_sweep`) |
| Paper-evidence ready | Partial — single seed only, not multi-seed |

### SYN-2: Scale Sweep

| Field | Value |
|---|---|
| Name | Scale sweep (noise=0.10, margin weights) |
| Script | `scripts/run_synthetic.py` |
| Datasets | Synthetic |
| Key args | `--noise 0.1 --weight-scheme margin --seed 42 --n-items {10,20,50,100} --save-timings` |
| Output paths | `outputs/scale_sweep_n{10,20,50,100}/` |
| Status | **executed** |
| Results present | Yes — 4 scale points, includes timings |
| Aggregated table | `docs/tables/main_results.csv` (rows `scale_sweep`), `docs/tables/runtime_results.csv` |
| Paper-evidence ready | Yes — supports runtime scaling claim |

### SYN-3: Margin Multi-Seed Replication

| Field | Value |
|---|---|
| Name | Multi-seed replication (n=20, noise=0.20, margin) |
| Script | `scripts/run_synthetic.py` |
| Datasets | Synthetic |
| Key args | `--n-items 20 --noise 0.20 --weight-scheme margin --seed {42,123,456,789,1234}` |
| Output paths | `outputs/margin_multiseed_n20_noise0.20/seed_{42,123,456,789,1234}/` |
| Status | **executed** |
| Results present | Yes — 5 seeds |
| Aggregated table | `docs/tables/main_results.csv` (rows `margin_multiseed`) |
| Paper-evidence ready | Yes — supports cross-seed stability claims |

### SYN-4: Uniform Multi-Seed Replication

| Field | Value |
|---|---|
| Name | Multi-seed replication (n=20, noise=0.20, uniform weights) |
| Script | `scripts/run_synthetic.py` |
| Datasets | Synthetic |
| Key args | `--n-items 20 --noise 0.20 --weight-scheme uniform --seed {42,123,456,789,1234}` |
| Output paths | `outputs/uniform_multiseed_n20_noise0.20/seed_{42,123,456,789,1234}/` |
| Status | **executed** |
| Results present | Yes — 5 seeds |
| Aggregated table | `docs/tables/main_results.csv` (rows `uniform_multiseed`) |
| Paper-evidence ready | Yes |

### SYN-5: Variant Method Follow-up

| Field | Value |
|---|---|
| Name | Noise sweep with additional ranking method variants |
| Script | `scripts/run_variant_followup.py` |
| Datasets | Synthetic |
| Key args | Various (see script header) |
| Output paths | `outputs/noise_sweep_variant_followup/`, `outputs/variant_multiseed_n20_noise0.20/` |
| Status | **executed** |
| Results present | Yes |
| Paper-evidence ready | Partial |

### SYN-6: Exact vs Greedy FAS Comparison

| Field | Value |
|---|---|
| Name | Compare exact MWFAS (ILP) vs greedy heuristic |
| Script | `scripts/run_exact_vs_greedy.py` |
| Datasets | Synthetic |
| Key args | See script |
| Output paths | `docs/tables/exact_vs_greedy_fas.csv`, `docs/tables/exact_vs_greedy_summary.csv` |
| Status | **executed** (synthetic only; ILP solver stubbed) |
| Results present | Yes |
| Paper-evidence ready | No — ILP stub means "exact" results are not truly exact |

### SYN-7: FAS Balance α Sweep

| Field | Value |
|---|---|
| Name | Sweep hybrid balance parameter α |
| Script | `scripts/run_fas_balance_alpha_sweep.py` |
| Datasets | Synthetic |
| Key args | See script |
| Output paths | `docs/tables/fas_balance_alpha_sweep.csv`, `docs/tables/fas_balance_alpha_summary.csv` |
| Status | **executed** |
| Results present | Yes |
| Paper-evidence ready | Partial — synthetic only, no real-data validation |

### SYN-8: FAS Balance α/β Grid

| Field | Value |
|---|---|
| Name | 2D grid search over α and β parameters |
| Script | `scripts/run_fas_balance_alpha_beta_grid.py`, `scripts/run_fas_balance_alpha_beta_generalization.py` |
| Datasets | Synthetic |
| Key args | See scripts |
| Output paths | `docs/tables/fas_balance_alpha_beta_grid.csv`, `docs/tables/fas_balance_alpha_beta_generalization.csv` |
| Status | **executed** |
| Results present | Yes |
| Paper-evidence ready | Partial — synthetic only |

### SYN-9: Regime Analysis

| Field | Value |
|---|---|
| Name | Regime analysis (noise level vs method performance gap) |
| Script | `scripts/run_regime_analysis.py` |
| Datasets | Synthetic |
| Key args | See script |
| Output paths | `docs/tables/regime_analysis.csv`, `docs/figures/regime_analysis_*.png` |
| Status | **executed** |
| Results present | Yes |
| Paper-evidence ready | Partial — synthetic only |

### SYN-10: Diagnostic Experiments

| Field | Value |
|---|---|
| Name | Method diagnostics (greedy FAS underperformance investigation) |
| Script | `scripts/run_diagnostic_experiments.py`, `scripts/diagnose_greedy_fas_underperformance.py` |
| Datasets | Synthetic |
| Key args | See scripts |
| Output paths | `docs/tables/diagnostic_*.csv` |
| Status | **executed** |
| Results present | Yes |
| Paper-evidence ready | Supplementary / appendix material |

---

## Real-Data Experiments

### REAL-1: Publication Vote Comparison v2 (Canonical Evidence)

| Field | Value |
|---|---|
| Name | Publication vote suite — vote construction comparison |
| Script | `scripts/run_publication_vote_suite.py` |
| Datasets | SciDocs (BEIR), HotpotQA |
| Key args | ms2 / ms1 / ms1_drop_mutual vote constructions; 3 rankers (BM25, TF-IDF, MiniLM) |
| Output paths | `outputs/pub_vote_cmp_v2/` |
| Post-processing | `scripts/build_paper_evidence_package.py`, `scripts/analyze_publication_vote_deltas.py` |
| Final tables | `outputs/pub_vote_cmp_v2/paper_package/tables/` (3 tables) |
| Status | **executed** |
| Results present | Yes — canonical paper evidence |
| Paper-evidence ready | **Yes** — primary evidence package |

### REAL-2: Real-Data Bootstrap Significance

| Field | Value |
|---|---|
| Name | Bootstrap ΔnDCG confidence intervals |
| Script | `scripts/bootstrap_method_deltas.py`, `scripts/run_bootstrap.py` |
| Datasets | SciDocs, HotpotQA (from REAL-1 per-query outputs) |
| Key args | 2000 bootstrap replications |
| Output paths | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` |
| Status | **executed** (integrated into REAL-1 pipeline) |
| Results present | Yes |
| Paper-evidence ready | **Yes** |

### REAL-3: FiQA Experiment

| Field | Value |
|---|---|
| Name | FiQA (BEIR) full pipeline |
| Script | `scripts/run_publication_vote_suite.py` with `--dataset fiqa` |
| Datasets | FiQA (BEIR) |
| Key args | Same vote constructions as REAL-1 |
| Output paths | None committed |
| Status | **implemented** (loader exists, not run) |
| Results present | No |
| Paper-evidence ready | No — requires HuggingFace download |

### REAL-4: BRIGHT Experiment

| Field | Value |
|---|---|
| Name | BRIGHT benchmark full pipeline |
| Script | `scripts/run_publication_vote_suite.py` with `--dataset bright` |
| Datasets | BRIGHT |
| Key args | Same vote constructions as REAL-1 |
| Output paths | None committed |
| Status | **implemented** (loader exists with manual-download fallback, not run) |
| Results present | No |
| Paper-evidence ready | No — requires dataset download |

### REAL-5: Real Experiment Validation Run

| Field | Value |
|---|---|
| Name | Small validation / smoke test for real experiment scripts |
| Script | `scripts/run_real_experiment.py` |
| Datasets | Any supported dataset (requires download) |
| Key args | `--dataset scidocs --max-queries 20` (smoke test) |
| Output paths | `outputs/real_small_validation/`, `outputs/real_full/` |
| Status | **partial** (output directories present but mostly empty) |
| Results present | Directories exist; no substantive CSV outputs committed |
| Paper-evidence ready | No |

---

## Planned / Not Yet Coded

### PLAN-1: LLM Pairwise Comparator

| Field | Value |
|---|---|
| Name | Use real LLM (GPT-4o, Llama-3) for pairwise preferences |
| Status | **planned** — mentioned in `TODO.md`, not coded |
| Blocking factor | API access, cost |

### PLAN-2: ILP Exact MWFAS Solver

| Field | Value |
|---|---|
| Name | Implement ILP-based exact MWFAS |
| Status | **done** — `src/consistency_ranker/mwfas_solver.py`, `method="scip"`/`"exact"`/`"ilp"`, backed by the free, open-source SCIP solver via PySCIPOpt. Optional legacy `method="gurobi"` backend also available. See `tests/test_exact_mwfas_scip.py` and `reports/exact_open_source_ilp_repair_investigation/`. |
| Blocking factor | Resolved — solver dependency is PySCIPOpt (`pip install "consistency-ranker[exact]"`), no license required |

### PLAN-3: Additional Rankers

| Field | Value |
|---|---|
| Name | Cross-encoder (e.g. MonoBERT) as a fourth ranker |
| Status | **planned** — `scripts/generate_score_file.py` designed to be extensible |

### PLAN-4: Hierarchical Statistical Model

| Field | Value |
|---|---|
| Name | Mixed-effects model over queries for significance testing |
| Status | **planned** — mentioned in `docs/Q1_JOURNAL_GAP_ANALYSIS.md` |

---

## Additional real benchmarks (registry support)

| Dataset id | Acquisition | Notes |
|---|---|---|
| `nfcorpus` | Hugging Face `BeIR/nfcorpus` | Same BEIR path as SciDocs/FiQA |
| `msmarco_passage` | Hugging Face `BeIR/msmarco` (streaming) | Use `--max-docs`; full corpus is multi-million passages |
| `trec_dl_passage` | Optional `ir-datasets` → `msmarco-passage/trec-dl-{2019,2020}` | Judged evaluation layer; passage text via MS MARCO doc store |
| `robust04` | Optional `ir-datasets` | TREC Robust 2004; licensing via ir-datasets / TREC |

Status: **implemented** (download/prepare scripts + registry); manuscript runs are **not** pre-committed for these ids.
