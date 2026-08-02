# Submission Metadata

Date: 2026-08-02
Target journal: SN Computer Science
Access date for official guidelines: 2026-08-02
Official guidelines URL: https://link.springer.com/journal/42979/submission-guidelines
Springer Nature editorial policies URL: https://www.springernature.com/gp/policies/editorial-policies

## Copy-Ready Fields

Manuscript title:

Structural Consistency Does Not Reliably Predict Retrieval Utility: An
Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker
Retrieval

Running title:

Structural Consistency vs. Retrieval Utility

Article type:

Original Research

Abstract:

Purpose: Preference-graph repair is often treated as if restoring acyclicity improves ranking quality. Heuristic studies leave greedy graph-objective suboptimality open for null results, and construction is rarely experimental. This study tests whether heuristic or exact minimum-weight feedback-arc-set (MWFAS) edge-deletion repair yields a multiplicity-corrected retrieval gain for score-derived multi-ranker graphs.

Methods: On four public benchmarks, graphs were built from stored BM25, TF-IDF, and MiniLM scores under three vote-construction regimes. Unrepaired, greedy, and exact repairs were compared with paired sign-flip tests and Holm correction. Exact SCIP diagnosed greedy suboptimality for the stated edge-deletion objective.

Results: Construction dominated structure: a conservative regime was always acyclic; a permissive regime was cyclic for most queries. Normalization cut BM25 edge-weight share from 0.988 to 0.512. Repair removed contradictory weight and changed top-k membership by 10.6% when pools exceeded the cutoff. No repaired-versus-unrepaired nDCG comparison survived Holm correction in the canonical, larger-pool, or exact-repair families. Dataset-macro nDCG kept CombSUM competitive (0.554) with the best repaired hybrid (0.546). Exact repair removed less weight than greedy yet yielded no corrected retrieval gain.

Conclusion: Under this protocol, repair is structurally active but not a validated nDCG optimization. Missing Holm-corrected evidence is not equivalence; smaller effects remain possible. The contribution is a factorized audit of construction, repair, extraction, and utility, with exact MWFAS only as an identification control.

Abstract word counts (2026-08-02):
- Method A (whitespace / `wc -w`): 217
- Method B (alphanumeric tokens; hyphenated compounds split): 243
Both ≤250 (SN Computer Science structured-abstract limit).

Keywords:

preference graphs; feedback arc set; graph repair; rank aggregation;
information retrieval; retrieval evaluation

Corresponding author:

Soroush Vahidi

Author affiliation:

Ying Wu College of Computing, New Jersey Institute of Technology, Newark, NJ,
USA

Author email:

sv96@njit.edu

ORCID:

https://orcid.org/0000-0003-1934-6282

Funding statement:

This work received in-kind computational support through the Cohere Labs
Catalyst Grant Program, the Google Cloud Research Credits Program,
Microsoft Azure for Students, and Fireworks AI credits provided through
the AMD AI Developer Program. These resources supported the bounded
real-LLM pilot (Microsoft Azure / OpenAI-compatible, Google Gemini,
Cohere, and Fireworks AI APIs). The principal score-derived experiments
used stored BM25, TF-IDF, and MiniLM scores and local open-source SCIP
solving and required no paid LLM API calls. The supporting organizations
had no role in the study design, analysis, interpretation, or preparation
of the manuscript.

Competing-interests statement:

The author declares that there are no competing interests.

Ethics approval:

Not applicable. This study uses only publicly available benchmark datasets and
stored, derived score files; it involves no human subjects, no personal or
identifiable data, and no new data collection from human participants.

Consent to participate:

Not applicable; no human participants were involved in this study.

Consent for publication:

Not applicable; no individual person's data are presented in this manuscript.

Data-availability statement:

The datasets used in this study are publicly available from their original
sources and are cited in the manuscript. No new benchmark dataset was
generated. Compact processed artifacts used to generate the reported results
are available in the public repository linked under Code availability. Raw
provider request and response payloads from the bounded large-language-model
pilot are not included in the repository, because they may contain
prompt/completion content and operational details excluded by the project's
artifact policy.

Code-availability statement:

The code, fixed query lists, processed intermediates, figure data, and scripts
required to reproduce the reported tables and figures are available at
https://github.com/SoroushVahidi/consistency-aware-llm-rankin.

Materials-availability statement:

Not applicable. This study does not generate new physical materials.

