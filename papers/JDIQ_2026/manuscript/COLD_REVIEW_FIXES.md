# Cold-Review Fixes — Category A and Sentence-Level

**Source report:** `PRE_SUBMISSION_REVIEW.md` (latest manuscript reviewer-simulation report)  
**Manuscript:** `main.tex`  
**Date:** 2026-07-13  
**Scope:** Targeted pre-submission rewrite. Verified numerical results, redesigned figure data, statistical conclusions, and central thesis preserved.

---

## Category A issues

### A1. Resolve “original study” / “original title” / manuscript-history framing

| Field | Detail |
|---|---|
| **Status** | Fixed |
| **Type** | Writing-only |
| **Evidence** | Cold-reader stop on uncited “original study/title/earlier version”; AC consensus as highest risk |
| **Files** | `main.tex` (Abstract, Introduction, Background, Discussion, Limitations, Conclusion, Experimental Setup, Secondary Analyses, Data Availability); figure titles in `figures_v2/generate_figures.py` |

**Representative old → new**

| Location | Exact old wording (representative) | Exact new wording (representative) |
|---|---|---|
| Abstract | “...evaluation pipeline as the original study while replacing its unstable raw-margin weighting with a calibrated canonical protocol...” | “...using stored BM25, TF-IDF, and MiniLM candidate scores... Our primary analysis uses a normalized retention-matched protocol... As a raw-score ablation, we also evaluate the unnormalized construction...” |
| Conclusion | “This paper revisited a narrower question than the manuscript's original title implied...” | “This study examines not only whether preference-graph repair affects retrieval, but also whether that conclusion is stable under defensible choices for normalizing and aggregating heterogeneous ranking scores.” |
| Discussion opening | “...more specific conclusion than the manuscript's earlier raw-margin version...” / `primary_minmax_retention_matched` | “...more specific than a naive ‘repair either helps or it does not’ framing...” / “primary normalized retention-matched protocol” |
| Limitations opening | “The revised study has a clearer limitations profile than the earlier raw-margin version...” | “This study's limitations fall into several categories, detailed below.” |
| Failure taxonomy | “An earlier draft... The blocking audit showed...” | “A separate raw-margin failure-mining corpus... That taxonomy is not manually verified...” |

**Classification used for phrase audit**

1. Scientifically necessary protocol language (kept/adapted): raw-margin ablation, retention matching to the unnormalized construction, fixed raw-margin thresholds  
2. Artifact/reproducibility metadata (kept, de-internalized): seeds, solver version, manifests  
3. Unnecessary manuscript-history language (removed/rewritten): original study/title/narrative, revised study/paper, earlier draft, blocking audit, internal package IDs

---

### A2. Provide anonymized repository/artifact mirror

| Field | Detail |
|---|---|
| **Status** | **Unresolved submission task** (no fabricated URL) |
| **Type** | Process / artifact (not inventable from repo) |
| **Evidence** | Repo-wide search found **no** anonymous.4open.science / Zenodo anonymous / Figshare / OSF anonymous URL. Public GitHub URL is author-identifying (`README.md`). ACM expects anonymity-preserving artifact access for double-anonymous review. |
| **Files** | `main.tex` §Data Availability rewritten to state absence honestly and refuse “email the authors” / placeholder links |

**Current manuscript stance:** no author-identifying GitHub URL; no placeholder URL; notes that a verified anonymized mirror was not available at writing time and should be supplied via the venue submission system.

**Author instructions to create one (do before submission):**

1. Create a review-only snapshot without identifying content. Scrub or anonymize: Git history; remotes; commit authors; README / docs identity; package metadata (`pyproject.toml`, egg-info); PDF metadata; absolute local paths; author names; repository badges; user-specific URLs; private dissertation filenames. Prefer a fresh orphan export over shipping identifying `.git` history.  
2. Host on an anonymity-preserving mirror such as `https://anonymous.4open.science` (preferred for ACM-style double-blind), configured so access logs do not expose reviewer identity to authors.  
3. Verify the anonymous URL does **not** redirect to `github.com/SoroushVahidi/...` and does not reveal identity in HTML title, clone URL, or embedded docs.  
4. Insert only that verified URL into §Data Availability; do not email-on-request and do not invent a URL here.

**Final commit note (2026-07-13):** Still unresolved. Manuscript correctly claims no verified anonymized URL.

---

### A3. Fix min-max / TF-IDF dash inconsistencies

