# Revision Summary — Final Pre-Commit Pass

**Date:** 2026-07-13  
**Branch target:** `main`  
**Primary files:** `main.tex`, `main.pdf`, `references.bib`, `figures_v2/`, `COLD_REVIEW_FIXES.md`, `SECONDARY_METRIC_ASSESSMENT.md`, this file

Verified experimental nDCG values were not altered. No fabricated URLs, metrics, or experiments.

---

## Manuscript-history framing

Previously resolved and re-verified: no PDF hits for “original study/title,” “blocking audit,” `primary_minmax_retention_matched`, or “canonical package.” Reader-facing prose uses primary normalized / raw-margin ablation language.

---

## Literature added in this final pass

Verified via Crossref (DOI → metadata):

| Key | Citation | Use |
|---|---|---|
| `manmatha2002formal` | Manmatha & Sever, HLT 2002, DOI `10.3115/1289189.1289265`, pages `98` (Crossref) | Heterogeneous retrieval scores require explicit normalization before aggregation |
| `lee1997analyses` | Lee, SIGIR 1997, pp. 267–276, DOI `10.1145/258525.258587` | Multiple-evidence fusion / score–rank combination behavior (ACM title verified; not the longer informal title variant) |
| `urbano2019statistical` | Urbano, Lima & Hanjalic, SIGIR 2019, pp. 505–514, DOI `10.1145/3331184.3331259` | Paired significance vs uncertainty vs Type I/II/III considerations |

**Not added:** Ma et al. listwise LLM reranking — only a CoRR/arXiv record was verified (`arXiv:2305.02156`); no peer-reviewed final venue/pages confirmed, and the LLM paragraph does not require a listwise contrast.

**Earlier pass retain:** Karp 1972; Kemeny 1959; Bradley–Terry 1952; Eades–Lin–Smyth 1993.

---

## CombMNZ decision

**Not added as an experimental baseline.**

Reasons (documented rather than implemented):

- Historical CombMNZ = CombSUM × (#nonzero contributing systems), after per-system normalization (Fox & Shaw; Lee).
- Stored scores make a CombMNZ variant computable without re-retrieval, but several implementation choices remain under-specified relative to this pipeline (what counts as nonzero after min–max; missing-document coding already implicit in CombSUM; tie-break interaction with Prior/RRF).
- Expanding the baseline table/figure would broaden the paper into a fusion bake-off without changing the repair-sensitivity thesis.
- Manuscript now states CombSUM is retained and CombMNZ is deliberately out of the primary baseline family, with Lee cited for fusion analysis.

---

## Exact ILP formulation

Added a compact linear-ordering MIP (antisymmetry, triple transitivity, reversed-edge objective), plus solver identity/version, proven-optimal gap=$0$ policy, unused 300s safety limit, 1{,}025/1{,}025 solves, and the cyclic-query definitions of the 87.9% / 26.3% structural gaps. Source: `reports/exact_open_source_ilp_repair_investigation/`.

---

## Page length

| State | Pages |
|---|---|
| After cold-review pass | 29 |
| After this editorial + ILP/citation pass | **28** |

Causes of the earlier 27→29 inflation: literature, reproducibility/seeds, HotpotQA eligibility prose, secondary-metric note, figure title renames — not new experimental tables.

This pass recovered one page by tightening CARB, Data Availability, and duplicated artifact-limitation text while adding the ILP block and three IR citations.

**JDIQ page limit:** Live ACM author-guidelines page was behind a Cloudflare challenge in this environment. Local project summary (`JDIQ_GUIDELINE_SUMMARY.md`) cites typical research-paper expectations of roughly 20–25 pages in **final ACM journal format**; the current file uses the single-column `manuscript` review option, which naturally runs longer. **No verified hard JDIQ page/word ceiling was confirmable from an authoritative live ACM page in this session.** 28 manuscript pages is retained as necessary for disclosure + methods.

---

## Secondary metrics

Re-verified against `SECONDARY_METRIC_ASSESSMENT.md` / `reports/additional_metrics_investigation/`:

- MAP/MRR exploratory only; not in primary Holm family.
- Holm survivors remain 0; conclusion unchanged.
- No new metric table added (prose remains sufficient).

---

## Anonymous artifact (unresolved submission task)

Still **no** verified anonymized URL. Manuscript does **not** claim one exists and does **not** include the public author GitHub URL.

**Before venue submission, authors must create and test a scrubbed anonymous mirror that removes/anonymizes:**

- Git history and remotes  
- commit authors  
- README / docs identity  
- package metadata (`pyproject.toml`, egg-info)  
- PDF metadata  
- absolute local paths  
- author names  
- repository badges  
- user-specific URLs  

Preferred pattern: `anonymous.4open.science` (or equivalent anonymity-preserving host). Attach via the submission system, not email-on-request.

---

## Compilation

```bash
cd papers/JDIQ_2026/manuscript
tectonic -X compile main.tex --keep-logs
```

| Check | Result |
|---|---|
| Compile | Success |
| Pages | **28** |
| Undefined refs/cites | 0 |
| Literal `??` | 0 |
| Manuscript path | `papers/JDIQ_2026/manuscript/main.tex` |
| PDF path | `papers/JDIQ_2026/manuscript/main.pdf` |

---

## Remaining reviewer risks

1. Anonymous artifact still must be created before submission.  
2. No modern cross-encoder/LLM reranker baseline (scoped out).  
3. HotpotQA $n{=}52$ remains thin.  
4. CombMNZ / broader fusion ablations out of scope.  
5. Retention-target sensitivity integrated (structure changes; Holm survivors still 0).


---

## Overnight integration (auto)

- Retention-sensitivity Limitations claim corrected using `reports/retention_matching_investigation/`.
- CombMNZ exploratory: DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous definition; expanding baselines would add vo
- Local anonymous artifact package prepared under `/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-20260713-225928/artifact_prep/` (hosted anonymous URL still unresolved).
- Validation pages=28; fail=[]
