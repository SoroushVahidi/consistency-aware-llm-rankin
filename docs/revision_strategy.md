# Revision Strategy — LLM Baseline Gap

> **SUPERSEDED (as of 2026-07-28).** Predates `papers/JDIQ_2026/`, whose
> manuscript (`papers/JDIQ_2026/manuscript/main.tex`) reflects whatever
> revision strategy was actually adopted. Treat this file as a historical
> planning record, not current guidance.

> **Updated:** 2026-04-06
> **Context:** The editor flagged (1) missing LLM baselines, (2) insufficient
> modern baselines, (3) weak positioning. This tracks resolution status.

---

## 1. LLM Baseline Gap — Current State

| Component | Status |
|-----------|--------|
| LLM pairwise pipeline code | **done** — `src/rerankers/llm_pairwise.py` (OpenAI + Gemini) |
| Dry-run validation | **done** — 50 queries, 9,500 pairs |
| Real OpenAI run — SciDocs | **done** — 50 queries, 5,250 pairs, gpt-4o-mini |
| Real OpenAI run — HotpotQA | **done** — 20 queries, 900 pairs, gpt-4o-mini |
| Real Gemini run — SciDocs | **partial** — 2 queries, 380 pairs (free-tier quota) |
| Real OpenAI run — FiQA | **done (bounded)** — target 20, processed 10 queries, 46 pairs |
| Repaired-vs-unrepaired under real LLM | **done** — negative on SciDocs, near-zero on HotpotQA/FiQA |
| Bootstrap CIs from real LLM data | **done** — committed for SciDocs/HotpotQA/FiQA OpenAI runs |
| Full-scale LLM evaluation (≥50 queries) | **not done** |

---

## 2. Key Real LLM Findings

| Dataset | Queries | ΔnDCG (rep − unrep, Copeland) | Cyclic % | Best method |
|---------|---------|-------------------------------|----------|-------------|
| SciDocs | 50 | −0.0010 (CI below 0) | 92% | llm_pairwise_copeland (0.9749) |
| HotpotQA | 20 | +0.0000 (CI [0,0]) | 80% | tournament_sort (0.9271) |
| FiQA | 10 processed | +0.0000 (CI [0,0]) | 10% | llm_pairwise_copeland (1.0000) |

FAS repair direction under real LLM preferences is **consistently negative**
with a negative effect in SciDocs and near-null effects in HotpotQA/FiQA.

---

## 3. Editor's Concern Resolution

**Status: SUBSTANTIALLY ADDRESSED.**

The editor flagged that the manuscript lacked LLM-based baselines. We now have:

- Real gpt-4o-mini pairwise judgments on three datasets (SciDocs, HotpotQA, FiQA).
- 12 aggregation methods evaluated on the same real LLM judgments.
- Consistent finding: repair does not improve nDCG under LLM preferences.
- Cross-provider signal from Gemini (directional only, n=2).

**What remains:**
- Larger query budgets to tighten uncertainty, especially for FiQA.
- Larger query budgets for stronger statistical claims.
- Position debiasing analysis.

---

## 4. Recommended Manuscript Language

> "To assess whether our findings transfer to LLM-generated preferences, we
> conducted bounded pilot studies using gpt-4o-mini as a pairwise relevance
> judge on SciDocs (50 queries, top-15), HotpotQA (20 queries, top-15), and
> FiQA (bounded run: 10 processed queries from a 20-query target). Real LLM
> judgments showed regime-sensitive cyclicity (high on SciDocs/HotpotQA, low
> on FiQA in this run). Repaired-vs-unrepaired ΔnDCG was slightly negative on
> SciDocs and near-zero on HotpotQA/FiQA, consistent with a conservative
> structural-vs-relevance decoupling interpretation. A
> supplementary pilot using Google Gemini on 2 SciDocs queries showed
> directionally consistent results (ΔnDCG = −0.0045)."

---

## 5. What Must NOT Be Said

- Do not claim these are full-benchmark reproductions (bounded runs).
- Do not over-interpret zero-width CIs from bounded runs as universal null effects.
- Do not claim Gemini and OpenAI results are directly comparable.
- Do not claim the editor's concern is "fully resolved" without larger runs.
