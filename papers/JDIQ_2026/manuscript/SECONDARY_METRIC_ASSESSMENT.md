# Secondary Metric Assessment

**Date:** 2026-07-13  
**Source computation:** `reports/additional_metrics_investigation/` (recomputed from stored candidate scores / rankings / qrels; no new upstream retrieval)  
**Primary metric (unchanged):** nDCG@$k$

---

## Metrics considered

| Metric | Computable from stored artifacts? | Appropriate for this study? | Decision |
|---|---|---|---|
| **nDCG@$k$** (primary) | Yes (already primary) | Yes — graded relevance; matches main family | Keep primary |
| **MRR** | Yes — recomputed from stored scores/rankings without regenerating BM25/TF-IDF/MiniLM | Yes as secondary binary-relevance check | Mentioned in manuscript as secondary robustness; **not** added as a new main-text table |
| **MAP** | Yes — same as MRR | Yes as secondary binary-relevance check | Same as MRR |
| **Recall@$k$** | Yes | **Weak for confirmatory use** — candidates are already pool-truncated, so Recall can mislead about retrieval completeness | **Not** used as confirmatory metric; omission stated in Limitations |
| Precision@$k$ / Success@$k$ | Yes | Informative diagnostically, but mostly volume with little independent punch beyond MAP/MRR | Not added to manuscript |

**Note on ranking storage:** Calibrated `query_records.jsonl` drops full ranking lists but retains metric scalars for some measures; the additional-metrics pipeline rebuilds rankings from stored score files + qrels. No paid API calls and no new retrieval runs were required.

---

## Did conclusions change?

**No — not in the primary Holm sense.**

| Protocol slice | Holm-surviving repaired-vs-unrepaired cells | Interpretation |
|---|---|---|
| Primary nDCG family (manuscript) | 0 | Unchanged central claim |
| Additional suite including MAP/MRR | 0 Holm survivors among confirmatory MAP/MRR/nDCG cells | Does not overturn null robustness claim |
| BH (exploratory) | Small mixed-sign subset: SciDocs `ms1` MAP/MRR positive; BRIGHT `ms1` some negative | Confirms construction/method sensitivity details; **not** a broad robust positive repair result |

Classification from the investigation executive report: **“B. Metric-sensitive details, main conclusion robust.”**

---

## Multiplicity policy

- Primary inferential family remains **nDCG repaired-versus-unrepaired** under the primary normalized protocol (Holm + BH as before).  
- MAP/MRR are explicitly labeled **secondary / exploratory** and are **not** folded into that primary Holm family.  
- Expanding the primary family to include all MAP/MRR cells would inflate multiplicity without changing Holm survivors (still 0), while risking BH noise being over-interpreted.

---

## What was added to the manuscript

- Short prose in §Statistical Analysis describing the MAP/MRR secondary check and Holm=0 outcome.  
- Limitations sentence clarifying MAP/MRR are secondary and Recall@$k$ is not confirmatory under pool truncation.  
- **No new figure.**  
- **No new results table** (volume vs. value: prose robustness note is enough given unchanged Holm conclusion).

---

## Modern reranking baseline (related reviewer ask)

Not added. Stored candidate scores do not provide a fair cross-encoder/LLM rerank comparison without new inference, supervised splits, and a different experimental budget. Baseline-role text now states that Prior/RRF/CombSUM/Borda are graph-independent controls for the **repair-sensitivity** question, not SOTA retrieval claims.
