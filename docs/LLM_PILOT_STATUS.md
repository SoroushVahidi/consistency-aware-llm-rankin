# LLM Pilot Status and Editor-Concern Assessment

> **Updated:** 2026-04-06
> **Role:** Authoritative source for the question: *"Has the editor's
> LLM-baseline concern been addressed?"*

---

## 1. Pilot Inventory

| Pilot | Provider | Dataset | Queries | top_k | Pairs | Model | Status | Artifact |
|-------|----------|---------|---------|-------|-------|-------|--------|----------|
| Dry-run validation | — (mock MD5) | SciDocs | 50 | 20 | 9,500 | — | complete | `outputs/llm_scidocs_pilot_comparison/` |
| OpenAI real — SciDocs | OpenAI | SciDocs | 50/50 | 15 | 5,250 | gpt-4o-mini | complete | `outputs/openai_scidocs_real_pairwise_q50_k15/` |
| OpenAI real — HotpotQA | OpenAI | HotpotQA | 20/20 | 15 | 900 | gpt-4o-mini | complete | `outputs/openai_hotpotqa_real_run_q20_k15/` |
| OpenAI real — FiQA | OpenAI | FiQA | 10/20 target (usable-query constrained) | 15 | 46 | gpt-4o-mini | complete (bounded) | `outputs/openai_fiqa_real_run_q20_k15/` |
| Gemini real — SciDocs | Google Gemini | SciDocs | 2/5 | 20 | 380 | gemini-3.1-flash-lite-preview | partial (quota) | `outputs/gemini_scidocs_real_pilot/` |

---

## 2. Real OpenAI Cross-Dataset Summary

Canonical manuscript-facing 3-dataset summary is maintained at:
`outputs/openai_real_llm_cross_dataset_summary.md`.

- SciDocs 50q: cyclic 46/50 (92.0%), ΔnDCG(rep−unrep, copeland) = −0.0010, 95% CI [−0.001905, −0.000208].
- HotpotQA 20q: cyclic 16/20 (80.0%), ΔnDCG = 0.0000, 95% CI [0.0, 0.0].
- FiQA (new): cyclic 1/10 (10.0%), ΔnDCG = 0.0000, 95% CI [0.0, 0.0].

Interpretation should remain conservative: regime-sensitive cyclicity and
non-uniform relevance effects.

---

## 3. Editor's LLM-Baseline Concern

**Status: SUBSTANTIALLY ADDRESSED (bounded real-LLM evidence on three datasets).**

| Concern element | Status |
|-----------------|--------|
| LLM pairwise pipeline implemented | done — OpenAI + Gemini providers |
| Pipeline validated end-to-end | done — dry-run + real runs |
| Real LLM preferences on SciDocs | done — 50 queries |
| Real LLM preferences on additional datasets | done — HotpotQA + FiQA |
| Repaired-vs-unrepaired finding under real LLM | done — small/non-uniform; negative on SciDocs, null on HotpotQA/FiQA |
| Bootstrap CIs from real LLM data | done — OpenAI bootstrap summaries committed |
| Full-scale benchmark reproduction | not done — runs remain bounded and should be described as such |

---

## 4. API Usage (OpenAI runs used in current 3-dataset summary)

| Run | API calls | Tokens | Cost |
|-----|-----------|--------|------|
| OpenAI SciDocs 50q | 5,250 | 1,042,062 | $0.1582 |
| OpenAI HotpotQA 20q | 900 | 316,298 | $0.0483 |
| OpenAI FiQA 10q processed | 46 | 22,602 | $0.0034 |
| **Total** | **6,196** | **1,380,962** | **$0.2099** |
