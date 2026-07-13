# PROMPT_MODE_SCOPE_AUDIT

## Pairwise

- Quantitative outputs: yes.
- Manuscript role: yes, primary real-LLM evidence for OpenAI on SciDocs, HotpotQA, and FiQA.
- Main-paper suitability: yes, but only with conservative scope wording and without unsupported Cohere/Azure claims.

## Pointwise

- Quantitative outputs: yes, committed OpenAI runs exist for SciDocs and HotpotQA, with bootstrap summaries.
- Manuscript role: auxiliary scope check only.
- Main-paper suitability: supplementary or brief scope-check mention only; they do not directly address the repaired-vs-unrepaired pairwise-graph question.

## Listwise

- Quantitative outputs: yes, committed OpenAI runs exist for SciDocs and HotpotQA, with bootstrap summaries and raw ranking strings.
- Manuscript role: auxiliary scope check only.
- Main-paper suitability: supplementary or brief scope-check mention only.

## Stale supporting artifact

The file `outputs/manuscript_artifacts/tables/table_4_llm_paradigm_comparison.csv` is stale for pointwise/listwise scope. It labels SciDocs pointwise and listwise evidence as `mock`, even though committed real OpenAI runs now exist for both paradigms.
