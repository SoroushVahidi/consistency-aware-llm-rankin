# Q1 Journal Gap Analysis

> **Purpose:** Rigorous audit of the repository's current state against Q1
> journal submission standards.  Based entirely on actual repository contents
> as of the current checkout.  Does not recommend changes that are not
> achievable from the existing code and outputs.

---

## 1. Current Project Goal

Study whether **graph-theoretic cycle repair** (Minimum Weighted Feedback Arc
Set, MWFAS) on pairwise-vote preference graphs improves retrieval ranking
quality (nDCG@k) on standard IR benchmarks, and identify the conditions under
which it helps, is neutral, or hurts.

---

## 2. Current Strongest Supported Claims

All claims below are backed by committed artifacts in `outputs/pub_vote_cmp_v2/paper_package/`.

| # | Claim | Evidence |
|---|-------|----------|
| C1 | Vote aggregation strategy (ms2 / ms1 / ms1_drop_mutual) is the dominant factor controlling cycle prevalence and SCC size. | `table_graph_ndcg_and_consistency.csv`: ms2 → 1.7% cyclic on SciDocs; ms1 → 97.5% cyclic. |
| C2 | FAS repair measurably reduces graph–label inconsistency (backward-edge weight BEW and pairwise inconsistency count PIC relative to qrels-derived reference ranking). | Same table: SciDocs ms1 BEW pre/post 309.1→308.0; PIC 99.8→88.1. |
| C3 | Under ms1 (high-cycle regime) on SciDocs, repaired-vs-unrepaired Copeland hybrid yields negative mean ΔnDCG with a bootstrap 95% CI strictly below zero (mean −0.0091, CI [−0.017, −0.003]). | `table_bootstrap_delta_ndcg.csv` row `scidocs / ms1 / copeland`. |
| C4 | The negative ΔnDCG concentrates in queries with largest-SCC ≥ median (mean −0.015 vs −0.001 for below-median). | Same table rows `copeland_scc_high` / `copeland_scc_low`. |
| C5 | Under ms2 and ms1_drop_mutual (low-cycle regimes), repaired vs unrepaired rankings coincide (ΔnDCG = 0, CI [0, 0]) — repair is effectively inactive. | Table rows for ms2 and ms1_drop_mutual across both datasets. |
| C6 | Balance hybrids show no meaningful ΔnDCG under any vote construction (CI always includes 0, effect size negligible). | All `balance` rows in `table_bootstrap_delta_ndcg.csv`. |
| C7 | HotpotQA ms1: Copeland ΔnDCG is slightly negative (mean −0.00087, CI [−0.00218, 0]) — evidence of marginal harm, not clear benefit. | `table_bootstrap_delta_ndcg.csv` row `hotpotqa / ms1 / copeland`. |
| C8 | Synthetic experiments: `borda` dominates `greedy_fas_topological` across all noise levels and seeds; FAS reduces pairwise inconsistency count but does not translate to Kendall τ gains. | `docs/tables/main_results.csv`, `docs/RESULTS_AUDIT.md`. |

---

## 3. Current Weak Points for a Q1 Journal Submission

### 3.1 Dataset Breadth

- The publication-facing package covers only **two real datasets** (SciDocs,
  HotpotQA).  Both are small (≤120 queries after eligibility filtering).
- **FiQA** and **BRIGHT** have loader code, gitkeep placeholders, and even
  some proxy/bootstrap outputs in `docs/tables/`, but are **not in the
  canonical paper package** (`scripts/build_paper_evidence_package.py` only
  loops over `DATASETS = ("scidocs", "hotpotqa")`).
- For a Q1 journal, at least 3–4 IR benchmarks of varying domain and
  difficulty are expected.

### 3.2 Ranker and Vote-Construction Coverage

- Three rankers only (BM25, TF-IDF, MiniLM-L6).  No neural reranker (e.g.
  MonoBERT, cross-encoder) is included.  Reviewers may question whether
  results hold with stronger base rankers.
- Only three vote constructions are evaluated.  The vote-construction ablation
  is not formally presented as a standalone table with effect-size reporting.

### 3.3 Statistical Analysis Gaps

- Bootstrap CIs exist for the repaired-vs-unrepaired pair only.  **No
  significance test** comparing FAS methods against the score-sum / Borda /
  PageRank baselines (is the prior-only hybrid competitive?).
