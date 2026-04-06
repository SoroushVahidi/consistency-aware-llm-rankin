# Safe Claims for Paper Writing

> Conservative statement set for manuscript preparation.  All claims in §1 are
> directly backed by committed artifacts in this repository.  All claims in §2
> go beyond the evidence and must **not** be stated without additional experiments.

---

## 1. Statements That Are Clearly Supported Now

These can appear in a paper body or abstract without additional qualification
(though caveats noted below each claim should appear somewhere in the paper).

### SC-1 — Vote construction controls cycle prevalence

> "Under majority-style vote aggregation (min_support=2, min_aggregate_margin=0.1),
> preference graphs are near-acyclic: on SciDocs, 1.68% of queries have cyclic
> preference graphs (average largest SCC 1.04).  Under per-ranker vote inclusion
> (min_support=1), 97.5% of queries are cyclic (average largest SCC 15.6)."

*Evidence:* `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv`  
*Caveat:* Measured on SciDocs only; HotpotQA shows similar pattern (0% vs 94.2% cyclic).

---

### SC-2 — A conflict-mitigating post-filter restores near-acyclicity

> "Dropping mutual 2-cycle pairs after per-ranker edge inclusion (ms1_drop_mutual)
> restores near-acyclicity (SciDocs: 9.17% cyclic, average largest SCC 1.80)
> while retaining more edges than majority-style aggregation (159.4 vs 72.4 mean edges)."

*Evidence:* Same table as SC-1.  
*Caveat:* ms1_drop_mutual is a post-hoc filter, not fit on a validation set.

---

### SC-3 — FAS repair reduces label-aligned graph inconsistency

> "On SciDocs under ms1, greedy MWFAS repair reduces mean backward-edge weight
> (BEW) from 309.09 to 307.96 (Δ1.13) and pairwise inconsistency count (PIC)
> from 99.84 to 88.08 (Δ11.76), measured against a qrels-derived reference ranking."

*Evidence:* `table_consistency_qrels_bew.csv`, `table_graph_ndcg_and_consistency.csv`  
*Caveat:* BEW and PIC are measured against the same qrels used to compute nDCG; they are not an independent measure of "truth proximity."

---

### SC-4 — Repair harms Copeland nDCG under high-cyclicity construction

> "Under per-ranker vote inclusion (ms1) on SciDocs, repaired Copeland hybrid
> yields a mean per-query ΔnDCG of −0.0091 (repaired − unrepaired), with a
> bootstrap 95% CI of [−0.017, −0.003] (n=120 queries, 2000 replications).
> The confidence interval is strictly below zero."

*Evidence:* `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`  
*Caveat:* Single dataset; CI is query-level bootstrap of mean Δ, not a hierarchical model.

---

### SC-5 — Retrieval harm concentrates in high-conflict queries

> "Stratified analysis on SciDocs ms1 Copeland shows ΔnDCG is more negative for
> queries with largest SCC ≥ median (n=70: mean −0.015, CI [−0.027, −0.006])
> than for below-median queries (n=50: mean −0.001, CI [−0.005, +0.004])."

*Evidence:* Same bootstrap table, rows `copeland_scc_high` and `copeland_scc_low`.  
*Caveat:* Median split is post-hoc; SCC size and nDCG harm may share a common cause.

---

### SC-6 — Repair is inactive under near-acyclic constructions

> "Under ms2 and ms1_drop_mutual vote constructions on both SciDocs and HotpotQA,
> repaired and unrepaired Copeland rankings are identical for all queries tested
> (ΔnDCG = 0.0 for all, CI [0, 0]).  FAS removes essentially no edge weight."

*Evidence:* `table_bootstrap_delta_ndcg.csv`, all ms2 and ms1_drop_mutual rows.

---

### SC-7 — Balance hybrids are repair-neutral across all conditions tested

> "Repaired vs unrepaired weighted-balance hybrid rankings show no meaningful
> ΔnDCG under any vote construction or dataset tested; all bootstrap CIs include
> zero and |Δ| < 10⁻⁴."

*Evidence:* All `balance` rows in `table_bootstrap_delta_ndcg.csv`.

---

### SC-8 — Synthetic baselines consistently outperform greedy FAS ranking

> "In synthetic experiments across noise levels 0.05–0.30 (n=20 items) and
> scale points 10–100 (noise=0.10), Borda count and score-sum achieve higher
> Kendall τ than the greedy-FAS topological ranker.  The gap is largest under
> uniform edge weights."

*Evidence:* `docs/tables/main_results.csv`.  
*Caveat:* Synthetic data only; ground truth is a latent quality score, not qrels.

---

### SC-9 — Greedy FAS runtime dominates and scales with graph density

> "Greedy FAS accounts for 49% of total runtime at n=10 items, rising to 97%
> at n=100 items (wall time: 0.004 s to 1.232 s).  Runtime scales super-linearly
> with n for dense pairwise graphs."

