# Results for Paper (Evidence-Only)

> **SUPERSEDED (as of 2026-07-28).** Written 2026-04-04, before
> `papers/JDIQ_2026/`. Its "Canonical real-data package" points at
> `outputs/pub_vote_cmp_v2/` and `outputs/q1_journal_package/`, both
> explicitly marked `do_not_use`/stale/"conflicts with all4" in
> `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv` — the same nominal
> claims (e.g. SciDocs ms1 Copeland ΔnDCG) are numerically different, and
> in at least one case sign-different, between the two packages. The
> current canonical vote-suite evidence is `outputs/pub_vote_cmp_all4/`,
> reported in `papers/JDIQ_2026/manuscript/main.tex`. Do not cite this
> file's package paths as canonical.

This file summarizes what should be cited from committed outputs without
overstating support.

---

## 1) Best evidence tables currently available

### Canonical real-data package
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv`

### Aggregated Q1 package
- `outputs/q1_journal_package/table_main_performance.csv`
- `outputs/q1_journal_package/table_structural_consistency.csv`
- `outputs/q1_journal_package/table_significance.csv`
- `outputs/q1_journal_package/table_regime_analysis.csv`
- `outputs/q1_journal_package/table_failure_cases.csv`

### Additional manuscript-ready CSV bundle (this hardening pass)
- `reports/paper_tables/table_01_repair_effects.csv`
- `reports/paper_tables/table_02_proxy_baseline_leaderboard.csv`
- `reports/paper_tables/table_03_synthetic_multiseed_stability.csv`
- `reports/paper_tables/table_04_synthetic_noise_sweep.csv`
- `reports/paper_tables/table_05_failure_context.csv`

---

## 2) Concise interpretation per dataset

### SciDocs (canonical package)
- `ms1` is high-cyclicity and produces the strongest negative repaired-vs-
  unrepaired Copeland effect with CI below zero.
- `ms2` and `ms1_drop_mutual` are near-acyclic and mostly inactive for repair.
- Structural consistency (BEW/PIC) improves post-repair under `ms1`.

Primary files:
- `outputs/q1_journal_package/table_main_performance.csv`
- `outputs/q1_journal_package/table_significance.csv`
- `outputs/q1_journal_package/table_structural_consistency.csv`

### HotpotQA (canonical package)
- Same directional pattern as SciDocs but weaker effect size and lower
  statistical confidence for negative Copeland delta under `ms1`.
- Near-acyclic variants again show inactive repair effects.

Primary files:
- `outputs/q1_journal_package/table_main_performance.csv`
- `outputs/q1_journal_package/table_significance.csv`

### FiQA / BRIGHT
- Present in broader proxy outputs (`outputs/real_full/**`) but not in canonical
  paper package tables; should be treated as supplementary until canonicalized.

### Metric-aware FAS (`--repair-weighting` in `run_real_experiment.py`)
- **Not** in pre-committed publication tables. Use per-query CSV columns `repair_weighting`, `fas_repair_variant`, `fas_weight_removed_ma`, and method suffixes `*_ma` when running with `--repair-weighting both` to compare plain vs metric-aware repaired hybrids (e.g. `hybrid_rrf_copeland_a03` vs `hybrid_rrf_copeland_a03_ma`, or ablation names like `hybrid_rrf_repaired_copeland_a03` vs `…_ma` when `--include-hybrid-ablation` is on).

### Optional IR benchmarks (`nfcorpus`, `msmarco_passage`, `trec_dl_passage`, `robust04`)
- Registered for download/prepare and `run_real_experiment.py`; **no pre-committed
  vote-suite or paper_package tables** in this repository.
- Treat any numbers you generate locally as **manuscript supplements** until you
  pin a new `outputs/.../paper_package/` tree and cite that path explicitly.

---

## 3) Cross-dataset pattern summary

1. Vote construction determines whether repair does anything measurable.
2. Structural inconsistency reduction is easier to obtain than retrieval gains.
3. High-cyclicity regimes are where negative retrieval deltas emerge.
4. Near-acyclic regimes produce inactive (often identical) repaired/unrepaired
   rankings.

---

## 4) Failure-analysis summary

Current explicit failure case:
- `outputs/q1_journal_package/table_failure_cases.csv` identifies SciDocs `ms1`
  Copeland as a meaningful harmful case.

Contextualized version:
- `reports/paper_tables/table_05_failure_context.csv` adds cyclicity and
  structural-shift context (FAS removed weight, ΔBEW, ΔPIC).

---

## 5) What should appear in the paper

1. Main table with nDCG and cyclicity by vote construction.
2. Bootstrap ΔnDCG table for repaired-vs-unrepaired method pairs.
3. Structural consistency pre/post table (with explicit caveat on definition).
4. Regime-stratified analysis (high vs low SCC).
5. One explicit failure table/paragraph.

---

## 6) What should NOT appear in the paper as headline evidence

1. Claims of universal retrieval gains from repair.
2. Claims of direct LLM-judgment generalization without dedicated experiments.
3. Claims of exact MWFAS superiority.
4. Broad external-validity claims from only two canonical datasets.

