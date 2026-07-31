# Q1 Journal: Scientific Positioning and Claims

> **SUPERSEDED (as of 2026-07-28).** Written for a pre-JDIQ Q1 submission
> target; its "Primary evidence" citations point at
> `outputs/pub_vote_cmp_v2/`, explicitly marked `do_not_use`/stale in
> `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`. The actual submitted
> positioning is in `papers/JDIQ_2026/manuscript/main.tex` and
> `papers/JDIQ_2026/CANONICAL_PAPER_STORY.md`.

> **Purpose:** Defines the safe claim set, recommended narrative, and likely
> reviewer objections based on the evidence committed to this repository.
> Grounded in actual outputs — does not project or invent results.

---

## 1. Safe Claims Supported by Repository Evidence

The following claims are directly supported by committed artifacts and can
be stated without qualification in a journal manuscript.

### Claim S1 — Vote construction controls graph cyclicity

**Statement:** The choice of vote aggregation strategy is the dominant factor
determining cycle prevalence in multi-ranker preference graphs.  Majority-
filtered aggregation (ms2: min_support=2, min_aggregate_margin=0.1) yields
near-acyclic graphs (SciDocs: 1.7% cyclic queries, avg largest SCC ≈ 1.04).
Per-ranker edge inclusion (ms1: min_support=1) yields high cyclicity (SciDocs:
97.5% cyclic, avg largest SCC ≈ 15.6).  A conflict-resolving post-filter
(ms1_drop_mutual: drop mutual 2-cycle pairs) restores near-acyclicity while
retaining more edges than ms2.

**Primary evidence:** `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`

---

### Claim S2 — FAS repair reduces label-aligned structural inconsistency

**Statement:** Greedy MWFAS repair reduces two graph-level structural
inconsistency metrics — backward-edge weight (BEW) and pairwise inconsistency
count (PIC) — when measured against a qrels-derived reference ranking over the
candidate pool.  This effect is largest under high-cyclicity constructions (ms1).

**Example values (SciDocs, ms1):**
- Mean BEW pre → post: 309.09 → 307.96 (Δ 1.13)
- Mean PIC pre → post: 99.84 → 88.08 (Δ 11.76)

**Caveat:** BEW/PIC are measured against a qrels-derived reference, not an
independent ground truth.  This does not assert "closer to the true ranking."

**Primary evidence:** Same table as S1; `table_consistency_qrels_bew.csv`

---

### Claim S3 — FAS repair can harm nDCG@k under high-cyclicity vote construction

**Statement:** Under ms1 vote construction on SciDocs, repaired Copeland hybrid
has a mean per-query ΔnDCG of −0.0091 (repaired − unrepaired), with a
bootstrap 95% CI of [−0.017, −0.003] (2000 bootstrap replications, n=120
queries).  The CI is strictly below zero.

**Primary evidence:** `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`

---

### Claim S4 — The harm concentrates in high-conflict subgraphs

**Statement:** On SciDocs ms1, queries with largest SCC ≥ median show a more
negative mean ΔnDCG (−0.015, CI [−0.027, −0.006], n=70) than queries below
median (−0.001, CI [−0.005, +0.004], n=50).  This suggests harm concentrates
where cycles are most severe.

**Primary evidence:** Same bootstrap table, rows `copeland_scc_high` /
`copeland_scc_low`

---

### Claim S5 — Repair is inactive under near-acyclic vote constructions

**Statement:** Under ms2 and ms1_drop_mutual, repaired and unrepaired rankings
are identical for all method pairs tested (ΔnDCG = 0, CI [0, 0]).  FAS removes
essentially no weight.

**Primary evidence:** Bootstrap table, all ms2 and ms1_drop_mutual rows

---

### Claim S6 — Balance hybrids are retrieval-neutral to repair

**Statement:** Repaired vs unrepaired balance hybrid (BEW-minimizing ranking
extraction) shows no meaningful ΔnDCG under any vote construction or dataset.
The CI always includes zero and effect sizes are negligible (|Δ| < 0.0001).

