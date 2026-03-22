# Q1 Publication Gap Analysis (Hardening Pass)

This document is an evidence-grounded gap analysis for Q1-journal readiness.
It uses only committed repository artifacts and explicitly marks unsupported
or weakly supported areas.

---

## 1) Current contribution in precise scientific language

The repository studies retrieval ranking from weighted pairwise-preference
graphs and analyzes the effect of greedy feedback-arc-set (FAS) repair on:

1. Graph structural consistency (graph-vs-reference BEW/PIC metrics).
2. Retrieval effectiveness (nDCG@k and related metrics).
3. Sensitivity to vote-construction regimes (`ms2`, `ms1`, `ms1_drop_mutual`).

Core methods are implemented in:
- `scripts/run_real_experiment.py`
- `src/consistency_ranker/greedy_fas.py`
- `src/consistency_ranker/baseline_ranking.py`
- `scripts/run_publication_vote_suite.py`
- `scripts/build_paper_evidence_package.py`

---

## 2) Current evidence package

### Canonical paper package (committed)
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv`
- `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md`

### Aggregated Q1 package (committed)
- `outputs/q1_journal_package/table_main_performance.csv`
- `outputs/q1_journal_package/table_structural_consistency.csv`
- `outputs/q1_journal_package/table_significance.csv`
- `outputs/q1_journal_package/table_regime_analysis.csv`
- `outputs/q1_journal_package/table_failure_cases.csv`
- `outputs/q1_journal_package/table_per_dataset_summary.csv`
- `outputs/q1_journal_package/summary_report.md`

### Additional committed analyses
- Synthetic and diagnostic tables in `docs/tables/*.csv`
- Proxy multi-dataset outputs in `outputs/real_full/**`

---

## 3) What is already strong enough for a journal

1. **Clear conditional finding (not a universal win):**
   repaired-vs-unrepaired Copeland can be harmful under high-cyclicity vote
   construction (`ms1`), especially on SciDocs.
   Evidence: `outputs/q1_journal_package/table_significance.csv`.

2. **Structured regime analysis:**
   SCC-stratified harm localization is available (high vs low SCC).
   Evidence: `outputs/q1_journal_package/table_regime_analysis.csv`.

3. **Structural-vs-retrieval decoupling:**
   BEW/PIC can improve while nDCG does not.
   Evidence: `outputs/q1_journal_package/table_structural_consistency.csv`
   and `table_main_performance.csv`.

4. **Reproducible analysis scripts and committed outputs:**
   key paper tables are reproducible from script entry points.
   Evidence: `scripts/generate_q1_tables.py`,
   `scripts/build_paper_evidence_package.py`,
   `docs/REPRODUCTION_Q1.md`.

---

## 4) What is not yet strong enough for a Q1 journal

1. **Empirical breadth is narrow in canonical paper package:**
   SciDocs + HotpotQA only in canonical tables.
2. **LLM-specific framing risk:**
   committed publication evidence is ranker-vote derived (BM25/TF-IDF/MiniLM),
   not direct human/LLM pairwise labels.
3. **No exact MWFAS backend in real pipeline:**
   `src/consistency_ranker/mwfas_solver.py` keeps ILP as not implemented.
4. **Manuscript package had no dedicated `reports/paper_tables/` bundle before
   this pass.**

---

## 5) Missing baselines

### Missing in canonical publication package
- Full non-hybrid baseline panel (e.g., `score_sum`, `borda`, `pagerank`)
  is not directly shown in `outputs/pub_vote_cmp_v2/paper_package/tables/*`.

### Available but not canonicalized
- Baselines are present in `outputs/real_full/<dataset>/<source>/*_summary.csv`
  and can be surfaced into paper-ready tables.

---

## 6) Missing ablations

1. Vote-construction ablation exists and is strong (`ms2/ms1/ms1_drop_mutual`),
   but alpha/beta and hybrid-component sweeps are not integrated into canonical
   paper tables.
2. Scripts exist (`scripts/run_fas_balance_alpha_sweep.py`,
   `scripts/run_fas_balance_alpha_beta_grid.py`) but not promoted into
   canonical package.

---

## 7) Missing statistical analysis

1. Canonical package emphasizes bootstrap CIs for selected pairs.
2. Missing in canonical package:
   - broad paired comparison matrix across more baselines,
   - effect-size table in paper-facing directory,
   - consolidated evidence inventory.

Existing capabilities:
- `scripts/bootstrap_method_deltas.py`
- `scripts/run_bootstrap.py`

---

## 8) Missing robustness checks

1. Canonical package has two datasets and three vote constructions.
2. Additional robustness artifacts exist but were not packaged for manuscript:
   - synthetic multiseed directories:
     `outputs/margin_multiseed_n20_noise0.20/`,
     `outputs/uniform_multiseed_n20_noise0.20/`,
     `outputs/variant_multiseed_n20_noise0.20/`
   - synthetic noise sweeps:
     `outputs/noise_sweep_n*/`,
     `outputs/noise_sweep_variant_followup/noise_*/`
   - proxy multi-dataset real runs:
     `outputs/real_full/`

---

## 9) Missing failure analysis

Current failure table exists:
- `outputs/q1_journal_package/table_failure_cases.csv`

Gap:
- limited contextualization in paper-facing bundle (e.g., cyclicity + BEW/PIC
  context joined directly with failure rows).

---

## 10) Missing reproducibility components

Addressed in this hardening pass:
- Added overwrite-safety and path validation in:
  - `scripts/run_real_experiment.py`
  - `scripts/run_synthetic.py`
- Added reproducible command driver:
  - `Makefile`
- Added paper-table generation script:
  - `scripts/generate_paper_tables.py`

Still missing for full Q1 hardening:
- pinned lockfile (requirements lock / resolver lock).
- broader cross-machine environment specification.

---

## 11) Missing manuscript artifacts

Before this pass: no dedicated machine-readable paper-table bundle directory.

Now added:
- `reports/paper_tables/` (generated by `scripts/generate_paper_tables.py`)
  with repair effects, baseline leaderboard, robustness summaries, and artifact
  inventory.

---

## 12) Top reviewer risks

1. “Two canonical datasets are insufficient for Q1 generalization.”
2. “LLM framing exceeds evidence (ranker-vote proxies dominate).”
3. “Structural metrics improve, but retrieval does not—what is the core claim?”
4. “Exact MWFAS is unimplemented in real pipeline.”
5. “Baseline panel is under-exposed in manuscript package.”
6. “Potential reproducibility clobbering from silent output overwrites” (now mitigated).

---

## 13) Top 10 actions to make the paper Q1-ready

1. Extend canonical paper package to include FiQA and BRIGHT real-data results.
2. Add direct LLM pairwise preference experiments (or narrow scope explicitly).
3. Integrate full baseline panel into canonical paper tables.
4. Add paired significance/effect-size tables for broader method comparisons.
5. Implement exact ILP MWFAS backend (or bound claims to greedy only).
6. Add robustness appendix tables from multiseed/noise sweeps.
7. Add failure-context table linking harm to cyclicity and consistency shifts.
8. Freeze reproducible environment with lockfile.
9. Keep README/manuscript wording strictly aligned with committed evidence.
10. Re-run and version a final end-to-end “camera-ready” artifact build.