*Evidence:* `docs/tables/runtime_results.csv`.  
*Caveat:* Synthetic pairwise graphs are fully dense (all n(n-1) directed edges); real graphs are sparser.

---

### SC-10 — The repository is fully reproducible for committed evidence

> "All evidence tables in `outputs/pub_vote_cmp_v2/paper_package/` and
> `docs/tables/` were produced by committed scripts and can be regenerated
> (from committed intermediate outputs, without network access) using
> `python scripts/generate_q1_tables.py`."

*Evidence:* Committed outputs + `docs/REPRODUCTION_Q1.md`.  
*Caveat:* Re-running the full pipeline from raw data requires HuggingFace Hub access and is not reproducible offline.

---

## 2. Statements That Would Be Too Strong or Unsupported Now

Do **not** make any of these claims in a submitted manuscript.

### US-1 — FAS repair improves retrieval quality

> ~~"Minimum weighted feedback arc set repair improves nDCG@k for preference-based ranking."~~

*Why unsupported:* Bootstrap evidence shows strictly negative ΔnDCG for Copeland/ms1 on SciDocs; neutral elsewhere.

---

### US-2 — The method outperforms Borda count

> ~~"Our consistency-repair method outperforms Borda count on information retrieval benchmarks."~~

*Why unsupported:* Borda and score_sum dominate in synthetic experiments; real-data experiments do not include Borda as a standalone comparison baseline.

---

### US-3 — Lower BEW/PIC implies better retrieval

> ~~"Reducing graph structural inconsistency (BEW, PIC) improves user-facing retrieval effectiveness."~~

*Why unsupported:* BEW/PIC decrease (SC-3) while nDCG also decreases (SC-4) for the same condition (SciDocs ms1 Copeland).

---

### US-4 — Results generalise to LLM-generated preferences

> ~~"These findings apply to LLM pairwise preference judgements."~~

*Why unsupported (for canonical package):* Core canonical experiments use BM25/TF-IDF/MiniLM score-derived votes. Separate bounded real-LLM addendum exists (SciDocs/HotpotQA/FiQA) and supports only conservative regime-conditional transfer language.

---

### US-5 — Results generalise beyond SciDocs and HotpotQA

> ~~"We demonstrate consistent behaviour across diverse retrieval benchmarks."~~

*Why unsupported (for broad generalization):* Canonical package remains two-dataset, while the real-LLM addendum now includes bounded FiQA evidence. Broader claims still require larger query budgets and more datasets (e.g., BRIGHT).

---

### US-6 — Exact MWFAS outperforms greedy on real data

> ~~"The exact ILP-based MWFAS solver produces superior rankings compared to the greedy heuristic."~~

*Why unsupported:* ILP solver is a stub; exact-vs-greedy comparison is synthetic only.

---

### US-7 — The hybrid parameter α=0.3 is optimised

> ~~"We tuned the hybrid balance parameter α on a validation set."~~

*Why unsupported:* α sweep exists only for synthetic data; no validation-set tuning on real data is documented.

---

### US-8 — The method is efficient at scale

> ~~"Our method is computationally efficient and suitable for production use."~~

*Why unsupported:* Only n ≤ 100 items tested; greedy FAS takes ~1.2 s at n=100 on dense synthetic graphs; no real-world latency analysis.

---

## 3. Wording Suggestions for Conservative Paper Framing

| Avoid | Prefer |
|---|---|
| "repair improves ranking quality" | "repair reduces structural inconsistency, but does not uniformly improve nDCG@k" |
| "our method outperforms baselines" | "score-sum and Borda count consistently outperform the greedy-FAS topological ranker in synthetic experiments" |
| "we demonstrate that …" | "our results suggest that …" / "under the conditions tested, …" |
| "cycle repair is beneficial" | "cycle repair is conditionally harmful (high-cyclicity regime) or inactive (low-cyclicity regime)" |
| "results generalise" | "results hold on the currently examined bounded datasets (SciDocs, HotpotQA, bounded FiQA); broader generalisation requires further study" |
| "the dominant factor is …" | "the dominant factor under our experimental conditions is …" |
| "proves that BEW/PIC reduction is useful" | "shows that FAS repair measurably reduces graph–label backward-edge weight; the connection to retrieval quality requires caution (see §X)" |

---

## 4. Recommended Narrative Arc for a Submission

1. **Frame as a diagnostic study**, not a method proposal: you study *when* and *whether* cycle repair helps, not that it always helps.
2. **Lead with the vote-construction finding** (SC-1, SC-2): it is the clearest and most novel result.
3. **Present the harm finding** (SC-4) as the central negative result, which is scientifically interesting precisely because it is non-obvious.
4. **Use the structural result** (SC-3) as a secondary finding: FAS repair does do something — it reduces graph–label tension — even when nDCG does not improve.
5. **Frame the balance-hybrid neutrality** (SC-7) as a robustness check.
6. **Acknowledge generalisability limits** (US-4, US-5) explicitly in the Limitations section.