- No multiple-comparisons correction is applied or discussed.
- Query counts are small: SciDocs n≈120, HotpotQA n=52.  Power is limited.
- No effect-size measure (e.g. Cohen's d) is reported alongside CIs.

### 3.4 Structural Metrics Are Self-Referential

- BEW and PIC are measured against a **qrels-derived reference ranking**, not
  a ground-truth total order.  A reviewer will note this is circularity: qrels
  encode the same signal as nDCG@k, so confirming BEW drops is not an
  independent measure.
- No external graph-theoretic metric (e.g. fraction of edges reversed, SCC
  diameter, or topological ambiguity count) is systematically reported
  alongside nDCG.

### 3.5 Methodology Coverage

- ILP exact MWFAS solver is **stubbed** (`src/consistency_ranker/mwfas_solver.py`).
  Exact-vs-greedy comparison exists for synthetic data only
  (`docs/tables/exact_vs_greedy_fas.csv`) but not on real data.
- No ablation of the hybrid α parameter beyond the fixed default (α=0.3) in
  the publication suite.  The α/β sweep scripts exist
  (`scripts/run_fas_balance_alpha_beta_grid.py`) but are not wired into the
  final paper package.

### 3.6 Synthetic–Real Consistency

- Synthetic experiments use Kendall τ; real experiments use nDCG@k.  There is
  no bridge connecting the two evaluation paradigms (e.g. reporting Kendall τ
  between produced ranking and qrels-derived ranking on real data).
- The regime analysis (`docs/tables/regime_analysis.csv`,
  `docs/tables/regime_deltas.csv`) is computed on **synthetic** data only.

### 3.7 Reproducibility Packaging

- `docs/FINAL_REPRODUCTION_GUIDE.md` exists but assumes a `/workspace` path
  and a `.venv` activation that is not standard across environments.
- No single top-level script runs all analyses from raw outputs to final
  tables.
- No machine-readable environment spec beyond `requirements.txt` (no
  `environment.yml` or locked pinfile).
- The `scripts/check_repo_ready.py` verification script is missing.

---

## 4. Missing Experiments

| Missing Item | Impact | Feasibility Without Network |
|---|---|---|
| FiQA and BRIGHT in canonical paper package | High: only 2 datasets is too narrow for Q1. | Low: requires HuggingFace download. |
| Exact MWFAS on real data | Medium: only greedy heuristic is fully evaluated. | Medium: ILP stub needs pulp/gurobipy. |
| Significance tests vs score-sum/Borda baselines | High: current CI only covers repaired-vs-unrepaired. | High: can be computed from existing per-query CSVs. |
| Regime analysis on real data (SCC size vs ΔnDCG scatter) | High: synthetic regime analysis exists, real one does not. | High: computable from existing per-query CSVs. |
| α/β sweep on real data | Medium: grid scripts exist but not piped into paper package. | High: computable from existing per-query CSVs. |
| Ranker-family comparison (stronger reranker) | Medium: adds generalization. | Low: requires models. |

---

## 5. Missing Statistical Analyses

- Paired t-test / Wilcoxon signed-rank test for each method pair (complement to
  bootstrap CIs, tests for median rather than mean difference).
- Multiple comparisons correction (Bonferroni or Benjamini–Hochberg) across the
  method-pair × dataset × vote-construction matrix.
- Correlation analysis: Pearson / Spearman between graph cyclicity measures
  (pct_cyclic, avg_largest_SCC, fas_weight_removed) and per-query ΔnDCG.
- Effect-size summary table (Cohen's d or rank-biserial correlation) alongside
  bootstrap CIs.

---

## 6. Missing Baselines or Datasets

**Datasets absent from the canonical paper package:**
- FiQA (financial QA, BEIR suite) — loader exists, gitkeep present.
- BRIGHT (reasoning-intensive retrieval) — loader exists, gitkeep present.
- SciDocs with BM25-only baseline (no multi-ranker votes) — would isolate the
  contribution of vote aggregation.

**Baselines absent from the paper package:**
- ListNet / LambdaMART (learning-to-rank) — no code present.
- RRF without FAS (pure reciprocal-rank fusion of raw ranker scores) — this is
  the `hybrid_rrf_prior_only` method and IS present; it should be featured more
  prominently as the main competitor.
- Copeland ranking on raw (un-repaired) graph as a standalone baseline — this
  exists as `hybrid_rrf_unrepaired_copeland_a03` but is not labeled prominently
  as a baseline in the manuscript summary.

---

## 7. Packaging and Reproducibility Weaknesses

| Weakness | File(s) | Severity |
|---|---|---|
| Hard-coded `/workspace` paths in docs | `docs/FINAL_REPRODUCTION_GUIDE.md` | Medium |
| No `scripts/check_repo_ready.py` | — | Medium |
| No canonical single-command paper regeneration | — | High |
| `pyproject.toml` `[project.scripts]` only exposes `run-synthetic`; real experiment pipeline has no entry point | `pyproject.toml` | Low |
| `README.md` quickstart only covers synthetic; no end-to-end real-data command | `README.md` | Medium |
| No locked dependency file (pip-tools / poetry lock) | — | Low |
| Large plot files and per-query CSVs not explicitly .gitignored | `.gitignore` absent | Low |

---

## 8. Manuscript Positioning Recommendation

The evidence supports a **conditional diagnostic paper**, not a positive methods
paper.  The headline result is that FAS repair is not a free win: it reduces
structural inconsistency but can harm retrieval quality under vote constructions
that produce high cyclicity (ms1 / Copeland).  The paper's value is in
characterizing the conditions (vote construction, graph regime, extraction
strategy) rather than claiming a universal improvement.

**Recommended title direction:**
> "When Does Cycle Repair Help? Vote Construction, Graph Regime, and the
> Retrieval Impact of Feedback-Arc-Set Repair on LLM Preference Graphs"

**Recommended contribution list:**
1. A controlled characterization of how vote aggregation (ms1 / ms2 /
   drop-mutual) controls cycle prevalence in multi-ranker preference graphs.
2. A diagnostic study of FAS repair impact on nDCG@k: neutral under near-
   acyclic graphs, potentially harmful under high-cyclicity Copeland hybrids.
3. A structural consistency metric (BEW, PIC vs qrels reference) that decouples
   graph-level improvement from retrieval-level impact.
4. A reproducible benchmark with bootstrap significance testing on two IR
   benchmarks and synthetic controlled sweeps.

---

*Generated from repository audit of actual contents.  Last updated: see git log.*
