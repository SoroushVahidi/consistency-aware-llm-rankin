# LLM Pilot Status and Editor-Concern Assessment

> **Purpose:** Single authoritative tracking document for the LLM pairwise
> pilot experiments. Records completed pilots, blocked pilots, and the
> comparison framework to be populated once real API results arrive.
>
> **Grounding rule:** Only committed artifacts are cited. Nothing is projected
> or invented. Evidence-type labels follow the four-tier system:
> `real completed run` | `pilot run` | `dry-run validation` | `pending`.
>
> **Role:** This document is the authoritative source for answering the
> question: *"Has the editor's LLM-baseline concern been addressed?"*

---

## 1. Current Pilot Inventory

| Pilot | Evidence type | Dataset | Queries | Model | Status | Artifact |
|-------|---------------|---------|---------|-------|--------|----------|
| Dry-run pipeline validation | dry-run validation | SciDocs | 50 | deterministic mock (MD5) | ✅ **completed** | `outputs/llm_scidocs_pilot_comparison/` |
| Real API pilot (30 queries) | pending → pilot run | SciDocs | 0 of 30 | gpt-4o-mini | ❌ **blocked** — `insufficient_quota` | `outputs/llm_scidocs_real_pilot/` |

### Notes on the dry-run pilot

The dry-run pilot (`outputs/llm_scidocs_pilot_comparison/`) uses
deterministic mock judgments (MD5 hashing of document IDs) to simulate LLM
pairwise comparisons. This is **not real LLM output**. The pilot validates
that the pipeline infrastructure (judgment collection, caching, aggregation,
evaluation) runs correctly end-to-end. Key structural observation: 100% of
the 50 sampled SciDocs queries produced cyclic preference graphs under mock
judgments (mean 90.8 FAS edges removed).

Do not cite numerical nDCG results from the dry-run as evidence of LLM
reranking performance.

### Notes on the blocked real pilot

`outputs/llm_scidocs_real_pilot/config.json` records that 0 queries were
processed before the API key returned `insufficient_quota`. The script
`scripts/run_llm_scidocs_real_pilot.py` is fully built and resumable via
disk-backed caching. Once billing credits are available, it will collect
real gpt-4o-mini pairwise judgments on 30 SciDocs queries (top-20 candidates,
11 400 API calls total, estimated cost ~$0.10–0.30 at gpt-4o-mini pricing).

---

## 2. Editor's LLM-Baseline Concern — Resolution Status

> **Overall status: PARTIALLY DONE**

The editor flagged that the manuscript lacked LLM-based baselines in two
respects:
1. No LLM-generated pairwise preferences used in experiments.
2. No comparison of graph-repair methods with LLM-elicited judgments.

| Concern element | Status | Evidence |
|-----------------|--------|----------|
| LLM baselines implemented in code | ✅ **done** | `src/rerankers/llm_pointwise.py`, `llm_pairwise.py`, `llm_listwise.py` |
| LLM pairwise pipeline validated end-to-end | ✅ **done** | dry-run, 50 SciDocs queries — `outputs/llm_scidocs_pilot_comparison/` |
| Real LLM pairwise preferences in evaluation | ❌ **not done** | blocked by API quota |
| LLM results included in comparison table | ❌ **not done** | pending real API run |
| Manuscript text positioning LLM work | ✅ **done** | `docs/related_work_positioning_note.md` |

### What "partially done" means for the cover letter

> "We have implemented pointwise, pairwise, and listwise LLM reranking
> modules and validated the pairwise pipeline end-to-end via a controlled
> dry-run experiment on 50 SciDocs queries. A real gpt-4o-mini pilot (30
> queries) is prepared and fully resumable; execution was deferred due to
> API billing constraints at the time of submission. We note this explicitly
> in §Limitations and provide the implementation for reviewer inspection."

---

## 3. Comparison Framework — To Be Populated on New Pilot Arrival

When a new real OpenAI pilot directory appears in `outputs/`, use the
checklist and table templates below to assess it.

### 3.1 Arrival checklist

- [ ] New output directory created (e.g., `outputs/llm_scidocs_real_pilot_v2/` or similar)
- [ ] Summary CSV committed (e.g., `pilot_summary.csv` with method × metric rows)
- [ ] Per-query CSV committed (e.g., `pilot_per_query.csv`)
- [ ] JSONL judgments file committed (or confirmed not committed due to size)
- [ ] Config JSON committed with `dry_run: false` and `n_queries_processed > 0`

### 3.2 Comparison template: new pilot vs. earlier dry-run pilot

Populate the table below once the real pilot summary CSV is available.

