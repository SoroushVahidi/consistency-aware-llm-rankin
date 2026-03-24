# LLM Real Pilot Results — Authoritative Summary

> **Updated:** 2026-03-24
> **Scope:** Complete inventory and honest assessment of all LLM pairwise
> baseline experiments conducted in this repository.

---

## 1. Exact Pilot Inventory

### Pilot A: Dry-Run Validation (mock)

| Field | Value |
|-------|-------|
| Directory | `outputs/llm_scidocs_pilot_comparison/` |
| Provider | None (deterministic MD5 mock) |
| Dataset | SciDocs |
| Queries | 50, top_k=20 |
| Pairs | 9,500 |
| Manuscript use | **Infrastructure validation only** |

### Pilot B: OpenAI Real — SciDocs (complete)

| Field | Value |
|-------|-------|
| Directory | `outputs/openai_scidocs_real_run_q20_k15/` |
| Provider | OpenAI (gpt-4o-mini) |
| Dataset | SciDocs |
| Queries | **20/20** complete, top_k=15 |
| Pairs | 2,100 |
| API calls | 2,100 (0 errors) |
| Tokens | 971,078 |
| Cost | $0.15 |
| Wall time | 20 min |
| Best nDCG@15 | 0.9574 (Markov) |
| Cyclic queries | 19/20 (95%) |
| Avg FAS edges | 7.2 |
| ΔnDCG (rep − unrep) | −0.0003 (Copeland), −0.0003 (balance) |

### Pilot C: OpenAI Real — HotpotQA (complete)

| Field | Value |
|-------|-------|
| Directory | `outputs/openai_hotpotqa_real_run_q10_k15/` |
| Provider | OpenAI (gpt-4o-mini) |
| Dataset | HotpotQA |
| Queries | **10/10** complete, top_k=15 |
| Pairs | 450 |
| API calls | 450 (0 errors) |
| Tokens | 161,205 |
| Cost | $0.02 |
| Wall time | 4.7 min |
| Best nDCG@15 | 0.9008 (tournament sort) |
| Cyclic queries | 9/10 (90%) |
| Avg FAS edges | 4.3 |
| ΔnDCG (rep − unrep) | −0.0070 (Copeland), −0.0070 (balance) |

### Pilot D: Gemini Real — SciDocs (quota-limited)

| Field | Value |
|-------|-------|
| Directory | `outputs/gemini_scidocs_real_pilot/` |
| Provider | Google Gemini (gemini-3.1-flash-lite-preview) |
| Dataset | SciDocs |
| Queries | 2/5, top_k=20 |
| Pairs | 380 |
| Best nDCG@20 | 0.9855 (Copeland) |
| Cyclic queries | 2/2 (100%) |
| ΔnDCG (rep − unrep) | −0.0045 |
| Blocker | Free-tier daily quota (500 RPD) |

### Pilot E: OpenAI Blocked (legacy)

| Field | Value |
|-------|-------|
| Directory | `outputs/llm_scidocs_real_pilot/` |
| Status | **Blocked** — `insufficient_quota` on first call |
| Queries | 0/30 |
| Manuscript use | None |

---

## 2. Strongest Safe Conclusions

1. **Real LLM judgments produce highly cyclic preference graphs.**
   95% cyclic on SciDocs (n=20), 90% on HotpotQA (n=10). This confirms
   that the cycle-repair motivation extends to LLM-sourced preferences.

2. **FAS repair does not improve nDCG under real LLM preferences.**
   ΔnDCG is negative on both datasets: −0.0003 (SciDocs) and −0.0070
   (HotpotQA). This is consistent with the qrels-derived ms1 Copeland
   finding.

3. **Simple aggregation methods (Copeland, win-rate, Markov) match or
   exceed FAS-repair methods** on both datasets under real LLM preferences.

4. **The direction is consistent across two providers.** The Gemini pilot
   (n=2, ΔnDCG = −0.0045) is directionally consistent, though too small
   for independent claims.

5. **The pipeline is ready for scale-up.** Runs are fully resumable via
   disk cache. Scaling to 50+ queries requires only API budget.

---

## 3. What Must NOT Be Claimed

1. **Do not claim** formal statistical significance — no bootstrap CIs computed.
2. **Do not claim** these are full-scale benchmark reproductions (20q, 10q).
3. **Do not claim** Gemini and OpenAI produce comparable judgments.
4. **Do not claim** the editor's concern is fully resolved without larger runs.
5. **Do not cite** dry-run nDCG values as LLM performance evidence.

---

## 4. How These Pilots Change the Editorial-Gap Assessment

**Before:** US-4 ("Results generalise to LLM-generated preferences") was
completely unsupported. L1 ("LLM baselines not run") was an open gap.

**After:** US-4 is now **supported by bounded pilots** — real LLM data on
two datasets shows the same direction as qrels-derived evidence. L1 is
**substantially mitigated** — real results exist on two datasets.

**Editor's concern: substantially addressed.** The infrastructure gap is
closed. The empirical gap is narrowed to a question of scale and formal
significance, not direction.

---

## 5. The Single Most Important Remaining Limitation

**Bounded sample sizes.** The runs cover 20 (SciDocs) and 10 (HotpotQA)
queries. Bootstrap CIs are not computed. Scaling to ≥50 queries per dataset
and computing formal CIs would upgrade the evidence from "bounded pilot"
to "real completed run" in the four-tier system.

---

## 6. Files Reference

| File | Description |
|------|-------------|
| `outputs/openai_scidocs_real_run_q20_k15/` | Full SciDocs OpenAI run |
| `outputs/openai_hotpotqa_real_run_q10_k15/` | Full HotpotQA OpenAI run |
| `outputs/gemini_scidocs_real_pilot/` | Partial Gemini SciDocs run |
| `outputs/llm_scidocs_pilot_comparison/` | Dry-run validation |
| `scripts/run_openai_real_pilot.py` | Parameterized OpenAI pilot runner |
| `scripts/run_gemini_scidocs_pilot.py` | Gemini pilot runner |
| `src/rerankers/llm_pairwise.py` | Core LLM pairwise module |
