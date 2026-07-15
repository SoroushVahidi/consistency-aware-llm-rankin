# JDIQ Author Guideline Summary

> **PARTIALLY SUPERSEDED (as of 2026-07-14).** The venue-guideline content
> below remains generally applicable, but the submission checklist's
> "failure taxonomy with frequencies" item and its narrow baseline-list
> item ("CombSUM, RRF, prior") are stale: the finished manuscript excludes
> the failure taxonomy as evidence and reports a wider baseline set
> (adds PageRank, RankCentrality, Bradley-Terry, Markov-hybrid). Do not use
> those two checklist items to judge submission readiness; check against
> `manuscript/main.tex` directly instead.

**Prepared:** 2026-07-12  
**Target venue:** ACM Journal of Data and Information Quality (JDIQ)  
**Purpose:** Master reference for manuscript preparation in `papers/JDIQ_2026/`

All requirements below cite official ACM/JDIQ sources. Verify URLs before submission; guidelines may update.

---

## 1. Official sources

| Resource | URL |
|----------|-----|
| JDIQ on ACM Digital Library | https://dl.acm.org/journal/jdiq |
| JDIQ author guidelines (submission) | https://dl.acm.org/journal/jdiq/author-guidelines |
| JDIQ authors page (CODE-ISSS mirror) | https://codes-isss.org/jdiq_subdomain/authors/ |
| ACM Primary Article Template (LaTeX) | https://www.acm.org/publications/proceedings-template |
| ACM submission process | https://authors.acm.org/journals/submission-process |
| LaTeX preparation (`acmart`) | https://authors.acm.org/proceedings/production-information/preparing-your-article-with-latex |
| ACM reference format | https://www.acm.org/publications/authors/reference-format |

---

## 2. Aims and scope (mandatory alignment)