**Primary evidence:** Bootstrap table, all `balance` rows

---

### Claim S7 — Synthetic baselines consistently outperform the plain FAS-topological ranker

**Statement:** Across all synthetic noise levels (0.05–0.30) and scale points
(n=10–100), `borda` and `score_sum` achieve higher Kendall τ than
`greedy_fas_topological`.  The gap is largest under uniform edge weights.

**Primary evidence:** `docs/tables/main_results.csv`

---

### Claim S8 — FAS greedy runtime scales sub-quadratically in practice

**Statement:** Greedy FAS solver dominates total runtime but scales acceptably:
n=100 items → ~1.2 s total.  The fraction of time in greedy FAS rises from
~49% (n=10) to ~97% (n=100).

**Primary evidence:** `docs/tables/runtime_results.csv`

---

## 2. Claims That Should NOT Be Made

The following claims are **not supported** by the committed evidence.  Making
them in a journal submission would expose the paper to rejection.

| Claim | Reason Not Supportable |
|---|---|
| "FAS repair improves retrieval quality" (unconditionally) | Bootstrap evidence shows strictly negative ΔnDCG for Copeland/ms1 on SciDocs; neutral or zero elsewhere. |
| "Our method outperforms Borda count on IR benchmarks" | Borda / score_sum dominate in all synthetic experiments; real experiments do not include Borda as a standalone benchmark method. |
| "Lower BEW/PIC implies better user-facing retrieval quality" | BEW/PIC are graph metrics vs qrels reference; they do not predict nDCG improvement. |
| "Results generalize to LLM-generated pairwise preferences" | Core canonical package is score-derived; separate bounded real-LLM addendum now exists (SciDocs/HotpotQA/FiQA) and supports only conservative regime-conditional claims. |
| "Results generalize beyond SciDocs and HotpotQA" | Real-LLM addendum now includes bounded FiQA evidence; broad external generalization still requires larger multi-dataset budgets (e.g., BRIGHT + higher query counts). |
| "The method is efficient enough for production use" | Only up to n=100 items tested; no real-time or batch-size analysis. |
| "Exact ILP MWFAS improves over the greedy heuristic in practice" | ILP solver is stubbed; exact-vs-greedy comparison is synthetic only. |
| "Our hybrid α=0.3 is an optimised hyperparameter" | α sweep exists for synthetic data; no validation-set tuning on real data is documented. |

---

## 3. Recommended Title Directions

**Primary option (diagnostic framing):**
> "When Does Cycle Repair Help? Vote Construction, Graph Regime, and the
> Retrieval Impact of Feedback-Arc-Set Repair on Preference Graphs"

**Alternative option (structural focus):**
> "Structural Consistency Without Retrieval Gains: A Study of FAS Repair on
> Multi-Ranker Preference Graphs"

**Option emphasising vote construction as the key variable:**
> "Vote Aggregation Controls Cycle Prevalence: A Diagnostic Study of Graph
> Repair for Multi-Ranker Retrieval Reranking"

---

## 4. Recommended Abstract Framing

> We study whether repairing cyclic inconsistencies in pairwise preference
> graphs — built from multiple IR rankers — improves retrieval effectiveness.
> We show that the vote aggregation strategy, not the repair algorithm itself,
> is the dominant factor controlling graph cyclicity.  Under high-cyclicity
> constructions, greedy minimum-weight feedback-arc-set (MWFAS) repair reduces
> structural inconsistency metrics but does not improve — and can harm —
> nDCG@k for Copeland-based hybrid rankers.  Under near-acyclic constructions,
> repair is effectively inactive.  These findings motivate a nuanced view of
> graph-based consistency repair: it is a useful diagnostic tool and a
> structural regulariser, but not a reliable route to better retrieval.

---

## 5. Recommended Contributions List

1. A controlled study of how vote aggregation strategy (min_support threshold,
   mutual-pair filtering) determines cycle prevalence and SCC structure in
   multi-ranker preference graphs.

