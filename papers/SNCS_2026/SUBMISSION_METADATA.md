# Submission Metadata

Date: 2026-08-01
Target journal: SN Computer Science

## Copy-Ready Fields

Manuscript title:

Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit
of Preference-Graph Repair for Multi-Ranker Retrieval

Running title:

Structural Consistency Is Not Retrieval Utility

Article type:

Original Research

Abstract:

Purpose: Preference-graph repair is often treated as if restoring acyclicity should improve ranking quality. This study asks whether, for score-derived multi-ranker retrieval graphs, heuristic or exact minimum-weight feedback-arc-set repair yields a multiplicity-corrected retrieval gain -- or whether structural consistency and retrieval utility must be reported as separate claims.

Methods: On four public benchmarks, query-level preference graphs were built from stored BM25, TF-IDF, and MiniLM scores under three vote-construction regimes. Rankings from unrepaired, greedy-repaired, and exactly repaired graphs were compared with paired sign-flip tests and Holm correction. Exact SCIP solutions served as a diagnostic control on heuristic under-repair, not as a production solver.

Results: Construction dominated structure: a conservative regime was acyclic throughout, while a permissive regime was cyclic for most queries; normalizing scores reduced BM25's conditional edge-weight share from 0.988 to 0.512. Repair removed non-trivial contradictory weight and, pooled across vote regimes when the pool exceeded the cutoff, changed top-k membership by 10.6% on average, yet no repaired-versus-unrepaired normalized discounted cumulative gain (nDCG) comparison survived Holm correction in the canonical, larger-pool, or exact-repair families. Graph-free fusion was competitive (CombSUM 0.554 versus 0.546 for the best repaired hybrid). Exact repair removed less weight than greedy repair yet still yielded no corrected retrieval gain.

Conclusion: Under this protocol, preference-graph repair is a real structural intervention but not a validated nDCG optimization step. Improving the repair objective -- even to certified optimality -- does not substitute for downstream evaluation; treat acyclicity metrics as structural diagnostics, not as proxies for retrieval utility.

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

Funding statement:

This work received computational support through the Cohere Labs Catalyst Grant
Program, the Google Cloud Research Credits Program, Microsoft Azure for
Students, and Fireworks AI credits provided through the AMD AI Developer
Program. The funders had no role in the study design, data analysis,
interpretation of results, or preparation of the manuscript.

Competing-interests statement:

The author declares no competing interests.

Data-availability statement:

The datasets used in this study are publicly available from their original
sources and are cited in the manuscript. No new benchmark dataset was generated.
The code and processed artifacts used to generate the reported results are
available at https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Raw
provider request and response payloads from the bounded large-language-model
pilot are not included in the repository for the reasons stated in the
manuscript.

Code-availability statement:

The code, fixed query lists, processed intermediates, figure data, and scripts
required to reproduce the reported tables and figures are available at
https://github.com/SoroushVahidi/consistency-aware-llm-rankin.

Ethics approval:

Not applicable. This study uses only publicly available benchmark datasets and
stored, derived score files; it involves no human subjects, no personal or
identifiable data, and no new data collection from human participants.

Consent to participate:

Not applicable; no human participants were involved in this study.

Consent for publication:

Not applicable; no individual person's data are presented in this manuscript.

Generative-AI disclosure:

Generative artificial-intelligence tools (Anthropic's Claude, via the Claude
Code command-line environment) were used to assist with software development for
this study - writing and revising analysis code, statistical-inference
utilities, figure-generation scripts, and audit scripts - and with drafting,
revising, and fact-checking portions of this manuscript's text and figures.
Every AI-assisted code change, statistical analysis, figure, table, citation,
and passage of manuscript text was reviewed and independently verified against
the underlying stored data and source code by the author before inclusion; no
generative-AI output was accepted without that verification. The author takes
full responsibility for the accuracy, integrity, and originality of the source
code, experiments, statistical analyses, figures, tables, interpretations,
citations, and manuscript text in this work. No generative-AI tool is credited
as an author, and no generative-AI tool independently designed the study,
selected the research questions, or made scientific judgments attributed to the
author in this manuscript.

Acknowledgements:

The author thanks Professor Ioannis Koutis for his guidance and emotional
support, his mother for her sustained emotional support, and Anders Borum for
providing lifetime access to Secure ShellFish.

Repository URL:

https://github.com/SoroushVahidi/consistency-aware-llm-rankin

Archival release or DOI:

None available as of this audit. Repository is public. See
`RELEASE_CANDIDATE_PLAN.md` and `ARCHIVAL_RELEASE_PLAN.md` (DOI wait until
acceptance / explicit authorization).

Required confirmation before final portal submission:

- Confirm the portal's exact article-type label if it differs from "Original
  Research."
- Confirm ORCID / phone / structured funding IDs if the portal requires them.
- Confirm whether opposed reviewers or highlights must be entered.

## Cover Letter Text

Dear Editor-in-Chief,

Please consider the manuscript "Structural Consistency Is Not Retrieval Utility:
An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker
Retrieval" for publication as an Original Research article in SN Computer
Science.

The manuscript studies a common assumption in graph-based ranking pipelines:
that repairing cycles in a derived preference graph should improve the
downstream retrieval ranking. Using four public retrieval benchmarks, three
score-derived rankers, three graph-construction regimes, and paired query-level
inference with Holm correction, the paper separates graph construction,
structural repair, ranking extraction, and retrieval evaluation. It also uses
exact SCIP-based minimum-weight feedback-arc-set repair as a methodological
control on heuristic repair.

The central finding is deliberately restrained. Repair is structurally active
and exact repair removes less edge weight than greedy repair, but no
repaired-versus-unrepaired nDCG comparison survives Holm correction in the
canonical, larger-pool, or exact-repair comparison families. The paper therefore
argues that structural consistency and retrieval utility should be reported as
separate quality dimensions.

The manuscript is appropriate for SN Computer Science because it combines
information retrieval, graph algorithms, empirical evaluation methodology, and
reproducible computational experimentation, all within the journal's broad
computer science scope. The contribution is a controlled empirical audit rather
than a claim of state-of-the-art reranking performance.

I confirm that the work is original, has not been published before, and is not
under consideration elsewhere. The code, fixed query lists, processed
intermediates, figure data, and scripts required to reproduce the reported
tables and figures are available at
https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Raw provider
request and response payloads from the bounded LLM pilot are excluded for
artifact-policy reasons, as stated in the manuscript.

Thank you for considering this submission.

Sincerely,

Soroush Vahidi

Ying Wu College of Computing

New Jersey Institute of Technology

sv96@njit.edu

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
| Professor Ioannis Koutis | Acknowledged for guidance and emotional support; likely advisor/mentor conflict. |
| Anders Borum | Acknowledged for Secure ShellFish access; not an appropriate scientific reviewer. |
| The author's mother | Acknowledged for emotional support; personal conflict. |
| Cohere Labs Catalyst Grant Program; Google Cloud Research Credits Program; Microsoft Azure for Students; AMD AI Developer Program; Fireworks AI | Listed only in the Funding declaration (computational / API-credit support); not repeated in Acknowledgments. |
| Guido Zuccon | Removed from the suggestion list during final audit because his current UQ profile also lists Google Research Australia, while the manuscript acknowledges Google Cloud Research Credits support. |
