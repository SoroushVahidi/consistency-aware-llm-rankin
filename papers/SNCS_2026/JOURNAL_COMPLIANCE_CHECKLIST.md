# SN Computer Science Compliance Checklist

Date: 2026-08-02
Official sources checked (access date 2026-08-02):
- SN Computer Science submission guidelines: https://link.springer.com/journal/42979/submission-guidelines
- SN Computer Science journal home/aims and scope: https://link.springer.com/journal/42979
- Springer Nature editorial policies (incl. AI / preprint / authorship): https://www.springernature.com/gp/policies/editorial-policies
- Springer Nature research data and code policies: https://www.springernature.com/gp/authors/research-data-policy and https://www.springernature.com/gp/open-science/code-policy

| Requirement | Status | Evidence |
|---|---|---|
| Article type fits journal scope | PASS | Journal scope includes Information Retrieval, Algorithms and Data Structures, Mathematical Programming and Combinatorial Optimization. |
| Single-blind compliance | PASS | Author name, affiliation, and email are present; single-blind review is stated by the journal. |
| Source files | PASS | Manuscript is LaTeX; journal requires editable source (.docx or LaTeX). |
| Title page contains title | PASS | `\title` present (current: Does Not Reliably Predict…). |
| Author information | PASS | Author name, affiliation, and active email present. ORCID is not included because none was verified in the repository. |
| Structured abstract | PASS | Purpose / Methods / Results / Conclusion; Method A = 219 words, Method B = 245 words; both ≤250. |
| Keywords | PASS | Six keywords (within 4–6). |
| Heading levels | PASS | Uses section/subsection only in displayed manuscript headings, within the three-level limit. |
| Abbreviations | PASS | Key abbreviations are defined before substantive use: MWFAS, SCIP, nDCG, MRR, MAP, LLM. |
| Citation style | PASS | `sn-basic` with `Numbered`; compiled citations appear numeric. |
| Reference list | PASS | Clean tectonic build; no undefined citations/references in log. |
| Tables numbered and cited | PASS | Ten tables in compiled PDF destinations; all labeled/captioned and cited. |
| Figures numbered and cited | PASS | Five figures; Figure 1 uses author-uploaded `figures/f1_pipeline.png` (SHA-256 `4feeac61…5af2`). |
| Figure files electronic/vector | PASS | Figures 2–5 are vector PDFs; Figure 1 is the author PNG required for the manuscript. |
| Acknowledgments | PASS | Separate `Acknowledgments` section (personal/non-funding). SNCS text says acknowledgments “on the title page”; sn-jnl places a dedicated section before declarations — least-risky template-compatible placement retained. Ambiguity recorded. |
| Statements and Declarations heading | PASS | Manuscript uses `Statements and Declarations`. |
| Funding | PASS | In-kind computational support for the real-LLM pilot only; principal experiments use stored scores + local SCIP; organizations’ non-role stated. |
| Competing interests | PASS | Declares no competing interests. |
| Ethics approval | PASS | States not applicable and explains public benchmarks/no human subjects. |
| Consent | PASS | Consent to participate and consent for publication marked not applicable. |
| Data availability | PASS | Public benchmarks, compact processed artifacts, raw-provider exclusion stated. |
| Code availability | PASS | Public repository URL stated. |
| Materials availability | PASS | Not applicable. |
| Author contributions | PASS | Concise single-author statement. |
| Generative AI policy | PASS | LLM use disclosed in Methodology/Reproducibility; AI is not listed as author; author accountability stated. |
| Preprint policy | PASS | Research Square preprint disclosed; cover letter states it is not an active journal submission / no dual submission. |
| Originality/not under consideration | PASS for package | Cover letter states originality and no concurrent consideration. |
| Highlights | NOT APPLICABLE | SNCS guidelines do not require highlights; optional file prepared. |
| Supplementary Information | NOT USED | No SI file created in this freeze; main PDF is 36 pages. |

## Residual Notes / Ambiguities

1. Structured-abstract section labels: the live guidelines page states a structured abstract of 150–250 words “divided into the following sections,” then shows a CMS fragment “For life science journals only.” Purpose/Methods/Results/Conclusion is retained as the least-risky reading already used by this package and consistent with journal examples elsewhere on Springer Nature sites.
2. Acknowledgments “on the title page” vs sn-jnl dedicated section: retained dedicated section matching the vendored template practice.
3. ORCID: not invented; author must supply if the portal requires it.
