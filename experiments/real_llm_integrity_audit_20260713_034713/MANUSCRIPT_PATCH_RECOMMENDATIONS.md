# MANUSCRIPT_PATCH_RECOMMENDATIONS

No manuscript file was edited. Every number below is drawn from this audit's
CSVs; none are invented. Section/table numbers verified against
`papers/JDIQ_2026/manuscript/main.tex` on origin/main (commit `1635d4b`) by
counting `\section`/`\subsection`/`\begin{table}` environments in document
order (Section 4 = "Experimental Setup"; its 8th subsection,
`\label{sec:llm-config}`, is Section 4.8 and contains the 5th numbered table,
`\label{tab:llm-config}` = Table 5; Section 8 = "Bounded Real-LLM Validation").

---

## 1. Section 4.8 ("LLM Providers and Inference Configuration") intro paragraph

**Current** (`main.tex` ~line 833-845):
> "Table~\ref{tab:llm-config} summarizes the API-based runs that inform the
> manuscript. The primary paired evidence is an OpenAI pairwise pilot using
> \texttt{gpt-4o-mini}. Separate OpenAI pointwise and listwise runs are used
> only as auxiliary scope checks. The protocol-distinct corroborative corpus
> uses Cohere and Azure OpenAI pairwise judgments over a different method
> pair (repaired vs.\ unrepaired Markov), and is therefore not pooled with
> the primary pilot. The same experiment logs also record Gemini setup
> attempts, but the versioned failure-mining corpus used here contains no
> usable Gemini records, so Gemini is not treated as analyzed evidence in
> this revision."

**Recommended replacement:**
> "Table~\ref{tab:llm-config} summarizes the API-based runs that inform the
> manuscript. The primary paired evidence is an OpenAI pairwise pilot using
> \texttt{gpt-4o-mini}. Separate OpenAI pointwise and listwise runs are used
> only as auxiliary scope checks. Cohere and Azure OpenAI pairwise judgments
> were also collected, on a different method pair (repaired vs.\ unrepaired
> Markov) and query sample from the primary pilot; in the stored analysis
> pipeline, these judgments are recorded as an auxiliary per-query ranking
> comparison and do not feed the preference graph, cyclicity, or repair
> statistics reported for that corpus in Section~\ref{sec:real-llm} --
> those are computed from the same mechanical vote-extraction protocol as
> the main evaluation (Section~\ref{sec:vote-extraction}). We therefore do
> not describe that corpus as LLM-judgment-derived repair evidence. The same
> experiment logs also record Gemini setup attempts, but the versioned
> failure-mining corpus used here contains no usable Gemini records, so
> Gemini is not treated as analyzed evidence in this revision."

## 2. Table 5 (`tab:llm-config`) row descriptions

**Current:**
> `Cohere API & command-r-plus-08-2024 & Pairwise & Protocol-distinct corroborative corpus on FiQA, HotpotQA, and BRIGHT.`
> `Azure OpenAI & gpt-4.1-mini & Pairwise & Protocol-distinct corroborative corpus on FiQA, HotpotQA, and BRIGHT.`

**Recommended replacement** (role column only):
> `Cohere API & command-r-plus-08-2024 & Pairwise & Auxiliary per-query ranking comparison on FiQA, HotpotQA, and BRIGHT; not used to construct the repair/cyclicity statistics reported for that corpus.`
> `Azure OpenAI & gpt-4.1-mini & Pairwise & Auxiliary per-query ranking comparison on FiQA, HotpotQA, and BRIGHT; not used to construct the repair/cyclicity statistics reported for that corpus.`

## 3. Section 8 ("Bounded Real-LLM Validation") -- the 62/69/69 paragraph

**Current** (~line 1395-1410):
> "The protocol-distinct multi-provider corpus is directionally consistent
> with the same picture while broadening scope to BRIGHT and a second
> provider family. Across its 200 query-regime records, repair is inactive
> in all 62 \texttt{ms2} records and all 69
> \texttt{ms1\_drop\_mutual} records; in \texttt{ms1}, it yields one help
> case and one harm case among 69 records. Because that corpus compares
> repaired and unrepaired Markov rankings rather than the Copeland-hybrid
> pair summarized in Table~\ref{tab:real-llm-summary}, we use it only as
> corroborative scope evidence rather than as a pooled estimate."

