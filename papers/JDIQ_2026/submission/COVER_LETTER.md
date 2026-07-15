# Cover Letter — JDIQ Submission

> Drafted for repository record-keeping only; not submitted anywhere by this
> process. Fill in the bracketed placeholders (`[...]`) with real author
> names, affiliations, ORCID iDs, and contact details before actual
> submission — none of that identifying information exists in this
> anonymized repository, and none has been invented here. Convert to the
> editorial system's required format (plain text or PDF letterhead) at
> submission time.

---

[Corresponding Author Name]
[Affiliation]
[Email]
[Date]

Editor-in-Chief
ACM Journal of Data and Information Quality (JDIQ)

Dear Editor,

We are pleased to submit our manuscript, "Data Quality for Derived
Preference Graphs: Construction Sensitivity and Repair Outcomes in
Multi-Ranker Retrieval," for consideration for publication in the ACM
Journal of Data and Information Quality.

**Motivation.** Multi-ranker retrieval systems routinely combine
heterogeneous rankers — sparse retrievers, dense retrievers, and other
learned components — into a single preference structure, and a growing
body of work proposes repairing cyclic inconsistency in that structure
before extracting a final ranking. This practice implicitly assumes the
preference graph itself is a trustworthy artifact. We show that assumption
is often false: a preference graph is a *derived data artifact* whose
cyclicity, edge weights, and repair outcomes are governed as much by upstream
score-normalization and vote-construction choices as by the retrieval
signal they are meant to represent. Data-quality problems in the graph's
construction pipeline can manufacture the very inconsistency a repair step
is then credited with fixing.

**Contribution.** The central contribution is a reproducible audit
methodology for preference graphs as derived data artifacts: a precise
definition of the audited object, an operational seven-dimension
data-quality taxonomy spanning provenance, calibration, vote semantics,
conflict structure, repair quality, downstream utility, and
reproducibility, and a decision rule separating construction artifact from
genuine evidence conflict. Applying that methodology across four retrieval
benchmarks (SciDocs, FiQA, HotpotQA, BRIGHT) and three vote-extraction
regimes, we show that raw, unnormalized ranker score margins produce severe
single-ranker dominance (BM25 accounted for essentially all edge weight
whenever it participated), and that normalizing this away materially
changes retained votes, edge weights, cyclicity, and several
repaired-versus-unrepaired retrieval signs. Under our primary normalized
protocol, feedback-arc-set repair remains structurally active but produces
no repaired-versus-unrepaired retrieval effect that survives paired
permutation testing, bootstrap uncertainty, leave-one-out influence
analysis, and Holm/Benjamini-Hochberg multiplicity correction — including
under an exact (provably-optimal) repair solver, not only a greedy
heuristic — and we show this null result is itself robust, surviving a
joint multiplicity correction across independently-defined normalization
protocols, independently-constructed candidate pools, and additional
graph-ranking baselines (PageRank, RankCentrality, Bradley-Terry, and a
Markov hybrid), rather than holding only under one convenient pipeline
configuration. A genuine pool-size-versus-cutoff evaluation ($P>k$) confirms
that repair can change top-$k$ membership even when it does not move nDCG,
and a power/minimum-detectable-effect analysis contextualizes that null
result rather than treating it as unqualified equivalence.

**Relevance to JDIQ.** Every headline empirical result in the paper is
mapped onto one dimension of the taxonomy above, so the results are
evidence for a reusable audit methodology, not an unconnected list of IR
sensitivity findings. We apply an intrinsic/contextual data-quality framing
directly to preference graphs: cyclicity, mutual-pair prevalence, and
removed-edge weight are intrinsic properties of the constructed artifact,
auditable independently of any downstream task, while nDCG and
qrels-anchored diagnostics describe the artifact's fitness for a specific
retrieval task. We believe this framing — and the general lesson that any
pipeline converting heterogeneous signals into a derived structure
(preference graphs, LLM-as-judge comparisons, learned fusion inputs) needs
its construction choices measured and reported as a first-class part of the
method — is a natural fit for JDIQ's scope.

**Reproducibility and artifact availability.** Every quantitative claim in
the manuscript traces to a versioned script, a generated table, and a
machine-readable manifest recording protocol identifiers, thresholds,
random seeds, and solver configuration; none of the reported numbers were
computed once and transcribed by hand. The full pipeline — canonical
aggregate ranker-comparison tables, candidate-pool policies,
normalization/threshold protocols, the exact (SCIP-based, open-source, no
commercial solver dependency) and greedy repair implementations, and all
statistical analysis code — is packaged as an anonymized artifact and
attached through the venue submission system alongside this manuscript; a
public, author-identified repository will be made available upon
acceptance.

**Ethical considerations.** This study uses only publicly available
retrieval benchmarks (SciDocs, FiQA, HotpotQA, BRIGHT) and their standard
relevance judgments; it involves no human subjects, no personally
identifiable information, and no proprietary or restricted data. The
paper's limited use of large-language-model outputs is confined to a
bounded protocol-quality check on already-stored judgments (Section
"Real-LLM Evidence: Scope and Role") and is explicitly not presented as
independent validation of the paper's primary mechanical-pipeline findings.

**Prior versions.** [State here, if applicable: whether this manuscript or
a substantially similar version has been submitted elsewhere, presented at
a workshop, posted as a preprint, or is a revision of a prior submission
to this or another venue. Leave this paragraph accurate and complete before
submission — do not submit a paper with undisclosed prior/overlapping
publication. Note for the author completing this placeholder: a
substantially earlier, differently-framed version of this manuscript's
underlying study was submitted to and rejected (not published, no overlap
obligation in ACM's 30%-new-content sense, which applies to prior
*publications*) by other venues before this JDIQ submission; state that
history here in whatever form is accurate and appropriate if the venue's
process calls for it, rather than leaving this paragraph blank by
oversight. **Important, verified in Task 9:** the earlier-titled version
of this manuscript ("Consistency-Aware Reranking via Preference Graph
Repair: Structural Gains and Conditional Retrieval Effects") was
automatically posted as a public preprint on Research Square via Springer
Nature's "In Review" service when it was submitted to the Iran Journal of
Computer Science (RSID rs-9335700), and remains live and publicly
searchable under the real author's name as of this writing. This is a
genuine double-anonymous-review risk independent of anything fixable in
the manuscript source: a reviewer who searches distinctive phrases from
this submission could locate that preprint. Disclose its existence
honestly here if the venue's process asks about preprints, and separately
decide (this is a decision only the author can make, not something this
revision process can resolve) whether to request its withdrawal from
Research Square, rely on JDIQ's own preprint policy (verify this directly;
not confirmed in this revision sequence), or accept the residual risk.]

**Suggested reviewers / conflicts of interest.** [Add if the venue
requests suggested or excluded reviewers; none are proposed in this draft.]

We believe this manuscript will be of interest to JDIQ's readership working
on data quality for derived and algorithmically-constructed artifacts,
retrieval fusion, and reproducible evaluation methodology, and we thank the
editorial team for considering it.

Sincerely,

[Corresponding Author Name]
on behalf of all authors
