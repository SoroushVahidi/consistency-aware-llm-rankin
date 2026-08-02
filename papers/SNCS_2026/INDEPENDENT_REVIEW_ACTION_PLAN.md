# Independent Review Action Plan

## Must Fix Before Submission

| Location | Proposed change | Evidence/source | Expected benefit | Scientific content change? | Risk |
|---|---|---|---|---|---|
| Title-page keywords, `main.tex` lines 77-78 | Reduce keywords from 8 to 6. | SN Computer Science official submission guidelines specify 4-6 keywords. | Journal-format compliance. | No. | Low. |
| Related Work Section 2.2 | Add PRP-Graph citation/discussion. | ACL Anthology page and DOI `10.18653/v1/2024.acl-long.313`. | Prevents a current-literature gap in graph-based LLM pairwise reranking. | No new result; background only. | Low. |
| Related Work Section 2.3 | Add exact MWFAS and linear-ordering references. | DOI `10.1145/3446429`; DOI `10.1287/opre.32.6.1195`. | Clarifies that exact repair is a diagnostic use of known optimization machinery. | No. | Low. |
| Table 6 layout | Widen interpretation column. | Visual PDF inspection showed the table was unnecessarily narrow and wrappy. | Improves readability without changing values. | No. | Low. |
| Evidence documentation | Update stale MDE value from 0.0207 to 0.0201 where current canonical SNCS evidence uses 0.0201. | `result_claims.yaml`, manuscript Table 6, and current result text use 0.0201. | Removes cross-document inconsistency. | No canonical result change. | Low. |

All must-fix items above were applied in this pass.

## Strong Recommendations

| Location | Proposed change | Evidence/source | Expected benefit | Scientific content change? | Risk |
|---|---|---|---|---|---|
| Repository/archive package | Create a DOI-backed archival release before journal submission, after author approval. | Reproducibility and citation stability requirements. | Stable reviewer and publisher citation. | No. | Low, but requires explicit public-release authorization. |
| Methods/provider reporting | Keep Gemini wording at provider level unless transport evidence is supplied. | Tracked run metadata records provider/model, but not Gemini Developer API versus Vertex AI transport. | Avoids unverifiable infrastructure claims. | No. | Low. |
| Introduction scope paragraph | If word pressure appears, shorten the non-claims list without changing substance. | `main.tex` lines 170-181 are slightly defensive. | Smoother journal tone. | No. | Medium if shortening removes useful guardrails. |
| Figure 3 | Consider regenerating with slightly larger tick labels. | Visual inspection only. | Minor readability gain. | No. | Low. |

## Optional Improvements

| Location | Proposed change | Evidence/source | Expected benefit | Scientific content change? | Risk |
|---|---|---|---|---|---|
| Discussion/Future Work | Optionally mention TourRank as related future LLM-ranking context. | WWW 2025 DOI `10.1145/3696410.3714863`. | Broader current-literature awareness. | No new result. | Low. |
| Table 5 caption | Shorten if the final PDF becomes too dense after copyediting. | Presentation review. | Editorial smoothness. | No. | Low. |
| Figure 5 note | Move part of the note to caption if the publisher requests cleaner figures. | Presentation review. | Cleaner visual. | No. | Low. |

## Not Appropriate for This Paper

| Suggestion considered | Reason rejected | Evidence/source | Expected benefit if done | Scientific content change? | Risk |
|---|---|---|---|---|---|
| Add full-scale LLM pairwise ranking experiments | Would require new provider calls and a new confirmatory study. | Current paper deliberately bounds the six-query pilot. | Broader LLM generality. | Yes. | High. |
| Add neural retrieval leaderboard baselines | The paper does not claim state-of-the-art retrieval effectiveness. | Manuscript scope statement, `main.tex` lines 170-181. | Leaderboard context. | Yes. | High scope creep. |
| Develop learned repair-selection policy | New research direction beyond repair audit. | Current evidence does not train or validate such a selector. | Practical deployment guidance. | Yes. | High. |
| Run new exact-solver scaling experiments | User explicitly prohibited new experiments; internal solver-scaling reports are not manuscript evidence. | `docs/CONTRIBUTIONS.md` artifact policy. | Optimization-method context. | Yes. | High. |