Author-contributions statement:

This is single-author work. Soroush Vahidi conceived the study, designed and
implemented the experimental pipeline, ran the experiments, analyzed and
verified the results, prepared the figures and tables, and wrote the
manuscript.

Generative-AI disclosure:

Anthropic Claude was used for software-development assistance, analysis and
audit utilities, figure preparation, and drafting and revising portions of the
manuscript. The author independently reviewed and verified all AI-assisted
code, analyses, figures, citations, and text against the source materials and
underlying evidence and assumes full responsibility for the work. No
generative-AI tool is credited as an author.

Acknowledgements:

The author thanks Professor Ioannis Koutis for his guidance and support,
Mitra Sharifani for her sustained personal support, and Anders Borum for
providing lifetime access to Secure ShellFish for the author's remote
research workflow.

Preprint disclosure:

An earlier, differently framed public preprint covering related themes was
posted on Research Square (DOI: 10.21203/rs.3.rs-9335700/v1; CC BY 4.0;
posted 2026-06-17) and was not peer-reviewed. That preprint is disclosed; it
is not an active journal submission. The present manuscript supersedes the
preprint’s retrieval interpretation where the revised exact and
multiplicity-corrected protocol changes the conclusion.

Repository URL:

https://github.com/SoroushVahidi/consistency-aware-llm-rankin

Archival release or DOI:

None available as of this audit. Repository is public. See
`RELEASE_CANDIDATE_PLAN.md` and `ARCHIVAL_RELEASE_PLAN.md` (DOI wait until
acceptance / explicit authorization).

Manuscript length (to be refreshed after freeze compile):

See `SUBMISSION_FREEZE_CHANGELOG.md` after the final clean build.

Required confirmation before final portal submission:

- Confirm the portal's exact article-type label if it differs from "Original
  Research."
- Confirm phone / structured funding IDs if the portal requires them.
- Confirm whether opposed reviewers or highlights must be entered.
- ORCID is verified and ready: https://orcid.org/0000-0003-1934-6282

## Cover Letter Text

Use the full letter in `COVER_LETTER.md` (synchronized 2026-08-02).

## Suggested Reviewers

Use the first six if the portal asks for six reviewers; keep Nihar B. Shah as
an alternate.

| Reviewer | Institution | Public email | Primary fit |
|---|---|---|---|
| Jimmy Lin | University of Waterloo | jimmylin@uwaterloo.ca | Information retrieval, reproducible retrieval infrastructure, neural/LLM ranking systems. |
| Julian Urbano | Delft University of Technology | j.urbano@tudelft.nl | IR statistical testing, multiple comparisons, empirical evaluation. |
| Nir Ailon | Technion - Israel Institute of Technology | nailon@cs.technion.ac.il | Rank aggregation, feedback arc set, pairwise-preference algorithms. |
| Sewoong Oh | University of Washington | sewoong@cs.washington.edu | Ranking from pairwise comparisons and statistical foundations of ranking. |
| David F. Gleich | Purdue University | dgleich@purdue.edu | Graph algorithms, PageRank, network analysis, reproducible scientific computing. |
| Michael D. Ekstrand | Drexel University | mdekstrand@drexel.edu | Recommender/search evaluation, reproducibility, and multiple testing. |
| Nihar B. Shah | Carnegie Mellon University | nihars@cs.cmu.edu | Pairwise comparisons, evaluation science, and controlled empirical evaluation. |

## Opposed Reviewers / Do Not Suggest

No formal opposed-reviewer request is necessary unless the portal requires one.
If it does, use the following conflict list:

| Person/entity | Reason |
|---|---|
| Professor Ioannis Koutis | Acknowledged for guidance and support; likely advisor/mentor conflict. |
| Anders Borum | Acknowledged for Secure ShellFish access; not an appropriate scientific reviewer. |
| Mitra Sharifani | Acknowledged for personal support; personal conflict. |
| Cohere Labs Catalyst Grant Program; Google Cloud Research Credits Program; Microsoft Azure for Students; AMD AI Developer Program; Fireworks AI | Listed only in the Funding declaration (in-kind computational / API-credit support for the real-LLM pilot); not repeated in Acknowledgments. |
| Guido Zuccon | Removed from the suggestion list during final audit because his current UQ profile also lists Google Research Australia, while the manuscript acknowledges Google Cloud Research Credits support. |
