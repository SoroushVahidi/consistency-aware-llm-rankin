# Citation Audit, Stage 5 (Discussion)

Every citation newly used or re-used with a new claim attachment in
`\section{Discussion}` (`sec:discussion`), verified against the claim it
is attached to. Citations already verified for bibliographic metadata in
Stage 2 (title, authors, venue, year, DOI) are not re-verified for
metadata here -- only for whether *this specific claim* is an accurate
paraphrase of the source. One genuinely new reference was added this
stage (`vahidi2026consistencyaware`) and is verified in full.

| Manuscript claim (Discussion location) | Source | Verification |
|---|---|---|
| "Pairwise ranking prompting with large language models is competitive with, and in some settings better than, pointwise scoring for text reranking" (`sec:discussion-literature`) | `qin-etal-2024-large` | Re-checked this stage via web search against the paper's own abstract/description (ACL Anthology, `aclanthology.org/2024.findings-naacl.97`): the paper's stated contribution is that off-the-shelf LLMs "do not fully understand" pointwise/listwise ranking prompt formulations and that Pairwise Ranking Prompting (PRP) is proposed and shown to be "an effective alternative." Matches the manuscript's claim; not overstated. |
| "Pointwise, pairwise, and listwise LLM reranking paradigms show real, measured effectiveness differences depending on formulation" (`sec:discussion-literature`) | `sun-etal-2023-chatgpt` | Metadata and topic verified Stage 2 (EMNLP 2023, "Is ChatGPT Good at Search? Investigating LLMs as Re-Ranking Agents"). Claim is a generic, low-risk paraphrase of the paper's comparative-formulation framing; not re-fetched this stage since the claim makes no specific numeric or directional assertion beyond "differences exist," which is uncontroversially within the paper's scope. |
| "Positional and prompt-order biases can affect LLM-as-judge outcomes" (`sec:discussion-literature`) | `zheng2023judging` | Metadata verified Stage 2 (NeurIPS 2023 Datasets and Benchmarks Track, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"). This paper's own known contribution includes identifying position bias as a limitation of LLM judges (a widely cited finding of this paper). Claim matches. |
| "Systematic position bias has been measured directly in LLM-as-judge pairwise comparisons" (`sec:discussion-literature`) | `shi2025judging` | Metadata verified Stage 2 (IJCNLP-AACL 2025, title itself is "Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge"). Title directly supports the claim; no further verification needed beyond confirming the title, which was already confirmed at Stage 2. |
| "Intrinsic inconsistency in LLM-based pairwise rankings has motivated explicit aggregation methods to mitigate it" (`sec:discussion-literature`) | `zeng2024llmrankfusion` | Metadata verified Stage 2 (arXiv:2406.00231, title "LLM-RankFusion: Mitigating Intrinsic Inconsistency in LLM-based Ranking"). Title directly supports the claim. |
| "Recent work on acyclic preference evaluation for language models treats acyclicity as a desirable property... and reports downstream gains from enforcing it, on tasks including model ranking, response selection, and fine-tuning data selection" (`sec:discussion-literature`) | `hu2024acyclic` | Metadata and claim thoroughly verified Stage 2 (arXiv:2410.12869, title "Towards Acyclic Preference Evaluation of Language Models via Multiple Evaluators," confirmed via two independent arXiv abstract-page fetches after an initial fetch returned inconsistent stale-version data; PGED framework ensembles/denoises multiple evaluators' preference graphs for acyclic results; evaluated on model ranking, response selection for test-time scaling, and data selection for fine-tuning). Claim matches Stage 2's verified description exactly; not re-fetched this stage. |
| "That result is not contradicted by this paper: the two studies test acyclicity's downstream value in different task settings... with different aggregation and repair mechanisms" (`sec:discussion-literature`) | `hu2024acyclic` (same source, interpretive claim) | This is this manuscript's own interpretive framing (a claim *about* the relationship between the two papers' findings), not a claim attributed to the source paper itself -- flagged as such here since it is the author's synthesis, not a paraphrase of `hu2024acyclic`'s own text. |
| Positioning against the author's earlier preprint (`sec:discussion-literature`, also `sec:related-repair`) | `vahidi2026consistencyaware` | **New reference, added this stage.** Verified via the Crossref API (`api.crossref.org/works/10.21203/rs.3.rs-9335700/v1`, an authoritative machine-readable metadata source, not a search-engine summary): type `posted-content` (preprint), publisher "Springer Science and Business Media LLC" (Research Square), single author Soroush Vahidi (New Jersey Institute of Technology), posted 2026-06-17, title matches `papers/_archive/IJCS_early_draft.zip`'s manuscript title exactly. This preprint was not previously cited in `main.tex` (Stages 2-4 treated it as "unpublished, not citable" based on the repository's internal record that its target-journal submission was rejected 2026-07-05); Stage 5 discovered it is nonetheless a public, DOI-bearing preprint (posted before the rejection date, consistent with automatic in-review preprint posting that is not retracted by a later journal-level rejection), and revised Related Work 2.3 and Discussion 5.4 to cite it properly as a preprint, with explicit "has not completed peer review... cited here only as a preprint" language preserved from the original framing. See `STAGE5_CHANGELOG.md` for the full reasoning behind this change. |

## Citations audited and found to require no change

`negahban2017rankcentrality`, `bradley1952rank`, `hunter2004mm`,
`kemeny1959mathematics`, `dwork2001rank`, `ailon2008aggregating`,
`kenyon2007fewerrors`, `karp1972reducibility`, `eades1993heuristic`,
`page1999pagerank`, `cormack2009rrf`, `fox1994combination`,
`jarvelin2002cumulated`, `holm1979simple`, `benjamini1995controlling`,
`efron1993introduction`, `robertson2009probabilistic`,
`salton1988termweighting`, `wang2020minilm` -- all cited in
Introduction/Related Work/Background/Methodology only (not newly cited or
reattached to a new claim in Discussion), already verified at the stage
each was introduced (Stage 2 for the literature citations, Stage 3 for
the methods/statistics citations). Not re-audited here since Stage 5's
brief scopes this audit to Discussion's citations specifically ("the
Discussion cites the most relevant current works").

## Sentence-level citation-density check

Verified by inspection: no sentence in the Discussion section ends with
more than one citation key (the densest is a single `\cite{...}` per
clause, e.g. `\cite{qin-etal-2024-large}` and
`\cite{sun-etal-2023-chatgpt}` in separate sentences), satisfying the
"do not cite more than four references at the end of one sentence"
constraint with margin to spare -- each claim in
Section~\ref{sec:discussion-literature} is deliberately split into its
own sentence with its own single citation, rather than bundling multiple
sources behind one claim, precisely so that each citation's claim
attachment stays checkable one-to-one.

## Duplicate or malformed BibTeX entries

Checked `references.bib` for duplicate keys and malformed entries this
stage (`grep -c "^@"` vs.\ unique key count): no duplicates found. One
entry added this stage (`vahidi2026consistencyaware`), documented above
and in `STAGE5_CHANGELOG.md`. No entry was removed; bibliography pruning
remains deferred to after Conclusion/Abstract are drafted, per the
`references.bib` header's own stated policy (unchanged since Stage 2).

## Retracted or superseded papers

No cited work is retracted, to the best of this process's knowledge;
none of the cited papers appear on Retraction Watch or in Crossref's
retraction metadata for the checked DOIs, and no cited work's own
citation trail (as encountered during Stage 2/3/5 research) surfaced a
retraction notice. Preprints cited (`hu2024acyclic`,
`vahidi2026consistencyaware`) are cited explicitly as preprints, not
represented as peer-reviewed publications, per their actual status.