**Source:** ACM DL JDIQ scope; [JDIQ CFP (MIT mirror)](https://web.mit.edu/smadnick/www/JDIQ/ACM-JDIQ-CFP.htm); [CODE-ISSS authors page](https://codes-isss.org/jdiq_subdomain/authors/)

JDIQ publishes high-quality articles making a **significant and novel contribution** to **data and information quality**. Relevant areas include:

- Information quality in the **enterprise context**
- **Database-related technical solutions** for information quality
- Information quality in **computer science and information technology**
- **Information curation**

JDIQ accepts diverse methods: statistical analysis, mathematical modeling, quasi-experimental methods, case study, systems building, database theory, and qualitative approaches. Papers must:

1. Demonstrate use of a **rigorous method**
2. Provide **valuable and relevant implications for practice**

**Implication for our paper:** Frame preference-graph inconsistency as a **data quality dimension**, repair as a **DQ improvement technique**, and retrieval nDCG as **downstream information quality of ranked outputs**. CARB fits the **resource/dataset** contribution category.

---

## 3. Paper types and page expectations

**Sources:** JDIQ special-issue CFPs (e.g., [Synthetic Data Quality SI](https://groups.google.com/a/aixia.it/g/aixia/c/42M3a4peWDI)); [Big Data Veracity SI](https://databasetheory.org/node/66); CODE-ISSS authors page

| Type | Typical length | Our fit |
|------|----------------|---------|
| **Technical / Research paper** | Up to ~20–25 pages (ACM format); some SIs specify up to 23 pages | **Primary target** — empirical DQ study + benchmark |
| **Experience paper** | Up to ~10–12 pages | Partial fit (lessons from repair deployment) |
| **Resource / Dataset paper** | Up to ~10 pages | CARB supplementary; could be companion submission |
| **Survey paper** | Up to ~23 pages | Not applicable |
| **Challenge / Vision paper** | ~2 pages | Not applicable |

**Note:** JDIQ uses ACM **small trim** journal format (same `acmart` class as JACM, JEA). Page counts refer to formatted ACM pages, not single-spaced Word pages.

---

## 4. Mandatory formatting requirements

**Sources:** [ACM submission process](https://authors.acm.org/journals/submission-process); [ACM LaTeX guide](https://authors.acm.org/proceedings/production-information/preparing-your-article-with-latex); [Overleaf acmart template](https://www.overleaf.com/latex/templates/association-for-computing-machinery-acm-small-standard-format-template/sksvmbxyfhnw)

### LaTeX (preferred)

```latex
\documentclass[manuscript]{acmart}
```

- Use **single-column `manuscript` option** for review submission
- Use latest **Primary Article Template** (acmart v2.18+; v2.19 as of June 2026 per ACM)
- Install **Libertine font set** before building (required; no substitution)
- **Do not** modify margins, line spacing, or template definitions
- Upon acceptance: remove `manuscript` option; submit to **ACM TAPS** for production

### Word

- Use ACM **Submission Template (Review Submission Format)**
- Single-column for review

### Required metadata (articles > 2 pages)

**Source:** [ACM ancillary template information](https://www.acm.org/publications/authors/submissions-bottom)

- **CCS Concepts** (required for articles > 2 pages)
- **Keywords** (required for articles > 2 pages)
- **ACM Reference Format** bibliography (required for articles > 1 page)

Suggested CCS concepts for our paper:

- Information systems → Data management systems → Data cleaning
- Information systems → Information retrieval → Retrieval models and ranking
- Computing methodologies → Machine learning → Learning paradigms → Supervised learning (for selector appendix)

---

## 5. Review process

**Source:** [JDIQ Editors' Comments, DOI 10.1145/1659225.1659226](https://doi.org/10.1145/1659225.1659226); JDIQ special-issue CFPs

- **Double-anonymous (double-blind)** review
- Typically **Associate Editor + ≥3 reviewers**
- **No accepted papers** in early JDIQ issues without revision (all required minor/major revision)
- ~**1/3 desk rejection** rate for TOIS-family journals (JDIQ FAQ on related TOIS process; expect similar screen for scope mismatch)

**Anonymization checklist:**

- Remove repository URLs that expose author identity (use anonymous artifact hosting or “available upon acceptance”)
- Anonymize acknowledgments
- Self-citation in third person or omit until camera-ready

---

## 6. Prior publication and overlap policy

**Sources:** JDIQ special-issue CFPs; CODE-ISSS authors page

- Extensions of prior work must contain **≥ 30% new material**
- **Significant new contributions must be identified in the introduction**
- Must disclose **all overlapping publications**

**Our situation:** IJCS rejection is unpublished (rejected). Prior drafts (Applied Intelligence, internal) must be checked for overlap. New JDIQ paper must emphasize:

1. DQ framing (not algorithm-design framing)
2. CARB benchmark contribution
3. Failure taxonomy as DQ diagnostic
4. Four-dataset empirical breadth not in IJCS

---

## 7. Reproducibility and artifact expectations

**Sources:** JDIQ scope (rigorous methods); [TOIS reproducibility emphasis](https://doi.org/10.1145/3447945) (sibling ACM journal standard); ACM artifact badging practice

JDIQ does not publish a separate artifact badging policy, but:

- Reproducibility is expected for empirical claims
- **Code and data availability** strengthen empirical DQ papers
- Describe how to reproduce tables and figures from canonical scripts

**Recommended for our submission:**

| Artifact | Content |
|----------|---------|
| Code repository | Public release or anonymous review archive |
| CARB data | Feature-only supplementary release (see created_data_audit) |
| Reproduction script | `scripts/run_publication_vote_suite.py` + `build_paper_evidence_package.py` |
| Environment | `requirements.txt`, Python 3.11+ |
| Fixed seeds | Document all random seeds |

---

## 8. Data availability expectations

**Source:** JDIQ scope (information curation); resource-paper guidelines in SI CFPs

- Describe **provenance** of all datasets (SciDocs, FiQA, HotpotQA, BRIGHT — all public)
- State **what is released** vs withheld (raw doc text, API caches, prompts)
- Provide **data card** for CARB (schema in `experiments/created_data_audit_*/phase10/`)
- Document **licensing** for derived artifacts

---

## 9. Supplementary material

**Source:** JDIQ experience-paper CFP (optional appendix); ACM DL supplementary practice

- Supplementary material is **encouraged** for extended tables, failure taxonomy details, CARB schema
- Keep main paper self-contained; move 366-method grid and selector details to supplement
- CARB can be linked as **supplementary dataset** or separate resource paper

---

## 10. Reference style

**Source:** [ACM Reference Format](https://www.acm.org/publications/authors/reference-format)

- Use **ACM Reference Format** (not IEEE, not APA)
- BibTeX: `ACM-Reference-Format` style with `acmart` class
- Citations appear as numbered `[n]` in review format

---

## 11. Section expectations (research paper)

Typical JDIQ technical paper structure:

| Section | Expectation |
|---------|-------------|
| Abstract | 150–250 words; problem, method, key findings, implications |
| Introduction | DQ motivation; contributions as bullet list; paper roadmap |
| Related Work | DQ frameworks, preference aggregation, rank fusion, graph consistency |
| Problem / Formalization | Define preference-graph DQ dimensions |
| Method / Approach | Vote construction, FAS repair, evaluation protocol |
| Experimental Setup | Datasets, baselines, metrics, statistical tests |
| Results | DQ improvement vs downstream task quality (decoupling) |
| Discussion | Practical implications: when to repair, when not |
| Threats to Validity | Protocol boundaries, BEW/PIC circularity, LLM scale |
| Conclusion | Summary; future work |
| Data Availability | CARB release statement |
| Acknowledgments | (camera-ready only if anonymous review) |

---

## 12. Abstract requirements

- Concise: typically **≤ 250 words** in ACM template
- Must state: **DQ problem**, **approach**, **empirical scope**, **main finding**, **practical implication**
- Avoid: “we propose a new method that improves ranking” (contradicted by evidence)
- Lead with: **decoupling of structural DQ improvement from retrieval quality**

---

## 13. Recommended practices

1. **Lead with information quality**, not algorithm novelty
2. **Compartmentalize experiment families** (vote suite vs failure-mining pooled vs LLM pilots)
3. **Report negative/null results** honestly — JDIQ values practical implications
4. **Include actionable guidance** (when repair is inactive, harmful, or irrelevant)
5. **Position CARB** as curation/benchmark contribution
6. **Pre-register claims** using `final_claim_support_matrix.csv` discipline
7. **Use bootstrap CIs** already computed (2000 reps) — do not invent new statistics
8. **Cite canonical source** (`pub_vote_cmp_all4`) for all main tables

---

## 14. Common mistakes to avoid

| Mistake | Risk |
|---------|------|
| Mixing `pub_vote_cmp_v2` and `pub_vote_cmp_all4` numbers | Internal inconsistency; reviewer distrust |
| Claiming uniform retrieval improvement | Contradicted by repository evidence |
| Framing as IR algorithm paper at KBS/TOIS level | JDIQ scope mismatch in opposite direction — avoid IR-only framing without DQ hook |
| Ignoring BEW/PIC circularity (same qrels) | Validity attack |
| Presenting tiny LLM pilots as confirmatory | Overclaiming |
| Using stale `manuscript_artifacts/` tables | Wrong numbers |
| Omitting CCS concepts / keywords | Desk rejection for metadata incompleteness |
| Modifying `acmart` margins | Format rejection at TAPS |
| Failing to disclose IJCS overlap | Ethics concern |

---

## 15. Submission checklist

### Before writing
- [ ] Read this guideline summary
- [ ] Read `CANONICAL_PAPER_STORY.md`
- [ ] Confirm claim matrix (`final_claim_support_matrix.csv`)

### Manuscript preparation
- [ ] `acmart` template with `[manuscript]` option
- [ ] CCS concepts and keywords
- [ ] ACM Reference Format bibliography
- [ ] Anonymous submission (no identifying metadata)
- [ ] ≥ 30% new material vs any prior draft; disclosed in introduction
- [ ] All figures ≥ 300 dpi; vector preferred
- [ ] Tables from canonical `pub_vote_cmp_all4` only

### Content
- [ ] DQ framing in title, abstract, introduction
- [ ] Four datasets reported with vote regimes
- [ ] Failure taxonomy with frequencies
- [ ] Baseline comparison (CombSUM, RRF, prior)
- [ ] Limitations: BEW/PIC, LLM scale, protocol boundaries
- [ ] Data availability statement for CARB
- [ ] Reproducibility statement with script paths

### Supplementary
- [ ] CARB schema document
- [ ] Extended baseline tables
- [ ] Claim-evidence matrix (optional, for reviewers)
- [ ] Reproduction README

### Final checks
- [ ] Spell-check; ACM style
- [ ] All acronyms defined at first use
- [ ] Figure/table captions self-contained
- [ ] Page limit respected (~20–25 pages research paper)
- [ ] Submit via ACM JDIQ portal (not email)

---

## 16. Submission portal

**Source:** https://dl.acm.org/journal/jdiq → Submit manuscript

Select paper type: **Research/Technical paper** (not experience, not challenge).

---

*This summary is a workspace planning document. Always verify against the live ACM JDIQ author guidelines before submission.*