| Method | nDCG@20 (dry-run, 50 q) | nDCG@20 (real pilot, N q) | Δ (real − dry-run) |
|--------|------------------------|--------------------------|---------------------|
| llm_pairwise_copeland | 0.5525 | _pending_ | — |
| bt_from_llm | 0.5511 | _pending_ | — |
| win_rate_from_llm | 0.5525 | _pending_ | — |
| markov_from_llm | 0.5644 | _pending_ | — |
| tournament_sort_from_llm | 0.5631 | _pending_ | — |
| greedy_fas_topological | 0.4005 | _pending_ | — |
| greedy_fas_weighted_balance | 0.4007 | _pending_ | — |
| greedy_fas_copeland | 0.4007 | _pending_ | — |
| hybrid_rrf_repaired_copeland_a03 | 0.4858 | _pending_ | — |
| hybrid_rrf_unrepaired_copeland_a03 | 0.5525 | _pending_ | — |
| hybrid_rrf_repaired_balance_a03 | 0.4858 | _pending_ | — |
| hybrid_rrf_unrepaired_balance_a03 | 0.5525 | _pending_ | — |

> **Note:** The dry-run nDCG numbers are from mock (non-LLM) judgments and
> serve only as a structural reference. The comparison is primarily useful for
> checking that the pipeline produces internally consistent results
> (e.g., similar ranking between methods) rather than for interpreting absolute
> nDCG values.

### 3.3 Key questions to answer once real pilot results arrive

1. **Do real LLM judgments also produce 100% cyclic graphs?**  
   — Check `% cyclic queries` in the new PILOT_COMPARISON.md.

2. **Does FAS repair improve nDCG under real LLM judgments?**  
   — Check ΔnDCG (repaired − unrepaired) for copeland and balance.
   — If CI strictly positive: upgrade editor-concern status to **done**.
   — If CI includes zero or is negative: status remains **partially done**;
     update DN4 and CC2 in `docs/safe_claims.md`.

3. **How does the real pilot compare to the score-derived baselines?**  
   — Cross-encoder achieved nDCG = 0.8977 on SciDocs (top-20).
   — Direct LLM Copeland serves as the LLM-preference baseline.
   — Report Δ (LLM Copeland − cross-encoder) with appropriate caveats.

4. **Does the new pilot materially change the manuscript story?**  
   — If repair under real LLM judgments shows the same regime-dependence
     as under qrels-derived preferences → story is consistent, no major
     revision needed.
   — If repair shows a robustly positive effect → update CC2, possibly S8.
   — If repair shows a strongly negative effect → add new DN item.

### 3.4 Documents to update based on new pilot

| Document | When to update | What to change |
|----------|----------------|----------------|
| `docs/safe_claims.md` | Always | Upgrade S12 evidence type from "dry-run validation" to "pilot run"; add real nDCG values; update DN4 if real LLM run completed |
| `docs/revision_strategy.md` | Always | Mark "LLM pairwise run on real data" as done in §1 table; update §7 concern status |
| `docs/related_work_positioning_note.md` | If story changes materially | Update Paradigm 3 run status; revise §7 summary table |
| This document (`LLM_PILOT_STATUS.md`) | Always | Fill in §3.2 table; update §2 resolution status |

---

## 4. Safe-Claim Additions Contingent on New Pilot Results

These claim drafts are **templates only** — do not promote them to Part A of
`docs/safe_claims.md` until real pilot results are available.

### Draft S13 — LLM pairwise preference graphs are highly cyclic (conditional)

> **Conditional on:** real pilot `% cyclic queries` ≥ 80%.
>
> *"On SciDocs, real gpt-4o-mini pairwise judgments produced cyclic preference
> graphs on X/N queries (Y%), with mean Z FAS edges removed per query. This
> confirms that the cycle-repair motivation extends from score-derived
> preferences to LLM-elicited preferences."*
>
> **Evidence type (once available):** pilot run  
> **Artifact (once available):** `outputs/<new_pilot_dir>/PILOT_COMPARISON.md`

### Draft S14 — FAS repair effect under real LLM judgments (conditional)

> **Conditional on:** real pilot results with n_queries_processed > 0.
>
> *"Under real gpt-4o-mini pairwise judgments on N SciDocs queries (top-20
> candidates), FAS repair produced ΔnDCG = X (repaired − unrepaired Copeland).
> [95% CI: pending bootstrap if n ≥ 30.] This result [supports / is consistent
> with / contradicts] the regime-dependence pattern observed with score-derived
> preferences."*
>
> **Evidence type (once available):** pilot run (upgrade to "real completed run"
> if ≥ 100 queries across ≥ 2 datasets)

---

## 5. Non-Actions (to avoid contaminating evidence record)

- Do **not** cite dry-run nDCG values as representative of LLM performance.
- Do **not** add S13 or S14 until real pilot results are committed.
- Do **not** update the editor-concern status to **done** until at least one
  dataset has real LLM judgment results with n_queries_processed > 0.
- Do **not** modify code or run new experiments in this document's scope.
