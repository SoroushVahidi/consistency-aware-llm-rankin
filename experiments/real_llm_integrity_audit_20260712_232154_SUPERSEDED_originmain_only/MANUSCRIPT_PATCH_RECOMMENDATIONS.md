# MANUSCRIPT_PATCH_RECOMMENDATIONS

## Section 4.8 / real-LLM scope paragraph

Replace the current paragraph that introduces the primary OpenAI pilot and the separate Cohere/Azure failure-mining corpus with:

> In addition to the mechanical three-ranker evaluation described above, we analyze a bounded sample of stored real large-language-model outputs. The auditable primary evidence is an OpenAI pairwise pilot using \texttt{gpt-4o-mini} on SciDocs (50 queries), HotpotQA (20 queries), and FiQA (10 usable queries from a 20-query target). Separate OpenAI pointwise and listwise runs on SciDocs and HotpotQA are used only as auxiliary scope checks. A quota-limited Gemini pilot exists for two SciDocs queries, but we do not treat it as analyzed evidence. We keep these API-based runs separate from the main mechanical-vote evaluation and treat them as bounded corroborative checks rather than scale-matched confirmatory evidence.

## Table 5

Replace the current four-row provider table with:

> OpenAI API | \texttt{gpt-4o-mini} | Pairwise | Primary paired pilot on SciDocs, HotpotQA, and FiQA. \\
> OpenAI API | \texttt{gpt-4o-mini} | Pointwise / listwise | Auxiliary scope check on SciDocs and HotpotQA. \\

Optional footnote below the table:

> A quota-limited Gemini pilot on two SciDocs queries is documented in the stored artifacts but is not treated as analyzed evidence here.

## Parser description

Replace the current parser sentence block with:

> The auditable OpenAI pairwise pilot uses top-$k=15$ candidate pools, seed 42, no candidate-order debiasing, and pairwise responses prompted as one-letter A/B judgments with up to four retries and exponential backoff on transient API failures. The pairwise parser accepts leading `A` or `B`, then falls back to presence-based matching, and otherwise defaults to `A`. Because the committed cache preserves only final winner/loser records rather than raw response text, ambiguity and fallback frequencies cannot be reconstructed retrospectively from the current artifact snapshot.

## Order-bias discussion

Replace any sentence claiming that the analyzed corroborative corpus used symmetric A$\rightarrow$B and B$\rightarrow$A prompting with:

> The committed primary-pairwise artifacts do not use candidate-order debiasing (`debias\_position=false`), and no auditable forward/reverse paired-prompt corpus is available in the current anonymous snapshot. We therefore treat order sensitivity as an unresolved limitation rather than a quantified result in this revision.

## Section 8 real-LLM results

Replace the current opening and corroborative-corpus paragraphs with:

> The bounded real-LLM evidence in this revision is the stored OpenAI pairwise pilot on SciDocs, HotpotQA, and FiQA. Cyclic-query prevalence is 92.0\% on SciDocs (46/50), 80.0\% on HotpotQA (16/20), and 10.0\% on FiQA (1/10). Repaired-versus-unrepaired Copeland-hybrid $\Delta$nDCG remains small: SciDocs shows a negative mean difference of $-0.0010$ with 95\% bootstrap CI $[-0.0019, -0.0002]$, while HotpotQA and FiQA are exactly zero in the stored summaries. We interpret these runs as bounded corroborative evidence that real LLM preferences can still produce substantial cyclicity without demonstrating a general retrieval-quality benefit from repair.

If a Gemini sentence is desired:

> A partial Gemini pilot on two SciDocs queries is archived, but its scale is too limited for manuscript-level inference.

## Limitations

Insert:

> The committed real-LLM artifacts preserve final pairwise winner/loser records but not the underlying raw pairwise response texts. As a result, ambiguity rates, fallback-to-`A` frequency, and alternative ambiguity-sensitive reparsing policies cannot be audited retrospectively from the current anonymous repository snapshot.

Also insert:

> Earlier draft text referred to a separate Cohere/Azure corroborative corpus, but no committed auditable version of that corpus is present in the current anonymous snapshot; we therefore do not rely on it here.

## Data Availability

Replace any sentence implying that all real-LLM parsing details are reconstructible from stored outputs with:

> Stored API-derived outputs are sufficient to reproduce the committed OpenAI pairwise query-level summaries, final judgment graphs, and downstream repaired-versus-unrepaired comparisons reported here. They are not sufficient to reconstruct the original pairwise response texts or to rerun ambiguity-sensitive parser audits without additional logs outside the current anonymous snapshot.