**Recommended replacement** (numbers unchanged and independently re-verified
by this audit -- VALIDATION_CHECKS.md -- only the causal framing changes):
> "A second, 200-query-regime corpus spanning FiQA, HotpotQA, and BRIGHT
> broadens scope beyond the paired OpenAI pilot above. Its repair/cyclicity
> statistics are computed on the same mechanical vote-extraction protocol as
> the main evaluation (not from the Cohere/Azure judgments also collected
> alongside it; see Section~\ref{sec:llm-config}); repair is inactive in all
> 62 \texttt{ms2} records and all 69 \texttt{ms1\_drop\_mutual} records, and
> in \texttt{ms1} yields one help case and one harm case among 69 records --
> the same regime-conditional pattern as Sections~\ref{sec:structural-results}
> and~\ref{sec:downstream-results}. This corpus's separately-collected
> Cohere and Azure pairwise judgments were audited independently
> (post-hoc, from stored request/response logs) for order sensitivity: both
> models show a statistically significant preference for one candidate
> position over the other on every dataset tested (Azure: 53-58\% preference
> for the first-shown document; Cohere: 61-70\% preference for the
> second-shown document; exact binomial $p < 0.01$ in every case), and the
> the two directions of a debiased forward/reverse prompt pair agree with each
> other only 65-89\% of the time (Cohen's $\kappa$ 0.27-0.71 depending on
> provider and dataset). We report this as an open order-sensitivity
> limitation on any future use of these judgments as primary graph-
> construction input, not as a property of the mechanical-graph statistics
> above, which do not depend on them."

## 4. Parser description (new -- currently absent)

No sentence in the manuscript currently describes how a raw pairwise LLM
response is converted into a preference edge. Recommended addition, placed at
the end of Section 4.8:
> "Pairwise responses are parsed by taking the first character of the
> response if it is `A` or `B`, else the sole letter present if only one of
> `A`/`B` appears anywhere in the response; a response containing both
> letters, neither letter, or no text defaults to `A`. Across the 12,020
> Cohere/Azure responses with preserved raw text, this default triggered on
> 1.1\% of responses (0.0\% on FiQA, 0.5-3.8\% on BRIGHT/HotpotQA depending
> on provider); it never triggered for the primary OpenAI pilot's stored
> outputs, for which raw response text was not retained and cannot be
> re-audited."

## 5. Order-bias discussion (new -- currently absent)

No sentence currently reports whether position debiasing was measured to
work. Recommended addition, placed adjacent to item 3 above or as a
Section 8 footnote:
> "Position debiasing for the Cohere/Azure corpus queries both candidate
> orderings and requires unanimous agreement to overturn the first-shown
> document; on disagreement (21-41\% of pairs depending on provider/dataset)
> it defaults to the first-shown document rather than abstaining. An audit
> of the underlying request/response logs found that removing both this
> default and the parser's ambiguous-response default reduces measured
> cyclicity in a preference graph built directly from these judgments by
> 91-100\% across provider/dataset combinations (from 30-62\% cyclic down to
> 0-10\%), indicating most such cyclicity would reflect these defaults
> rather than genuine intransitive model preferences. This graph is not the
> one used for the repair statistics reported above."

## 6. Limitations, "Real-LLM scale" paragraph

**Current** (~line 1628-1636):
> "\textbf{Real-LLM scale.} Section~\ref{sec:real-llm}'s paired cross-dataset
> pilot uses 10--50 queries per dataset and a single provider. We also
> analyze a separate 200-record multi-provider failure-mining corpus with
> Cohere/Azure judgments and BRIGHT coverage, but that corpus uses a
> different method pair, query sample, and protocol. Together these streams
> are sufficient to show that the main decoupling pattern is not obviously
> confined to one provider or to the mechanical-vote setting, but not
> sufficient to establish how it behaves under LLM judgments in general."

**Recommended replacement:**
> "\textbf{Real-LLM scale.} Section~\ref{sec:real-llm}'s paired cross-dataset
> pilot uses 10--50 queries per dataset and a single provider, and its raw
> response text was not retained, so its parsing cannot be independently
> re-audited from stored artifacts. We also collected a separate 200-record
> multi-provider (Cohere/Azure) pairwise-judgment set on FiQA, HotpotQA, and
> BRIGHT; its repair/cyclicity statistics (Section~\ref{sec:real-llm}) are
> computed on the same mechanical vote-extraction protocol as the main
> evaluation, not on these judgments, so it does not extend the primary
> pilot's provider coverage for the repair/cyclicity claim. The Cohere/Azure
> judgments themselves show provider-dependent, statistically significant
> position bias and 21-41\% forward/reverse disagreement (Section~\ref{sec:real-llm}),
> which would need to be resolved (e.g., by abstaining on disagreement rather
> than defaulting) before they could support a graph-construction-level
> LLM-judgment claim in a future revision. No claim in this paper currently
> depends on that resolution."

## 7. Data Availability

**Current** (~line 1767-1770):
> "\textbf{Reproducibility.} ... The real-LLM summaries likewise depend on
> stored API outputs, but a full rerun of those experiments would require
> commercial API access and may not be exactly reproducible if provider-side
> models change over time."

**Recommended addition** (append a sentence):
> "Reproducibility of the real-LLM summaries is asymmetric across providers:
> the OpenAI primary pilot's stored outputs retain only parsed winner/loser
> pairs, not raw response text, so its parsing choices cannot be
> independently re-audited or re-parsed under an alternative policy from
> stored artifacts alone. The Cohere/Azure corpus retains raw prompt and
> response text for 54.6\% of pairwise-direction calls (the remainder are
> within-run cache hits that only recorded the parsed outcome), which is
> sufficient to support the order-sensitivity and alternative-parsing audit
> summarized in Section~\ref{sec:real-llm} but not a full re-parse of every
> stored judgment."
