# Related Work Positioning Note — LLM Baselines

> **HISTORICAL (flagged 2026-07-31).** Written 2026-04-06, before the
> finalized `papers/JDIQ_2026/manuscript/main.tex`'s own related-work section
> (which cites Dwork/Kemeny, ACN/tournaments, RRF/CombSUM/Borda, and
> data-quality/data-cascades literature more broadly than this note). Not
> contradicted, just superseded in scope/detail. Already referenced as
> "historical package era" by `README.md`'s own doc index, but previously
> missing this in-file banner. Use `main.tex`'s related-work section for
> current positioning.

---

## 1. What We Have Run (real results)

| Category | Implementation | Real results |
|----------|---------------|-------------|
| Cross-encoder reranker (MS MARCO MiniLM) | Full, local inference | **Yes** — 3 datasets |
| Bradley-Terry MLE | Full | **Yes** — qrels-derived + real LLM |
| Win-rate ranking | Full | **Yes** — same |
| Markov chain (PageRank) | Full | **Yes** — same |
| Tournament sort | Full | **Yes** — same |
| LLM pairwise (PRP-style, OpenAI) | Full, multi-provider | **Yes** — SciDocs 50q, HotpotQA 20q, FiQA 10 processed |
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
> preference graphs. Bounded real runs on SciDocs (50 queries), HotpotQA
> (20 queries), and FiQA (10 processed queries) using gpt-4o-mini show
> regime-sensitive cyclicity and small/non-uniform repaired-vs-unrepaired
> nDCG effects (negative on SciDocs, near-zero on HotpotQA/FiQA)."

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
> resulting rankings. Bounded real runs with gpt-4o-mini on three datasets suggest that our
> qrels-derived regime-sensitivity findings partially transfer to direct
> LLM-generated preferences, while still requiring caution on generalization. A supplementary pilot with Google Gemini provides additional
> cross-provider directional evidence."
