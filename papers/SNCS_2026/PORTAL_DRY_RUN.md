# SN Computer Science Portal Dry Run

**Date:** 2026-08-01  
**Sources:** SN Computer Science submission guidelines
(https://link.springer.com/journal/42979/submission-guidelines), existing
`SUBMISSION_METADATA.md`, manuscript `main.tex`, and Springer Editorial Manager
LaTeX upload practice notes.  
**Action:** simulate every common portal field. **Do not submit.**

## Copy-ready field values

### Article type

Original Research  

**Author confirmation required** if the portal’s dropdown uses a different label
(e.g. “Research”, “Original Article”).

### Title

Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval

### Running title

Structural Consistency Is Not Retrieval Utility

### Abstract (structured; 248 words)

Purpose: Preference-graph repair is often treated as if restoring acyclicity should improve ranking quality. This study asks whether, for score-derived multi-ranker retrieval graphs, heuristic or exact minimum-weight feedback-arc-set repair yields a multiplicity-corrected retrieval gain -- or whether structural consistency and retrieval utility must be reported as separate claims.

Methods: On four public benchmarks, query-level preference graphs were built from stored BM25, TF-IDF, and MiniLM scores under three vote-construction regimes. Rankings from unrepaired, greedy-repaired, and exactly repaired graphs were compared with paired sign-flip tests and Holm correction. Exact SCIP solutions served as a diagnostic control on heuristic under-repair, not as a production solver.

Results: Construction dominated structure: a conservative regime was acyclic throughout, while a permissive regime was cyclic for most queries; normalizing scores reduced BM25's conditional edge-weight share from 0.988 to 0.512. Repair removed non-trivial contradictory weight and, pooled across vote regimes when the pool exceeded the cutoff, changed top-k membership by 10.6% on average, yet no repaired-versus-unrepaired normalized discounted cumulative gain (nDCG) comparison survived Holm correction in the canonical, larger-pool, or exact-repair families. Graph-free fusion was competitive (CombSUM 0.554 versus 0.546 for the best repaired hybrid). Exact repair removed less weight than greedy repair yet still yielded no corrected retrieval gain.

Conclusion: Under this protocol, preference-graph repair is a real structural intervention but not a validated nDCG optimization step. Improving the repair objective -- even to certified optimality -- does not substitute for downstream evaluation; treat acyclicity metrics as structural diagnostics, not as proxies for retrieval utility.

### Keywords (4–6)

preference graphs; feedback arc set; graph repair; rank aggregation; information retrieval; retrieval evaluation

(Manuscript `\keywords` line; portal may also accept the slightly expanded list in `SUBMISSION_METADATA.md` — keep to ≤6 terms.)

### Author name

Soroush Vahidi

### Affiliation

Ying Wu College of Computing, New Jersey Institute of Technology, Newark, NJ, USA

### Corresponding-author email

sv96@njit.edu

### ORCID

**Author confirmation required — do not invent.** No verified ORCID is recorded in this repository. Leave blank unless the author supplies an ORCID iD.

### Phone / postal address beyond affiliation city/state/country

**Author confirmation required — do not invent.** Not recorded for portal use in this package.

### Funding

This work received computational support through the Cohere Labs Catalyst Grant Program, the Google Cloud Research Credits Program, Microsoft Azure for Students, and Fireworks AI credits provided through the AMD AI Developer Program. The funders had no role in the study design, data analysis, interpretation of results, or preparation of the manuscript.

**Author confirmation required** for any formal grant identifier / award number if the portal has a structured funding registry field (none verified here).

### Acknowledgements

The author thanks Professor Ioannis Koutis for his guidance and emotional support, his mother for her sustained emotional support, and Anders Borum for providing lifetime access to Secure ShellFish.

(Funding organizations are **not** repeated here.)

### Competing interests

The author declares no competing interests.

### Authors’ contributions

This is single-author work. Soroush Vahidi conceived the study, designed and implemented the experimental pipeline, ran the experiments, analyzed and verified the results, prepared the figures and tables, and wrote the manuscript.

### Ethics approval

Not applicable. This study uses only publicly available benchmark datasets and stored, derived score files; it involves no human subjects, no personal or identifiable data, and no new data collection from human participants.

### Consent to participate

Not applicable; no human participants were involved in this study.

### Consent for publication

Not applicable; no individual person's data are presented in this manuscript.

### Data availability

The datasets used in this study are publicly available from their original sources and are cited in the manuscript. No new benchmark dataset was generated. The code and processed artifacts used to generate the reported results are available at https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Raw provider request and response payloads from the bounded large-language-model pilot are not included in the repository for the reasons stated in the manuscript.

### Code availability

The code, fixed query lists, processed intermediates, figure data, and scripts required to reproduce the reported tables and figures are available at https://github.com/SoroushVahidi/consistency-aware-llm-rankin.

(After freeze commit is recorded, author may optionally append: “Submission freeze commit: `<SHA>`; see `papers/SNCS_2026/SUBMISSION_FREEZE.md`.”)

### Generative-AI disclosure

Generative artificial-intelligence tools (Anthropic's Claude, via the Claude Code command-line environment) were used to assist with software development for this study - writing and revising analysis code, statistical-inference utilities, figure-generation scripts, and audit scripts - and with drafting, revising, and fact-checking portions of this manuscript's text and figures. Every AI-assisted code change, statistical analysis, figure, table, citation, and passage of manuscript text was reviewed and independently verified against the underlying stored data and source code by the author before inclusion; no generative-AI output was accepted without that verification. The author takes full responsibility for the accuracy, integrity, and originality of the source code, experiments, statistical analyses, figures, tables, interpretations, citations, and manuscript text in this work. No generative-AI tool is credited as an author, and no generative-AI tool independently designed the study, selected the research questions, or made scientific judgments attributed to the author in this manuscript.

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

Use the full letter in `COVER_LETTER.md` / `SUBMISSION_METADATA.md` (“Dear Editor-in-Chief…”).

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
| Enter author, affiliation, email | Ready; ORCID pending |
| Paste Statements and Declarations | Ready |
| Upload PDF + editable source | Ready |
| Enter data/code URLs | Ready (public repo) |
| Suggest reviewers | Ready |
| Opposed reviewers | Only if asked |
| Review PDF proof | Author action after upload |
| Final submit | **Do not click** without explicit authorization |

## Information still requiring author confirmation

1. Exact article-type dropdown label.
2. ORCID iD (if any).
3. Phone / full mailing address if the portal requires them.
4. Structured funding award IDs, if any.
5. Exact subject-area / MSC-like classification codes in the portal taxonomy.
6. Whether opposed reviewers must be entered.
7. Whether a separate highlights file is requested.
8. Whether to append the freeze commit SHA in the portal code-availability free text.
9. Timing: create Git tag `sncs-2026-submission-v1` immediately before vs after clicking submit (recommendation in `RELEASE_CANDIDATE_DECISION.md`).
