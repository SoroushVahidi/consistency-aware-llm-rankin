# Safe Claims — Real LLM Pairwise Evidence

> **HISTORICAL (flagged 2026-07-31).** Concerns bounded real-OpenAI LLM
> pairwise runs (SciDocs 50q/HotpotQA 20q/FiQA 10q) from 2026-04-06, and long
> predates the 2026-07-29/30 real-LLM exploratory pilot and its cluster-aware
> re-analysis (`reports/real_llm_clustered_reanalysis_20260730T023745Z/`,
> `docs/CONTRIBUTIONS.md` §1.2). Already referenced as "historical package
> era" by `README.md`'s own doc index, but previously missing this in-file
> banner. Treat as historical context, not an actively-maintained claims list.

> **Updated:** 2026-04-06
> **Scope:** Claims safe to make for manuscript text about real OpenAI pairwise runs.
> Complements `SAFE_CLAIMS_FOR_PAPER.md` (core non-LLM graph-repair claims).

---

## Part A — Supported Claims

### LLM-S1 — Real LLM cyclicity is regime-sensitive across datasets

> "In our real OpenAI pairwise runs, SciDocs (46/50; 92.0%) and HotpotQA
> (16/20; 80.0%) show high cyclic-query rates, while FiQA is lower-cyclicity
> in the current run configuration (1/10; 10.0%)."

**Evidence type:** real run (OpenAI gpt-4o-mini, temperature=0)  
**Artifact:** `outputs/openai_real_llm_cross_dataset_summary.md`

### LLM-S2 — Repaired-vs-unrepaired relevance effects are small and dataset-dependent

> "Repaired−unrepaired copeland hybrid ΔnDCG is small and non-uniform:
> SciDocs: −0.0010 (95% CI [−0.001905, −0.000208]); HotpotQA: 0.0000
> (95% CI [0.0, 0.0]); FiQA: 0.0000 (95% CI [0.0, 0.0])."

**Evidence type:** real run + bootstrap summaries  
**Artifacts:** `outputs/openai_scidocs_real_pairwise_q50_k15/openai_bootstrap_summary.csv`,
`outputs/openai_hotpotqa_real_run_q20_k15/openai_bootstrap_summary.csv`,
`outputs/openai_fiqa_real_run_q20_k15/openai_bootstrap_summary.csv`,
`outputs/openai_real_llm_cross_dataset_summary.md`

### LLM-S3 — Structural-vs-relevance decoupling is plausible, not universal

> "The three-dataset real-LLM evidence supports a conservative interpretation:
> high cyclicity does not guarantee relevance gains from repair, and lower
> cyclicity can coincide with near-zero repaired-vs-unrepaired differences."

**Evidence type:** synthesis from real runs  
**Artifact:** `outputs/openai_real_llm_cross_dataset_summary.md`

### LLM-S4 — Best-performing method differs by dataset

> "Best nDCG@15 methods are not identical across datasets in the real runs:
> `llm_pairwise_copeland` leads on SciDocs and FiQA, while
> `tournament_sort_from_llm` leads on HotpotQA."

**Evidence type:** real run summaries  
**Artifact:** `outputs/openai_real_llm_cross_dataset_summary.md`

---

## Part B — Do Not Claim

### LLM-DN1 — "Repair improves retrieval quality in general"

Not supported. The observed ΔnDCG is negative on SciDocs and null on
HotpotQA/FiQA in these runs.

### LLM-DN2 — "These are full benchmark evaluations"

Not supported. These are bounded real-LLM runs (SciDocs 50q, HotpotQA
20q, FiQA 10 processed queries).

### LLM-DN3 — "Low cyclicity on FiQA is universal"

Not supported. FiQA evidence currently reflects one bounded run where
10 usable queries were processed.

### LLM-DN4 — "Cross-dataset differences prove causal mechanisms"

Not supported. The evidence is comparative and descriptive; it is not a
controlled causal study.
