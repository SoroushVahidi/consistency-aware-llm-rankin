# LLM Pilot Status and Editor-Concern Assessment

> **Updated:** 2026-03-24
> **Role:** Authoritative source for the question: *"Has the editor's
> LLM-baseline concern been addressed?"*

---

## 1. Pilot Inventory

| Pilot | Provider | Dataset | Queries | top_k | Pairs | Model | Status | Artifact |
|-------|----------|---------|---------|-------|-------|-------|--------|----------|
| Dry-run validation | — (mock MD5) | SciDocs | 50 | 20 | 9,500 | — | **complete** | `outputs/llm_scidocs_pilot_comparison/` |
| OpenAI real — SciDocs | OpenAI | SciDocs | **20**/20 | 15 | 2,100 | gpt-4o-mini | **complete** | `outputs/openai_scidocs_real_run_q20_k15/` |
| OpenAI real — HotpotQA | OpenAI | HotpotQA | **10**/10 | 15 | 450 | gpt-4o-mini | **complete** | `outputs/openai_hotpotqa_real_run_q10_k15/` |
| Gemini real — SciDocs | Google Gemini | SciDocs | 2/5 | 20 | 380 | gemini-3.1-flash-lite-preview | **partial** (quota) | `outputs/gemini_scidocs_real_pilot/` |
| OpenAI blocked (legacy) | OpenAI | SciDocs | 0/30 | 20 | 0 | gpt-4o-mini | **blocked** | `outputs/llm_scidocs_real_pilot/` |

---

## 2. Real LLM Results Summary

### SciDocs — OpenAI gpt-4o-mini (20 queries, k=15)

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|--------|------|------|
| llm_pairwise_copeland | 0.9566 | 0.9141 | 4.60 | 4.60 |
| bt_from_llm | 0.9566 | 0.9141 | 4.80 | 4.80 |
| win_rate_from_llm | 0.9566 | 0.9141 | 4.60 | 4.60 |
| markov_from_llm | **0.9574** | 0.9171 | 4.85 | 4.85 |
| tournament_sort_from_llm | 0.9533 | 0.9100 | 4.25 | 4.25 |
| greedy_fas_topological | 0.9474 | 0.8936 | 5.25 | 5.25 |
| greedy_fas_weighted_balance | 0.9464 | 0.8924 | 6.40 | 6.40 |
| greedy_fas_copeland | 0.9464 | 0.8924 | 6.40 | 6.40 |
| hybrid_rrf_repaired_copeland_a03 | 0.9563 | 0.9132 | 4.45 | 4.45 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.9566 | 0.9141 | 4.60 | 4.60 |
| hybrid_rrf_repaired_balance_a03 | 0.9563 | 0.9132 | 4.45 | 4.45 |
| hybrid_rrf_unrepaired_balance_a03 | 0.9566 | 0.9141 | 4.60 | 4.60 |

- Cyclic queries: 19/20 (95%). Avg FAS edges removed: 7.2.
- Repaired vs unrepaired ΔnDCG: **−0.0003** (copeland), **−0.0003** (balance).

### HotpotQA — OpenAI gpt-4o-mini (10 queries, k=15)

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|--------|------|------|
| llm_pairwise_copeland | 0.8929 | 0.8444 | 3.10 | 3.10 |
| bt_from_llm | 0.8859 | 0.8361 | 3.00 | 3.00 |
| win_rate_from_llm | 0.8929 | 0.8444 | 3.10 | 3.10 |
| markov_from_llm | 0.8868 | 0.8375 | 3.70 | 3.70 |
| tournament_sort_from_llm | **0.9008** | 0.8583 | 2.50 | 2.50 |
| greedy_fas_topological | 0.8778 | 0.8267 | 3.80 | 3.80 |
| greedy_fas_weighted_balance | 0.8778 | 0.8267 | 4.30 | 4.30 |
| greedy_fas_copeland | 0.8778 | 0.8267 | 4.30 | 4.30 |
| hybrid_rrf_repaired_copeland_a03 | 0.8859 | 0.8361 | 2.90 | 2.90 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.8929 | 0.8444 | 3.10 | 3.10 |
| hybrid_rrf_repaired_balance_a03 | 0.8859 | 0.8361 | 2.90 | 2.90 |
| hybrid_rrf_unrepaired_balance_a03 | 0.8929 | 0.8444 | 3.10 | 3.10 |

- Cyclic queries: 9/10 (90%). Avg FAS edges removed: 4.3.
- Repaired vs unrepaired ΔnDCG: **−0.0070** (copeland), **−0.0070** (balance).

### Gemini — SciDocs (2 queries, k=20, quota-limited)

- Best nDCG@20: 0.9855 (Copeland). ΔnDCG: −0.0045. Cyclic: 2/2 (100%).
- Too small for statistical claims; directionally consistent with OpenAI runs.

---

## 3. Editor's LLM-Baseline Concern

**Status: SUBSTANTIALLY ADDRESSED.**

| Concern element | Status |
|-----------------|--------|
| LLM pairwise pipeline implemented | **done** — OpenAI + Gemini providers |
| Pipeline validated end-to-end | **done** — dry-run (50q) + real runs |
| Real LLM preferences on SciDocs | **done** — 20 queries, 2,100 pairs (OpenAI) |
| Real LLM preferences on second dataset | **done** — 10 queries, 450 pairs (HotpotQA) |
| Repaired-vs-unrepaired finding under real LLM | **done** — ΔnDCG negative on both datasets |
| Bootstrap CIs from real LLM data | **not done** — n=20/10 is borderline; possible but not computed |
| Full-scale (≥50 queries) real LLM run | **not done** — bounded pilots only |

**Justification:** Real gpt-4o-mini pairwise judgments on two datasets
(SciDocs 20q, HotpotQA 10q) confirm that LLM preferences produce highly
cyclic graphs (90–95%) and that FAS repair does not improve — and slightly
hurts — nDCG. This is consistent with the qrels-derived findings. The runs
are bounded pilots, not full-scale reproductions, and should be described
as such in the manuscript.

---

## 4. API Usage

| Run | API calls | Tokens | Cost | Time |
|-----|-----------|--------|------|------|
| OpenAI SciDocs | 2,100 | 971,078 | $0.15 | 20 min |
| OpenAI HotpotQA | 450 | 161,205 | $0.02 | 4.7 min |
| Gemini SciDocs | 307 | 145,678 | free tier | 48 min |
| **Total** | **2,857** | **1,277,961** | **$0.17** | **~73 min** |
