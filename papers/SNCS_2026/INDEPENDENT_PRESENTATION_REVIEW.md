# Independent Presentation Review

Primary input: `papers/SNCS_2026/manuscript/main.pdf`, read first as a
submission PDF. Source-line references below refer to the current
`main.tex` after safe review fixes.

## 2.1 Writing and Organization

The manuscript reads like a journal article rather than a repository report.
The writing is careful, explicit about scope, and generally clear. Section order
is conventional for SN Computer Science: Introduction, Related Work, Methods,
Results, Discussion, Conclusion, Declarations, References.

The main editorial risk is repetition from defensive scope control. It is
scientifically useful, but a reviewer may feel the manuscript tells them several
times what the paper does not claim.

Exact passages worth watching:

| Location | Issue | Assessment |
|---|---|---|
| `main.tex` lines 151-168 | Long explanation of exact repair's diagnostic role | Correct and important, but dense. Keep unless word pressure requires shortening. |
| `main.tex` lines 170-181 | Non-claims list | Strong scope control; slightly defensive. Acceptable as written for submission. |
| `main.tex` lines 198-222 | Contributions | Clear, but repeats some abstract/intro phrasing. Acceptable. |
| `main.tex` lines 1522-1554 | Table 6 caption/content | Dense robustness summary. Width was improved; content is still justified. |
| Discussion/Limitations, especially lines 1850-1968 | Conservative validity framing | Strong and journal-appropriate, though lengthy. |

No passage requires large rewriting. The best editorial stance is to keep the
restraint and avoid broadening claims.

## 2.2 Abstract

The structured abstract is self-contained, defines the problem, identifies
datasets and methods, states the central finding, and avoids unsupported LLM
generalization. It does not use unexplained acronyms except nDCG, which is
expanded before first use in the Results part.

The abstract is approximately 196 words, within Springer Nature's stated
150-250 word range for SN Computer Science structured abstracts. It accurately
matches the manuscript.

The title is accurate and appropriately emphasizes the distinction between
structural consistency and retrieval utility. It does not imply a new
state-of-the-art method. No title change is recommended.

Abstract score: 88/100.

## 2.3 Figures, Tables, and Pseudocode

Visual inspection of the compiled PDF found no margin overflow, missing
captions, malformed cross-references, or unreadable figures. Most visuals are
dense but necessary.

| Item | Classification | Rationale |
|---|---|---|
| Figure 1 | Keep unchanged | Pipeline schematic is readable and clarifies scope. |
| Table 1 | Keep unchanged | Dataset/workload summary is dense but interpretable. |
| Algorithm 1 | Keep unchanged | Fits the page and matches implementation-level description. |
| Table 2 | Keep unchanged | Helpful taxonomy separating primary, expanded, and structural-only comparisons. |
| Table 3 | Keep unchanged | Central structural result table; clear enough. |
| Figure 2 | Keep unchanged | Readable and necessary for graph-construction effects. |
| Figure 3 | Minor revision | Tick labels are small; not blocking because the caption and trends are still readable. |
| Table 4 | Keep unchanged | Central retrieval result table. |
| Figure 4 | Keep unchanged | Conservative effect-size display; does not imply unsupported significance. |
| Table 5 | Keep unchanged | Dense exact-repair summary, but scientifically important. |
| Figure 5 | Minor revision | In-figure note is long; acceptable because it prevents overinterpretation. |
| Table 6 | Minor revision applied | Original layout was narrow and effortful. Column widths were increased and the rendered page now fits cleanly. |

No figure-regeneration prompt is required before submission. If time permits,
Figure 3 could be regenerated with slightly larger tick labels, but that is not
a submission blocker.

## 2.4 Mathematical Presentation

Display formulas are numbered where needed. Variables are defined close to
their first use, and notation for graph construction, edge weights, repair
objective, ranking extraction, and retrieval evaluation is consistent with the
implementation.

No undefined symbol or equation-reference defect was found in the final PDF.
The algorithm fits on the page. Equation punctuation is consistent enough for
submission.

## 2.5 Citation and Quotation Accuracy

No direct quotation problem was found. The paper uses paraphrase rather than
extended quoted text.

Citation issues found:

| Issue | Resolution |
|---|---|
| Recent graph-based pairwise LLM reranking needed closer coverage. | Added PRP-Graph: Luo, Chen, He, and Sun, ACL 2024, DOI `10.18653/v1/2024.acl-long.313`, to Section 2.2. |
| Exact MWFAS/linear-ordering lineage was underdeveloped. | Added Groetschel, Juenger, and Reinelt 1984 and Baharev et al. 2021 to Section 2.3. |
| TourRank is relevant recent LLM tournament ranking work. | Not added as a required citation because it is optional future work and not necessary for the paper's repair-vs-utility inference. |

No sentence currently ends with an excessive pileup of unrelated citations after
the applied additions.

## 2.6 Journal Formatting and Style

Official SN Computer Science guidance checked at
https://link.springer.com/journal/42979/submission-guidelines.

Verified requirements:

- Single-blind title page with author name, affiliation, and corresponding email
  is appropriate.
- Structured abstract uses Purpose, Methods, Results, and Conclusion, and is in
  the 150-250 word range.
- Keywords must be 4-6. The manuscript had 8; this was corrected to 6.
- Numbered citation style is consistent with the `sn-basic`/Numbered setup.
- Figure and table numbering/citations are in order in the compiled PDF.
- Declarations include funding, competing interests, ethics/consent,
  generative-AI disclosure, data availability, and code availability.
- Springer Nature's AI-authorship guidance is satisfied: AI tools are not listed
  as authors, and AI use is disclosed in a suitable declaration.
- Source files are expected at submission; a local source archive is maintained
  in the submission package.

Recent accepted SN Computer Science technical articles use similar section
depth, declaration style, and article tone. The manuscript is longer and more
audit-heavy than many, but the density is justified by its evidence-mapping and
statistical design.

Rules not fully verifiable from public guidance: no hard page limit specific to
this article type was identified in the official journal page.

## 2.7 Limitations and Future Work

The limitations section is one of the strongest parts of the paper. It covers:
internal validity, construct validity, external validity, statistical conclusion
validity, computational limitations, exact-solver scalability, limited LLM
evidence, possible failure cases, and contexts where repair may or may not
matter.

Future work is specific enough: larger direct LLM audits, per-query prediction
of when repair matters, richer graph construction, and solver/scalability work.
The manuscript avoids generic "more data and models" wording.

## 2.8 Acknowledgements and Funding

The manuscript correctly acknowledges Professor Ioannis Koutis, the author's
mother, Anders Borum, the Cohere Labs Catalyst Grant Program, Google Cloud
Research Credits Program, Microsoft Azure for Students, and AMD/Fireworks AI
support where appropriate.

Funding and acknowledgements are professionally worded. Grant-like support is
represented in the Funding declaration. No private emails, endpoints, API keys,
project IDs, or raw provider responses appear in the manuscript text.

Provider/model reporting was checked against tracked metadata. The six-query
pilot uses Azure OpenAI `gpt-4.1-mini`, Google Gemini `gemini-2.5-flash`, Cohere
`command-r-plus-08-2024`, and Fireworks AI `gpt-oss-120b`. The tracked evidence
does not prove whether Gemini transport was Gemini Developer API or Vertex AI;
the manuscript should retain provider-level wording unless verifiable transport
evidence is supplied.
