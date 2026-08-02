# Cold-Read Report

Date: 2026-08-01
Input read first: `manuscript/main.pdf` only.
PDF state read: 41 A4 pages, title through references.

## Verdict

The manuscript reads as a journal article rather than a repository report. The
central story is recoverable from the Abstract, Introduction, Results,
Discussion, and Conclusion, and the paper consistently separates the primary
score-derived canonical study from the six-query real-LLM supporting pilot.

No manuscript correction is required before submission on scientific clarity,
correctness, or compliance grounds.

## Must Fix Before Submission

None found.

## Recommended Improvement

1. The Methods section is dense around extraction methods, especially the
   distinction among Markov, Rank Centrality, PageRank, Bradley-Terry, and
   topological rules. It is accurate, but a first-time reader must work hard
   through Section 4.7 and Table 2. This is acceptable because the table
   immediately maps methods to comparison families and because trimming it
   would risk losing auditability.
2. The exact-repair details are more extensive than some SN Computer Science
   readers may need. However, the paper's central gap depends on exact repair
   as a diagnostic control, so the solver/formulation detail is justified.
3. Figure 1 is information-rich and caption-heavy. It is still interpretable
   and does useful work by making greedy and exact repair parallel branches.
4. The conclusion repeats RQ1-RQ4 explicitly. This is somewhat formal, but it
   helps a cold reader verify that the paper answered its stated questions.

No revision was made for these items because they are readability tradeoffs,
not clarity or correctness defects.

## Acceptable As Written

1. The title accurately emphasizes structural consistency versus retrieval
   utility and does not imply a new state-of-the-art reranker.
2. The structured abstract is self-contained, uses no undefined acronym before
   expansion except familiar ranker names, states the four public-benchmark
   scope, and frames exact repair as a methodological control rather than solver
   engineering.
3. The Introduction defines the problem, gap, method contribution, empirical
   result, exact-repair rationale, and non-claims before the related work.
4. The main empirical scope is consistently score-derived multi-ranker
   retrieval. The real-LLM pilot is described as bounded, directional, and
   supporting only.
5. Tables 1-6 are interpretable without external planning documents. Table 5's
   note is long, but it prevents over-reading dataset rows as retrieval-level
   significance claims.
6. The Results avoid treating cost, latency, or solver agreement as retrieval
   quality.
7. The Discussion and Limitations avoid overclaiming a proof of no effect or
   blanket practical equivalence.
8. The acknowledgments and declarations are professionally worded and do not
   include private details beyond the corresponding-author email required on the
   title page.

## Central Story Recheck

1. Problem studied: Whether repairing cycles in derived weighted
   preference graphs for multi-ranker retrieval improves downstream retrieval
   effectiveness, or only improves graph-internal structural consistency.
2. Exact research gap: Prior work often reports cyclicity or repair as a
   structural improvement, but does not cleanly test whether the repair
   objective predicts retrieval utility under explicit construction choices,
   unrepaired baselines, heuristic-vs-exact repair control, and
   multiplicity-corrected paired inference.
3. Main methodological contribution: A controlled empirical audit pipeline that
   separates graph construction, structural repair, ranking extraction, and
   retrieval evaluation, including exact SCIP-based MWFAS repair as a diagnostic
   control on heuristic suboptimality.
4. Central empirical result: Repair is structurally active and exact repair
   removes less contradictory edge weight than greedy repair, but no
   repaired-versus-unrepaired nDCG comparison survives Holm correction in the
   canonical, larger-pool, or exact-repair families.
5. Why exact repair is scientifically important: It rules out the alternative
   explanation that a null retrieval result merely reflects greedy
   under-repair. If certified-optimal repair still does not reveal a retrieval
   gain, the structural-to-utility gap is not explained by heuristic weakness.
6. What the paper does not claim: It does not claim state-of-the-art retrieval,
   a new MWFAS formulation or solver, that repair never helps, that exact repair
   universally fails, that LLM ranking is broadly settled by a six-query pilot,
   or that a per-query deployment rule for repair has been validated.

## Title and Abstract Audit

Existing title:

`Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit
of Preference-Graph Repair for Multi-Ranker Retrieval`

Assessment:

- Accurate: yes.
- Emphasizes structural consistency versus retrieval utility: yes.
- Avoids state-of-the-art implication: yes.
- Concise enough for indexing: acceptable. The title is long, but the running
  title is short and the full title encodes the paper's actual contribution.

No title change is recommended.

Structured abstract assessment:

- Self-contained: yes.
- Datasets/methods/findings accurate: yes, at the level appropriate for an
  abstract.
- Exact repair included without overemphasizing solver engineering: yes.
- Avoids unsupported generalization to LLM ranking: yes.
- Undefined acronym check: MWFAS is expanded before acronym use; nDCG is spelled
  out before acronym use; BM25, TF-IDF, MiniLM are method names and acceptable
  keywords in IR context.
- Word limit: prior workspace count records 196 words, within the stated
  150-250 word limit.

## Acknowledgments and Funding Audit

The manuscript acknowledgments include:

- Professor Ioannis Koutis for guidance and emotional support.
- The author's mother for emotional support.
- Anders Borum for lifetime access to Secure ShellFish.
- Cohere Labs Catalyst Grant Program.
- Google Cloud Research Credits Program.
- Microsoft Azure for Students.
- AMD AI Developer Program through Fireworks AI credits.

The Funding declaration mirrors the grant-like/in-kind API and cloud-credit
support and states that no direct financial grant funding was received. No
unsupported support source was found in the manuscript. Personal
acknowledgments remain professionally worded.

## External API Reporting Audit

Repository evidence confirms the real-LLM pilot provider/model identifiers:

- Azure OpenAI: configured model/deployment `gpt-4.1-mini` (reported in
  copy-ready form as GPT-4.1 mini).
- Google Gemini: configured model `gemini-2.5-flash` (Gemini 2.5 Flash).
- Cohere: configured model `command-r-plus-08-2024` (Command R+ 08-2024).
- Fireworks AI: configured model path `accounts/fireworks/models/gpt-oss-120b`
  (GPT-OSS-120B).

Transport detail: repository evidence in
`docs/experiments/provider_capability_summary_20260727.json` states
"Configured Vertex Gemini model gemini-2.5-flash; project/location redacted."
The implementation also supports direct Gemini API-key mode, but the tracked
provider capability metadata supports Vertex AI wording for the configured
Gemini evidence.

The manuscript itself does not over-specify provider transports. Provider calls
are described only as part of the bounded six-query supporting pilot, not the
primary canonical score-derived experiment.
