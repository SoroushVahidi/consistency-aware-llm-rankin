# LLM Real Pilot Results — Authoritative Summary

> **Updated:** 2026-04-06
> **Scope:** Inventory and conservative interpretation of committed real-LLM
> pairwise evidence in this repository.

---

## 1. Current real-LLM evidence package (OpenAI)

Primary manuscript-facing summary:
- `outputs/openai_real_llm_cross_dataset_summary.md`

Included runs:
- SciDocs 50q (`outputs/openai_scidocs_real_pairwise_q50_k15/`)
- HotpotQA 20q (`outputs/openai_hotpotqa_real_run_q20_k15/`)
- FiQA bounded run, 10 processed queries (`outputs/openai_fiqa_real_run_q20_k15/`)

For each run, committed artifacts include per-query metrics, method summaries,
and bootstrap summaries for repaired-vs-unrepaired ΔnDCG.

---

## 2. Strongest safe conclusions

1. Real OpenAI pairwise judgments show **regime-sensitive cyclicity**:
   high cyclicity on SciDocs/HotpotQA and lower cyclicity on FiQA in the
   current bounded run.
2. Repaired-vs-unrepaired relevance deltas are **small and dataset-dependent**:
   slightly negative on SciDocs, near-zero on HotpotQA and FiQA.
3. This supports a conservative **structural-vs-relevance decoupling** framing:
   cycle repair can improve structure-oriented diagnostics without implying
   universal nDCG gains.

---

## 3. What must NOT be claimed

1. Do not claim universal retrieval improvement from repair.
2. Do not claim full benchmark reproduction across all datasets/query budgets.
3. Do not claim cross-dataset differences establish causal mechanisms.
4. Do not claim provider comparability from quota-limited Gemini evidence.

---

## 4. Remaining key limitation

The evidence is materially stronger than earlier two-dataset pilots, but still
bounded (especially FiQA: 10 processed queries), so manuscript language should
remain conservative and regime-conditional.
