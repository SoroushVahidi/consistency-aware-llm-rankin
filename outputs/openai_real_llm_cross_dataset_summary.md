# Real OpenAI Pairwise Cross-Dataset Summary (Manuscript-Facing)

This table consolidates the currently completed **real OpenAI pairwise** runs used for manuscript-facing evidence: SciDocs (50q), HotpotQA (20q), and FiQA (new run; target 20q, 10 usable/processed).

| Dataset | Run dir | Queries done | Cyclic-query rate | Best method | Best nDCG@15 | Best MAP@15 | Repaired−Unrepaired ΔnDCG (copeland) | 95% CI |
|---|---|---:|---|---|---:|---:|---:|---|
| SciDocs 50q | `outputs/openai_scidocs_real_pairwise_q50_k15` | 50 | 46/50 (92.0%) | `llm_pairwise_copeland` | 0.9749 | 0.9452 | -0.0010 | [-0.001905, -0.000208] |
| HotpotQA 20q | `outputs/openai_hotpotqa_real_run_q20_k15` | 20 | 16/20 (80.0%) | `tournament_sort_from_llm` | 0.9271 | 0.8958 | +0.0000 | [0.0, 0.0] |
| FiQA (new) | `outputs/openai_fiqa_real_run_q20_k15` | 10 | 1/10 (10.0%) | `llm_pairwise_copeland` | 1.0000 | 1.0000 | +0.0000 | [0.0, 0.0] |

## Conservative interpretation for manuscript text

Across three real-LLM datasets, cyclicity is clearly **regime-sensitive**: SciDocs and HotpotQA form a high-cyclicity regime (92% and 80% cyclic queries), while FiQA is lower-cyclicity in this run (10%). In the high-cyclicity setting (SciDocs), repaired-vs-unrepaired copeland hybrid shows a small negative ΔnDCG with CI below zero; in HotpotQA and FiQA, ΔnDCG is effectively null. This supports a conservative structural-vs-relevance decoupling interpretation: cycle repair can improve graph structure without implying uniform retrieval gains.

## Limits / non-claims

- These are bounded real-LLM runs, not full benchmark reproductions.
- FiQA processed 10 usable queries (from a 20-query target), so low-cyclicity evidence there is suggestive rather than definitive.
- Cross-dataset differences should be interpreted as empirical regime observations, not universal causal claims about repair.
