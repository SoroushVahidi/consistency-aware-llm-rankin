# SN Computer Science Portal Dry Run

**Date:** 2026-08-02  
**Sources:** SN Computer Science submission guidelines
(https://link.springer.com/journal/42979/submission-guidelines; accessed
2026-08-02), Springer Nature editorial policies
(https://www.springernature.com/gp/policies/editorial-policies),
`SUBMISSION_METADATA.md`, manuscript `main.tex`.  
**Action:** simulate every common portal field. **Do not submit.**

## Copy-ready field values

### Article type

Original Research  

**Author confirmation required** if the portal’s dropdown uses a different label
(e.g. “Research”, “Original Article”).

### Title

Structural Consistency Does Not Reliably Predict Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval

### Running title

Structural Consistency vs. Retrieval Utility

### Abstract (structured; Method A = 219 words; Method B = 245 words; both ≤250)

Purpose: Preference-graph repair is often treated as if restoring acyclicity improves ranking quality. Heuristic studies leave greedy graph-objective suboptimality open for null results, and construction is rarely experimental. This study tests whether heuristic or exact minimum-weight feedback-arc-set (MWFAS) edge-deletion repair yields a multiplicity-corrected retrieval gain for score-derived multi-ranker graphs.

Methods: On four public benchmarks, graphs were built from stored BM25, TF-IDF, and MiniLM scores under three vote-construction regimes. Unrepaired, greedy, and exact repairs were compared with paired sign-flip tests and Holm correction. Exact SCIP diagnosed greedy suboptimality for the stated edge-deletion objective.

Results: Construction dominated structure: a conservative regime was always acyclic; a permissive regime was cyclic for most queries. Normalization cut BM25 edge-weight share from 0.988 to 0.512. Repair removed contradictory weight and changed top-k membership by 10.6% when pools exceeded the cutoff. No repaired-versus-unrepaired nDCG comparison survived Holm correction in the canonical, larger-pool, or exact-repair families. Dataset-macro nDCG kept CombSUM competitive (0.554) with the best repaired hybrid (0.546). Exact repair removed less weight than greedy yet yielded no corrected retrieval gain.

Conclusion: Under this protocol, repair is structurally active but not a validated nDCG optimization. Missing Holm-corrected evidence is not equivalence; smaller effects remain possible. The contribution is a factorized audit of construction, repair, extraction, and utility, with exact MWFAS only as an identification control.

### Keywords (4–6)

preference graphs; feedback arc set; graph repair; rank aggregation; information retrieval; retrieval evaluation

### Author name

Soroush Vahidi

### Affiliation

Ying Wu College of Computing, New Jersey Institute of Technology, Newark, NJ, USA

### Corresponding-author email

sv96@njit.edu

### ORCID

https://orcid.org/0000-0003-1934-6282

(Verified; enter in the portal ORCID field and confirm matching manuscript title-page link.)

### Phone / postal address beyond affiliation city/state/country

**Author confirmation required — do not invent.** Not recorded for portal use in this package.

### Funding

This work received in-kind computational support through the Cohere Labs Catalyst Grant Program, the Google Cloud Research Credits Program, Microsoft Azure for Students, and Fireworks AI credits provided through the AMD AI Developer Program. These resources supported the bounded real-LLM pilot (Microsoft Azure / OpenAI-compatible, Google Gemini, Cohere, and Fireworks AI APIs). The principal score-derived experiments used stored BM25, TF-IDF, and MiniLM scores and local open-source SCIP solving and required no paid LLM API calls. The supporting organizations had no role in the study design, analysis, interpretation, or preparation of the manuscript.

**Author confirmation required** for any formal grant identifier / award number if the portal has a structured funding registry field (none verified here).

### Acknowledgements

The author thanks Professor Ioannis Koutis for his guidance and support, Mitra Sharifani for her sustained personal support, and Anders Borum for providing lifetime access to Secure ShellFish for the author's remote research workflow.

(Funding organizations are **not** repeated here.)

### Competing interests

The author declares that there are no competing interests.

### Authors’ contributions

This is single-author work. Soroush Vahidi conceived the study, designed and implemented the experimental pipeline, ran the experiments, analyzed and verified the results, prepared the figures and tables, and wrote the manuscript.

### Ethics approval

Not applicable. This study uses only publicly available benchmark datasets and stored, derived score files; it involves no human subjects, no personal or identifiable data, and no new data collection from human participants.

### Consent to participate

Not applicable; no human participants were involved in this study.

### Consent for publication

Not applicable; no individual person's data are presented in this manuscript.

### Data availability

The datasets used in this study are publicly available from their original sources and are cited in the manuscript. No new benchmark dataset was generated. Compact processed artifacts used to generate the reported results are available in the public repository linked under Code availability. Raw provider request and response payloads from the bounded large-language-model pilot are not included in the repository, because they may contain prompt/completion content and operational details excluded by the project's artifact policy.

### Code availability

The code, fixed query lists, processed intermediates, figure data, and scripts required to reproduce the reported tables and figures are available at https://github.com/SoroushVahidi/consistency-aware-llm-rankin.

### Materials availability

Not applicable. This study does not generate new physical materials.

### Generative-AI disclosure

Anthropic Claude was used for software-development assistance, analysis and audit utilities, figure preparation, and drafting and revising portions of the manuscript. The author independently reviewed and verified all AI-assisted code, analyses, figures, citations, and text against the source materials and underlying evidence and assumes full responsibility for the work. No generative-AI tool is credited as an author.

### Preprint disclosure

Research Square preprint DOI: 10.21203/rs.3.rs-9335700/v1 (public preprint; not an active journal submission). Current manuscript supersedes the preprint’s retrieval interpretation where the revised protocol changes the conclusion.

### Suggested reviewers

| Name | Institution | Email | Fit |
|---|---|---|---|
| Jimmy Lin | University of Waterloo | jimmylin@uwaterloo.ca | IR, reproducible retrieval, neural/LLM ranking |
| Julian Urbano | Delft University of Technology | j.urbano@tudelft.nl | IR statistical testing, multiple comparisons |
| Nir Ailon | Technion | nailon@cs.technion.ac.il | Rank aggregation, feedback arc set |
| Sewoong Oh | University of Washington | sewoong@cs.washington.edu | Ranking from pairwise comparisons |
| David F. Gleich | Purdue University | dgleich@purdue.edu | Graph algorithms, reproducible scientific computing |
| Michael D. Ekstrand | Drexel University | mdekstrand@drexel.edu | Evaluation, reproducibility, multiple testing |
| Nihar B. Shah (alternate) | Carnegie Mellon University | nihars@cs.cmu.edu | Pairwise comparisons, evaluation science |

### Opposed reviewers

None formally requested unless the portal requires a conflict list. If required, use only the conflict entries in `SUBMISSION_METADATA.md` (acknowledged mentors/supporters and credit-program entities as inappropriate scientific reviewers — not “scientific opposition”).

**Author confirmation required** before entering any opposed-reviewer names.

### Cover-letter text

Use the full letter in `COVER_LETTER.md`.

### Manuscript classifications / subject areas

Suggested (confirm against portal taxonomy — **author confirmation required** for exact codes):

- Information Retrieval
- Algorithms / Data Structures (feedback arc set / ranking aggregation)
- Empirical methods / evaluation methodology
- Mathematical programming / combinatorial optimization (MWFAS / SCIP control)

Exact SNCS subject-area pick-list values were not scraped as stable IDs in this dry run; choose the closest portal categories without inventing codes.

### Files to attach (see `UPLOAD_MANIFEST.md`)

1. `main.pdf`
2. `SNCS_2026_latex_source.zip`
3. Cover letter
4. Separate figures only if required
5. Highlights only if required

## Portal procedural checklist (simulated)

| Step | Status |
|---|---|
| Create account / select SN Computer Science | Author action |
| Choose article type | Ready pending label confirm |
| Enter title, running title, abstract, keywords | Ready |
| Enter author, affiliation, email | Ready; ORCID entered |
| Paste Statements and Declarations | Ready |
| Upload PDF + editable source | Ready |
| Enter data/code URLs | Ready (public repo) |
| Suggest reviewers | Ready |
| Opposed reviewers | Only if asked |
| Review PDF proof | Author action after upload |
| Final submit | **Do not click** without explicit authorization |

## Information still requiring author confirmation

1. Exact article-type dropdown label.
2. Phone / full mailing address if the portal requires them.
3. Structured funding award IDs, if any.
4. Exact subject-area / MSC-like classification codes in the portal taxonomy.
5. Whether opposed reviewers must be entered.
6. Whether a separate highlights file is requested (optional PDF ready).
7. Whether to append the freeze commit SHA in the portal code-availability free text.
8. Timing: create Git tag `sncs-2026-submission-v1` immediately before vs after clicking submit (recommendation in `RELEASE_CANDIDATE_DECISION.md`).
