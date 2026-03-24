# Revision Strategy — LLM Baseline Gap

> **Updated:** 2026-03-24
> **Context:** The editor flagged (1) missing LLM baselines, (2) insufficient
> modern baselines, (3) weak positioning. This tracks resolution status.

---

## 1. LLM Baseline Gap — Current State

| Component | Status |
|-----------|--------|
| LLM pairwise pipeline code | **done** — `src/rerankers/llm_pairwise.py` (OpenAI + Gemini) |
| Dry-run validation | **done** — 50 queries, 9,500 pairs |
| Real OpenAI run — SciDocs | **done** — 20 queries, 2,100 pairs, gpt-4o-mini |
| Real OpenAI run — HotpotQA | **done** — 10 queries, 450 pairs, gpt-4o-mini |
| Real Gemini run — SciDocs | **partial** — 2 queries, 380 pairs (free-tier quota) |
| Repaired-vs-unrepaired under real LLM | **done** — negative ΔnDCG on both datasets |
| Bootstrap CIs from real LLM data | **not done** |
| Full-scale LLM evaluation (≥50 queries) | **not done** |

---

## 2. Key Real LLM Findings

| Dataset | Queries | ΔnDCG (rep − unrep, Copeland) | Cyclic % | Best method |
|---------|---------|-------------------------------|----------|-------------|
| SciDocs | 20 | −0.0003 | 95% | markov (0.9574) |
| HotpotQA | 10 | −0.0070 | 90% | tournament_sort (0.9008) |

FAS repair direction under real LLM preferences is **consistently negative**
across both datasets and both hybrid components (copeland, balance).

---

## 3. Editor's Concern Resolution

**Status: SUBSTANTIALLY ADDRESSED.**

The editor flagged that the manuscript lacked LLM-based baselines. We now have:

- Real gpt-4o-mini pairwise judgments on two datasets (SciDocs, HotpotQA).
- 12 aggregation methods evaluated on the same real LLM judgments.
- Consistent finding: repair does not improve nDCG under LLM preferences.
- Cross-provider signal from Gemini (directional only, n=2).

**What remains:**
- Bootstrap CIs on the real LLM data (computable from existing per-query CSVs).
- Larger query budgets for stronger statistical claims.
- Position debiasing analysis.

---

## 4. Recommended Manuscript Language

> "To assess whether our findings transfer to LLM-generated preferences, we
> conducted bounded pilot studies using gpt-4o-mini as a pairwise relevance
> judge on SciDocs (20 queries, top-15) and HotpotQA (10 queries, top-15).
> Real LLM judgments produced highly cyclic preference graphs (90–95% of
> queries). FAS repair showed ΔnDCG of −0.0003 (SciDocs) and −0.0070
> (HotpotQA) relative to unrepaired aggregation, consistent with the
> regime-dependence pattern observed with score-derived preferences. A
> supplementary pilot using Google Gemini on 2 SciDocs queries showed
> directionally consistent results (ΔnDCG = −0.0045)."

---

## 5. What Must NOT Be Said

- Do not claim these are full-benchmark reproductions (20 and 10 queries).
- Do not report bootstrap CIs that have not been computed.
- Do not claim Gemini and OpenAI results are directly comparable.
- Do not claim the editor's concern is "fully resolved" without larger runs.
