# Stage 6 Whole-Manuscript Consistency Report

Date: 2026-07-31
Branch: `papers/sncs-2026-foundation`
Manuscript: `papers/SNCS_2026/manuscript/main.tex`

## Scope

Stage 6 polished the manuscript for SN Computer Science submission without
running new experiments, changing canonical numerical results, or adding new
scientific claims. The audit covered terminology, notation, cross-references,
figures, tables, declarations, abstract format, and source-to-PDF consistency.

## Journal Format

The SN Computer Science submission guidelines were rechecked from the official
Springer Nature journal page. The journal requires a structured abstract of
150--250 words with the sections Purpose, Methods, Results, and Conclusion.
The final abstract is 196 words and contains no citations, equations, figure
or table references, undefined notation, or repository-organization language.

## Consistency Checks

- Terminology is consistent around preference graphs, minimum-weight feedback
  arc set, exact repair, greedy repair, structural diagnostics, and retrieval
  effectiveness.
- Notation for query $q$, candidate set $D_q$, graph $G_q$, repaired graph
  $\widetilde{G}_q$, feedback arc set $F_q^\star$, pool size $P$, cutoff $k$,
  and nDCG is defined before use.
- Research questions RQ1--RQ4 are answered in the Conclusion in the same order
  as stated in Methodology.
- Dataset names are used consistently: SciDocs, FiQA, HotpotQA, and BRIGHT.
- Method names are consistent: BM25, TF-IDF, MiniLM, Reciprocal Rank Fusion,
  CombSUM, Copeland, balance, Markov, PageRank, Rank Centrality, and
  Bradley--Terry.
- The real-large-language-model pilot was corrected from "five providers" to
  "four providers," matching repository evidence.
- The external-validity limitation was corrected from "three classical and one
  dense base ranker" to "two lexical base rankers, one dense base ranker."
- The \texttt{ms2} cyclicity wording was softened from "by construction" to
  "in the observed evidence," avoiding a stronger-than-proven structural claim.
- Out-of-scope adjacent work is described only as learned policies for choosing
  when or how to invoke repair in a deployed system; no manuscript claim depends
  on a separate active-acquisition, CARB, policy-selection, or oracle-routing
  contribution.

## Cross-References

Automated source checks found:

- 65 labels, all unique.
- 161 `\ref`/`\eqref` uses, all resolved to existing labels.
- 59 cited bibliography keys, all present in `references.bib`.
- 62 BibTeX entries, all keys unique.
- 5 figures, 6 tables, and 1 algorithm; every one has a caption and label.

## Figures and Tables

Figure and table captions were inspected for self-containment and claim scope.
No figure or table required regeneration. Captions define or contextualize
abbreviations where needed, do not imply significance beyond the text, and keep
structural and retrieval conclusions separate.

## Statements and Declarations

Statements and Declarations now follow Springer-style order and wording:

- Funding.
- Competing interests.
- Ethics approval.
- Consent to participate.
- Consent for publication.
- Data, materials, and code availability.
- Authors' contributions.

The generative-AI disclosure remains in the Reproducibility and Implementation
section, consistent with the Stage 5 policy check that Springer Nature places
AI-use disclosure in Methods or an equivalent manuscript section rather than
as a separate backmatter declaration.

## Residual Notes

The manuscript compiles successfully to a 41-page PDF. Remaining TeX warnings
are underfull box diagnostics and a template/package UTF-8 warning from
`algorithm.sty`; no unresolved references or missing citations were detected.
