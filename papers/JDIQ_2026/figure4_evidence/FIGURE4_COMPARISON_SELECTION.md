# Figure 4 Comparison Selection

**Prepared:** 2026-07-12
**Scope:** Evidence collection only. No new experiments, no API calls, no regenerated retrieval outputs.

---

## The selected comparison

**Repaired hybrid vs. unrepaired hybrid ranking, on nDCG@15, across all four canonical benchmarks and all three vote-extraction regimes** — i.e. the retrieval-quality effect of the FAS acyclicity-repair intervention.

Concretely, this is two method-pairs evaluated together:

1. **Copeland hybrid:** `hybrid_rrf_repaired_copeland_a03` − `hybrid_rrf_unrepaired_copeland_a03`
2. **Balance hybrid:** `hybrid_rrf_repaired_balance_a03` − `hybrid_rrf_unrepaired_balance_a03`

Both are RRF fusions (α = 0.3) of the prior ranking with a graph-derived hybrid, differing only in whether the preference graph was FAS-repaired before scoring. This yields **24 rows** (4 datasets × 3 regimes × 2 pairs), each with a bootstrap mean ΔnDCG@15 and a 95% CI (2,000 resamples).

Source: `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` (the single canonical bootstrap table for the four-dataset vote suite).

---

## Why this is the right comparison for Figure 4

### 1. It is literally what the manuscript plan already calls "Figure 4"

Four independent planning documents already committed in `papers/JDIQ_2026/` converge on this exact comparison as Figure 4:

| Document | What it says |
|---|---|
| `FIGURE_PLAN.md` | "Fig. 4 — Bootstrap ΔnDCG forest plot ... Critical — central decoupling evidence" |
| `PROJECT_STATUS.md` | "Fig 4 bootstrap forest — Script exists; needs regeneration" |
| `MISSING_COMPONENTS.md` | "M5 Regenerate Figs 2–5 from `build_manuscript_assets.py`" (Fig 4 = bootstrap forest, per Figure Plan) |
| `SECTION_EVIDENCE_MAP.csv` (row `F003`) | `fig_delta_ndcg_bootstrap.png`, section §6, role **"Fig 4"**, canonical=main, notes="Bootstrap forest" |

**One inconsistency found and resolved:** `FIGURE_SPECIFICATIONS.md` (a later, more detailed document) numbers this same forest plot as **F05** and instead assigns **F04** to a different visualization (FAS weight removed vs. retrieval delta scatter plot). This is a drift between two planning documents, not a disagreement about content. Given (a) three older planning docs and the machine-readable `SECTION_EVIDENCE_MAP.csv` all agree the bootstrap forest plot is "Figure 4", and (b) the user's task description for this Figure 4 — "ΔnDCG + 95% bootstrap confidence interval for repair versus no repair" — matches the forest plot exactly and does not match the scatter plot, this package treats **the bootstrap ΔnDCG forest plot as Figure 4** and flags the numbering drift in `FINAL_REPORT.md` for manuscript authors to reconcile before submission.

### 2. It is the paper's central empirical claim

Per `CANONICAL_PAPER_STORY.md`, the manuscript's core hypothesis is that **structural graph repair is decoupled from downstream retrieval quality**. The bootstrap ΔnDCG-with-CI comparison is the direct quantitative test of that hypothesis: it is the only evidence in the repository that simultaneously (a) isolates the repair intervention itself (same fusion method, same queries, only the graph is repaired or not) and (b) reports inferential uncertainty (CI), rather than a point estimate alone.

### 3. It is a clean "repair vs no repair" pair, not a proxy

Other candidate comparisons in the repository were considered and rejected:

- **Pooled ranking-method comparison** (`final_baseline_comparison.csv`: CombSUM vs RRF vs proposed hybrid, etc.) answers "does repair+fusion beat other fusion baselines?" — a different, secondary question (destined for Figure 6/Table 6). It mixes repair with method choice and is not a same-method repaired-vs-unrepaired contrast.
- **Structural metrics pre/post repair** (BEW/PIC, `table_consistency_qrels_bew.csv`) measures whether repair improves *graph* consistency, not *retrieval* quality — this is Figure 3's job, and it is a necessary precursor to Figure 4, not a substitute for it.
- **Real-LLM pilot bootstrap deltas** (`outputs/openai_*/`) test the same repaired-vs-unrepaired Copeland/balance pair, but under a different judge (real LLM pairwise/pointwise/listwise calls) on N=10–50 queries per dataset. This is legitimate supplementary evidence for §8 (Real-LLM Validation, Table 9) but is explicitly a "bounded pilot" per `CANONICAL_PAPER_STORY.md` (S4) — not canonical for the main-suite Figure 4, and the task instructions forbid calling APIs or treating these pilots as the headline result.

### 4. It supports the required scientific message without overstating it

The 24-row comparison shows:
- **20 of 24 rows are exactly zero** (mean Δ = 0, CI = [0,0]): repair is retrieval-inactive whenever the underlying graph is near-acyclic (all `ms2` and `ms1_drop_mutual` rows, both pairs).
- **All 12 `balance`-pair rows are exactly zero**, including under `ms1` (the cyclic regime): the balance hybrid's ranking is insensitive to this repair.
- Among the 4 active `ms1`/Copeland rows, only **HotpotQA ms1** has a 95% CI that excludes zero (mean Δ = +0.0167, CI [0, 0.0405]) — the single positive, statistically distinguishable retrieval effect of repair anywhere in the canonical suite. FiQA ms1 Copeland is directionally positive but its CI straddles zero; SciDocs ms1 Copeland is directionally negative with CI straddling zero; BRIGHT ms1 Copeland is essentially zero with CI straddling zero.

This is exactly the "heterogeneous, usually null, one clear exception" pattern that `CANONICAL_PAPER_STORY.md` requires Figure 4 to demonstrate, and nothing in the selected data requires or invites a claim beyond what the manuscript's claim-support matrix already licenses.

---

## What was explicitly excluded, and why

Per the task's exclusion rules and cross-checked against `MASTER_EVIDENCE_INVENTORY.csv`:

- `outputs/pub_vote_cmp_v2/` — superseded two-dataset suite, flagged `do_not_use`/`stale` in the master inventory; conflicts with the all4 suite on SciDocs ms1 framing.
- `outputs/q1_journal_package/` — built from v2 by default, flagged `do_not_use`.
- `outputs/manuscript_artifacts/` — pre-all4 stale tables, flagged `do_not_use`/`stale`.
- The rejected IJCS manuscript zip — historical only.
- `outputs/bootstrap_modern/`, `outputs/real_full/` — different comparisons/protocols (flip-probability robustness checks; qrels-derived preference construction), not the ms2/ms1/ms1_drop_mutual repair contrast.
- `docs/tables/bootstrap_results*.csv` — legacy, one file is a recorded blocked run with no data, flagged `verify_before_use`/low confidence in the master inventory.

Full row-by-row disposition is in `BOOTSTRAP_SOURCE_INVENTORY.csv`.