2. A bootstrap significance analysis of the repaired-vs-unrepaired nDCG@k gap
   across vote constructions, showing the gap is negative (harmful) under high-
   cyclicity regimes and zero under near-acyclic regimes.

3. A structural consistency analysis showing FAS repair reliably reduces graph–
   label backward-edge weight (BEW) and pairwise inconsistency count (PIC),
   even when nDCG does not improve.

4. A conditional analysis linking nDCG harm to SCC size: harm concentrates in
   high-conflict (large SCC) queries.

5. A reproducible benchmark with all code, pre-computed outputs, and
   statistical analysis scripts released under MIT licence.

---

## 6. Likely Reviewer Objections and Repository Responses

### Objection R1: "Two datasets is insufficient for a Q1 journal."

**Repository response:** FiQA and BRIGHT loaders and processing scripts exist.
The pipeline can be extended with `--dataset fiqa` and `--dataset bright`.
The canonical vote-derived package currently covers SciDocs and HotpotQA only; the real-LLM addendum now includes bounded FiQA evidence.

**Recommended action:** Increase FiQA real-LLM query budget and run BRIGHT, then add them to
`DATASETS` in `scripts/build_paper_evidence_package.py`, and regenerate tables.

---

### Objection R2: "You only tested three weak rankers (BM25, TF-IDF, MiniLM)."

**Repository response:** All three rankers are standard IR baselines.  MiniLM-L6
is a widely used bi-encoder.  Adding a cross-encoder (e.g. MonoBERT) would
strengthen generalization claims.

**Recommended action:** Add a fourth ranker via `scripts/generate_score_file.py`
and re-run the vote-suite pipeline.

---

### Objection R3: "Bootstrap CIs only compare repaired vs unrepaired; you don't
test against the baseline prior-only method."

**Repository response:** The `hybrid_rrf_prior_only` method is present in per-
query CSVs.  Bootstrap comparisons of repaired methods against the prior-only
baseline can be generated from existing outputs using
`scripts/bootstrap_method_deltas.py`.

**Recommended action:** Add `prior_vs_repaired` and `prior_vs_unrepaired` pairs
to the bootstrap analysis loop and include in the paper package.

---

### Objection R4: "BEW/PIC are self-referential — they're measured against the
same qrels signal you're trying to optimise."

**Repository response:** Acknowledged in `MANUSCRIPT_SUMMARY.md` (limitations
section) and in claim S2's caveat.  BEW/PIC are graph-theoretic structural
metrics used to demonstrate that FAS does what it claims structurally, not to
predict nDCG.

**Recommended action:** Frame BEW/PIC explicitly as graph-level diagnostics, not
as retrieval quality proxies.  Add an independent structural metric (e.g.
fraction of edges reversed) that does not reference qrels.

---

### Objection R5: "You have no comparison to a globally-optimal MWFAS solver."

**Repository response:** Exact-vs-greedy comparison exists for synthetic data
(see `docs/tables/exact_vs_greedy_fas.csv`).  The ILP solver is stubbed in
`src/consistency_ranker/mwfas_solver.py`.

**Recommended action:** Implement the ILP stub using `pulp` and run exact-vs-
greedy on real data for a representative query slice.

---

### Objection R6: "The 'ms1_drop_mutual' post-filter is ad hoc and untested."

**Repository response:** ms1_drop_mutual is described as a post hoc edge filter
in `MANUSCRIPT_SUMMARY.md`.  Its effect on cyclicity and nDCG is reported and
consistent across both datasets.

**Recommended action:** Frame ms1_drop_mutual as a sensitivity analysis / middle-
ground construction, not as a principled method.  Report it in an appendix or
as an ablation row.

---

### Objection R7: "n=52 queries for HotpotQA is underpowered."

**Repository response:** This is correct.  The 95% CI for HotpotQA ms1 Copeland
touches zero.  The finding for HotpotQA should be framed as consistent-with-
but-weaker-than the SciDocs result, not as an independent confirmation.

**Recommended action:** Increase the HotpotQA query count, or acknowledge low
power explicitly in the limitations section.

---

*This document should be updated whenever new experiments are run or new
results are committed.*
