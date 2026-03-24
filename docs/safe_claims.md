# Safe Claims — LLM Pairwise Baseline Evidence

> **Updated:** 2026-03-24
> **Scope:** Claims safe to make regarding LLM pairwise baseline experiments.
> Complements `SAFE_CLAIMS_FOR_PAPER.md` (core graph-repair claims).
> Evidence-type labels: `real run` | `pilot run` | `dry-run validation`.

---

## Part A — Supported Claims

### LLM-S1 — Real LLM pairwise judgments produce highly cyclic preference graphs

> "On SciDocs, real gpt-4o-mini pairwise judgments produced cyclic preference
> graphs on 19/20 queries (95%), with mean 7.2 FAS edges removed per query.
> On HotpotQA, 9/10 queries (90%) were cyclic, with mean 4.3 FAS edges removed."

**Evidence type:** real run (OpenAI gpt-4o-mini, temperature=0)
**Artifacts:** `outputs/openai_scidocs_real_run_q20_k15/openai_per_query.csv`,
`outputs/openai_hotpotqa_real_run_q10_k15/openai_per_query.csv`

### LLM-S2 — FAS repair does not improve nDCG under real LLM preferences

> "Under real gpt-4o-mini pairwise judgments, repaired Copeland hybrid yields
> ΔnDCG = −0.0003 on SciDocs (20 queries) and −0.0070 on HotpotQA (10
> queries), both negative. Balance hybrid shows identical deltas. Repair does
> not improve retrieval quality under LLM-sourced preferences."

**Evidence type:** real run
**Artifacts:** `outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv`,
`outputs/openai_hotpotqa_real_run_q10_k15/openai_summary.csv`
**Caveat:** No bootstrap CIs computed. n=20 and n=10 are bounded pilots.
The direction is consistent across both datasets but formal significance
testing requires either larger samples or bootstrap analysis.

### LLM-S3 — The finding is consistent across providers (directional)

> "A quota-limited Gemini pilot (2 SciDocs queries, 380 pairs) showed
> ΔnDCG = −0.0045, directionally consistent with the OpenAI finding."

**Evidence type:** pilot run (Gemini, quota-limited)
**Artifact:** `outputs/gemini_scidocs_real_pilot/gemini_summary.csv`
**Caveat:** n=2 has no statistical power. This is a cross-provider
consistency observation, not independent confirmation.

### LLM-S4 — Simple aggregation methods match or exceed FAS-repair methods

> "Under real LLM preferences, Copeland, win-rate, and Markov-chain
> aggregation all achieve higher nDCG than FAS-topological and
> FAS-weighted-balance on both datasets."

**Evidence type:** real run
**Artifacts:** summary CSVs in both OpenAI output directories

### LLM-S5 — Pipeline infrastructure is complete and provider-agnostic

> "The LLM pairwise pipeline supports OpenAI and Gemini, with disk-backed
> caching, retry with exponential backoff, and resumable runs."

**Evidence type:** real run (demonstrated by both provider runs)
**Artifact:** `src/rerankers/llm_pairwise.py`

---

## Part B — Do Not Claim

### LLM-DN1 — "These results are statistically significant"

No bootstrap CIs computed. n=20 and n=10 are small. The direction is
consistent but formal significance is not established.

### LLM-DN2 — "These are full-scale benchmark reproductions"

These are bounded pilots (20 and 10 queries). They are not
full-benchmark evaluations comparable to published results.

### LLM-DN3 — "Gemini and OpenAI produce comparable judgments"

Different query counts, different k values, different models. No
controlled cross-provider comparison was conducted.

### LLM-DN4 — "The LLM baseline concern is fully resolved"

Substantially addressed but not fully resolved: bounded pilots, no
bootstrap CIs, no position debiasing in these runs.
