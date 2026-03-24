# Related Work Positioning Note — LLM Baselines

> **Updated:** 2026-03-24
> **Purpose:** How to position this work relative to LLM-based reranking
> literature, given the current evidence.

---

## 1. What We Have Run (real results)

| Category | Implementation | Real results |
|----------|---------------|-------------|
| Cross-encoder reranker (MS MARCO MiniLM) | Full, local inference | **Yes** — 3 datasets |
| Bradley-Terry MLE | Full | **Yes** — qrels-derived + real LLM |
| Win-rate ranking | Full | **Yes** — same |
| Markov chain (PageRank) | Full | **Yes** — same |
| Tournament sort | Full | **Yes** — same |
| LLM pairwise (PRP-style, OpenAI) | Full, multi-provider | **Yes** — SciDocs 20q, HotpotQA 10q |
| LLM pairwise (Gemini) | Full | **Partial** — 2 SciDocs queries |

---

## 2. What We Cite vs What We Reproduce

**Methods we cite and implement:**

- **PRP** (Qin et al., 2023) — our `llm_pairwise` module implements the core
  pairwise comparison approach with Copeland/BT/win-rate aggregation.
- **Bradley-Terry** (Bradley & Terry, 1952) — standard MLE.
- **Markov chain ranking** (Dwork et al., 2001) — PageRank-style.

**Methods we cite but do NOT implement:**

- **RankGPT** (Sun et al., 2023) — listwise sliding-window.
- **BLITZRANK** (Agrawal et al., 2026) — tournament-graph zero-shot.
- **AFR-Rank** (2025) — no code available.

---

## 3. Safe Positioning Language

> "We implement PRP-style (Qin et al., 2023) pairwise comparison using LLM
> judges and evaluate multiple aggregation strategies on the resulting
> preference graphs. Bounded pilot studies on SciDocs (20 queries) and
> HotpotQA (10 queries) using gpt-4o-mini confirm that LLM pairwise
> preferences produce highly cyclic graphs (90–95%) where FAS repair is
> active but does not improve nDCG."

---

## 4. What NOT to Claim

- Do not claim to outperform RankGPT, BLITZRANK, or any named system.
- Do not position this work as an LLM reranking paper — it is a graph-repair
  diagnostic study that includes LLM-sourced preferences as one input.
- Do not claim cross-encoder results are comparable to graph methods.

---

## 5. Honest Gap Statement

> "Recent work on LLM-based reranking (Sun et al., 2023; Qin et al., 2023;
> Agrawal et al., 2026) demonstrates strong zero-shot ranking performance.
> Our study is complementary: we investigate how pairwise preferences should
> be aggregated, and whether graph-theoretic cycle repair improves the
> resulting rankings. Bounded pilot studies with gpt-4o-mini on two datasets
> confirm that our qrels-derived findings transfer to LLM-generated
> preferences. A supplementary pilot with Google Gemini provides additional
> cross-provider directional evidence."