| Field | Detail |
|---|---|
| **Status** | Fixed |
| **Type** | Writing-only |
| **Evidence** | Reviewers flagged Abstract/Intro `min-max` vs body `min--max`; one `TF--IDF` vs elsewhere `TF-IDF` |
| **Decision** | Body/abstract use LaTeX `min--max` (renders as en dash); `TF-IDF` with hyphen throughout |
| **Files** | `main.tex` |

---

## Nine sentence-level cold-read findings

| # | Quoted sentence (or location) | Still present? | Why it caused hesitation | Rewrite summary | Type |
|---|---|---|---|---|---|
| 1 | “...evaluation pipeline as the original study...” (Abstract) | No | Unidentified prior study | Reframed as primary normalized protocol + raw-score ablation | Writing |
| 2 | “...narrower question than the manuscript's original title...” (Conclusion) | No | References a title the reader never saw | States research question directly | Writing |
| 3 | “...manuscript's earlier raw-margin version...” (Discussion) | No | Manuscript-history framing | Naive help/no-help framing; primary normalized protocol | Writing |
| 4 | “The revised study has a clearer limitations profile than the earlier raw-margin version...” | No | Implies a prior paper the reader must know | “This study's limitations fall into several categories...” | Writing |
| 5 | “...approximately 0.988... approximately 0.512...” (Abstract / §5.1) | No | Approx + three-decimal precision clash | Exact means `$0.988$` / `$0.512$` | Writing |
| 6 | “...approximately $0.3495$... $0.1100$...” (§5.3) | No | Same approx/precision clash | Dropped “approximately” | Writing |
| 7 | “...BM25, TF--IDF, and MiniLM...” (§5.1) | No | En dash broke TF-IDF consistency | `TF-IDF` | Writing |
| 8 | Abstract/Intro `min-max` vs body `min--max` | Normalized | Dash inconsistency | Uniform `min--max` in TeX | Writing |
| 9 | “...rather than a theorem that balance-based repair can never matter.” | No | Awkward “theorem that never” | “...not a general impossibility result for balance-based repair.” | Writing |
| 10* | “...The threshold-scale audit further shows...” (§5.1) | No | Dangling internal audit name | “A supporting analysis of the fixed raw thresholds further shows...” | Writing |

\*Listed as the tenth cold-read sentence in the report’s pause-and-doubt pass; treated with the same priority.

---

## Additional high-leverage fixes performed in the same pass

These were requested in the revision brief (items 5–9) and/or Category B of the same report; none changed verified primary nDCG conclusions.

| Issue | Fix | Evidence | Type |
|---|---|---|---|
| NP-hardness of FAS | Cited Karp (1972) | Authoritative reducibility volume | Writing + bib |
| Kemeny | Cited Kemeny (1959) + linked to FAS/Kemeny | Primary source | Writing + bib |
| Bradley–Terry | Positioned vs Rank Centrality and graph repair | Bradley & Terry (1952) | Writing + bib |
| Greedy vs classical heuristics | Related to Eades–Lin–Smyth; not claimed identical | Eades et al. (1993) | Writing + bib |
| Seeds | Bootstrap seed 13; permutation seed 17; 10,000 reps each; Monte Carlo not exact | `run_full_calibrated_core.py`, `full_calibration_utils.py` | Writing |
| Solver | PySCIPOpt 6.2.1 / SCIP; proven-optimal only; gap 0 | `exact_open_source_ilp_repair_investigation` | Writing |
| HotpotQA 70→52 | All-zero/nonpositive qrels; before normalization; same set for all methods; qrels-only | eligibility filter + exclusion audit | Writing |
| Secondary metrics | MAP/MRR explored from stored rankings; Holm = 0; not added as new table | `reports/additional_metrics_investigation/` | Analysis already available + writing |
| Modern reranker | Not added; baseline-role explanation strengthened | Incomparable without new inference | Writing |
| Dead notation $u \succ v$ | Removed from notation table | Unused in body | Writing |
| Markov damping | Teleportation 0.15 → ergodicity clarified | PageRank-style damping | Writing |

---

## What was **not** changed

- Primary nDCG point estimates, CIs, Holm/BH conclusions  
- Figure data underlying redesigned figures (titles/labels only)  
- Detector / experiment code / stored ranking files  
- Retention-matching honesty and Limitations candor  
- Exact-ILP robustness conclusion
