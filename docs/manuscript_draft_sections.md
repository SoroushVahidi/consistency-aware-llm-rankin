# Manuscript Draft Sections

> **Purpose:** Journal-ready draft prose for three manuscript sections, derived
> from `docs/revision_strategy.md`, `docs/safe_claims.md`, and
> `docs/related_work_positioning_note.md`. All claims are grounded in
> committed experimental artifacts; the pre-submission evidence-check
> note at the end lists every sentence that should be verified against
> repository outputs before final submission.
>
> **Style rules applied:** professional journal tone; no bullet lists in
> manuscript prose; no "state of the art"; no "novel" without direct
> justification; no internal file-path references; pending baselines
> clearly separated from completed evidence.

---

## Section 1 — Related Work

### Reranking from pairwise preferences: neural, LLM-based, and aggregation approaches

Neural reranking methods that score each query-document pair jointly —
commonly termed cross-encoders — form an established class of reranking
systems. These models, typically fine-tuned on large-scale passage-relevance
collections such as MS MARCO (Bajaj et al., 2018), produce a scalar relevance
score for each candidate document and rank by those scores (Nogueira & Cho,
2019; Nogueira et al., 2020). Because cross-encoders operate on document text
independently of other candidates, they do not produce or consume pairwise
preference signals and therefore operate at a different stage of the ranking
pipeline than the methods studied here. We include a representative pre-trained
cross-encoder as an external reference baseline in order to anchor our
results within the broader reranking literature.

Recent work has applied large language models (LLMs) as ranking agents across
three broad paradigms. In pointwise reranking, an LLM is prompted to assess
the relevance of each document independently and produce a relevance score or
label; documents are then ordered by those scores (Liang et al., 2022; Zhuang
et al., 2023). In pairwise reranking, sometimes termed Pairwise Ranking
Prompting (PRP), the LLM is prompted to compare two documents and declare a
preference, with all pairwise outcomes subsequently aggregated into a ranking
(Qin et al., 2023). In listwise reranking, the LLM is presented with a window
of candidate documents and asked to output a reordered permutation directly;
RankGPT (Sun et al., 2023) and related systems (Ma et al., 2023; Pradeep et
al., 2023) are representative examples of this approach. Each of these
paradigms produces a ranking from text using a single model and does not
address consistency constraints that arise within multi-ranker preference
aggregation. We have implemented representative systems for each of the three
LLM-based paradigms; however, their quantitative evaluation requires LLM API
access that was unavailable during the experimental period reported here, and
that evaluation is therefore deferred to future work.

A parallel and theoretically well-grounded line of work treats any collection
of pairwise comparison outcomes — regardless of whether they originate from
human judgements, retrieval scores, or LLM prompts — as tournament data and
aggregates them using social-choice or statistical methods. Condorcet-based
scoring (Copeland, 1951), Borda count, Markov-chain rank aggregation (Dwork
et al., 2001), and the Bradley–Terry paired-comparison model (Bradley & Terry,
1952) constitute foundational contributions in this area. Spectral estimation
methods (Ammar et al., 2016) and, more recently, aggregation of LLM-generated
pairwise preferences (Zhu et al., 2023; Jiang et al., 2023) have extended this
framework. The present work contributes to this class of methods by examining
a structural property of the preference graph that standard aggregation
procedures do not model: the presence of directed cycles arising from
inconsistent pairwise votes. We formulate cycle removal as a minimum-weight
feedback arc set problem, apply a greedy repair procedure before ranking
extraction, and empirically characterise the conditions under which this
step affects retrieval quality. The primary question is not which aggregation
formula performs best on clean, acyclic preference data, but rather how
structural inconsistency in the preference graph interacts with downstream
ranking quality and whether explicit repair can improve outcomes.

---

## Section 2 — Baselines and Experimental Setup

### Baseline suite

The evaluation includes two categories of baseline methods, distinguished by
their execution status.

The first category comprises baselines for which complete experimental results
are available. As an external reference representing text-aware neural
reranking, we evaluate a pre-trained cross-encoder (ms-marco-MiniLM-L-6-v2)
that scores each query-document pair from document text alone. To represent
the graph and tournament aggregation paradigm, we evaluate Bradley–Terry
maximum-likelihood estimation (via the MM algorithm), win-rate aggregation,
Markov-chain aggregation (stationary distribution of the pairwise-preference
random walk), and tournament sort. These methods consume the same pairwise
preference graphs as our approach but perform no cycle-detection or repair
step. The classical ranking methods Copeland scoring, Borda count, and
score-sum are also evaluated as internal comparators representing the original
submission's baseline suite.

The second category comprises LLM-based reranking baselines — pointwise
scoring, pairwise ranking prompting (Qin et al., 2023), and listwise
permutation reranking (Sun et al., 2023) — which have been implemented but
are not included in the quantitative comparison reported here. Their
evaluation requires LLM API access that was unavailable during the
experimental period; their role within the evaluation framework is discussed
in the Limitations section.

### Vote construction and preference graphs

Pairwise preference votes are constructed from a three-ranker ensemble
consisting of BM25, TF-IDF, and MiniLM-L6. We evaluate three vote-construction
strategies that produce graphs with qualitatively different structural
properties. Majority-filtered aggregation (requiring support from at least
two rankers with a minimum score margin) yields near-acyclic graphs on all
four evaluation datasets. Per-ranker inclusion without filtering produces
graphs with high cyclicity — for example, 87.5% of queries on SciDocs exhibit
at least one directed cycle under this construction, with an average largest
strongly connected component of 9.3 nodes. A third variant applies a mutual
2-cycle filter as a post-processing step, restoring near-acyclicity while
retaining more preference edges than the majority-filtered construction. These
three regimes provide the basis for the regime analysis in the Results section.

### Datasets

The modern-baseline comparison is conducted on three datasets: SciDocs (500
queries), HotpotQA (497 queries), and BRIGHT (71 queries). FiQA is included
in the structural-metrics and repair-effect analyses but excluded from the
modern-baseline ranking comparison because its relevance judgements are
limited to a single graded tier, which does not support meaningful ranking
differentiation within the candidate pool used here.

### Noise injection and robustness analysis

To assess method robustness under imperfect pairwise signals, synthetic
preference noise is injected by randomly flipping a specified proportion of
pairwise comparisons. Flip probabilities range from 5% to 30%. All effect-size
estimates are accompanied by 95% bootstrap confidence intervals computed from
2,000 bootstrap replications. Noise-regime comparisons are reported for
SciDocs and HotpotQA, the two datasets where high-cyclicity conditions are
most pronounced in the clean-preference setting.

---

## Section 3 — Limitations

The current evaluation is subject to three limitations that bear on the
interpretation of results.

First, all quantitative comparisons are derived from pairwise preference votes
constructed from a three-ranker ensemble of BM25, TF-IDF, and MiniLM-L6
retrieval models. No experiment uses preferences generated by a large language
model. We engage with LLM-based reranking paradigms — pointwise scoring,
pairwise ranking prompting, and listwise permutation reranking — at the level
of implementation and literature positioning only. Whether FAS cycle repair
provides measurable benefit when applied to LLM-elicited preference graphs is
an open empirical question not addressed here, and no claim on this point is
made. The most directly analogous pending experiment would apply the repair
pipeline to pairwise LLM judgements as the preference source, replacing
score-derived votes; this experiment is identified as the highest-priority
direction for future work.

Second, the cross-encoder and tournament-aggregation baselines are included as
representative methods evaluated within our specific experimental protocol.
Results are not comparable to published figures from other studies that use
different candidate pools, retrieval depths, or preprocessing pipelines. We
make no claim of reproducing or surpassing any specific previously published
system; numerical comparisons are valid only within the controlled conditions
of the present evaluation.

Third, the effect of FAS cycle repair on retrieval quality is modest and
regime-dependent. Under near-acyclic vote constructions, repair is inert
because no cycles are present. Under high-cyclicity conditions, the mean
per-query change in nDCG at the repaired Copeland hybrid configuration has a
point estimate near zero, with a 95% bootstrap confidence interval that
includes zero on at least two of the four evaluation datasets. The
structural-consistency metrics — backward edge weight and pairwise
inconsistency count — are both measured relative to the same relevance
judgements used to compute nDCG, which limits the independence of the
structural and retrieval assessments. The primary contribution of the repair
analysis is therefore characterisation: it establishes when structural
inconsistency is present in multi-ranker preference graphs, quantifies the
magnitude of that inconsistency, and determines the conditions under which
a greedy repair step affects downstream ranking quality.

---

## Pre-Submission Evidence Check

The following sentences in the sections above should be verified against
repository outputs before final submission. Each check is tied to a specific
artifact or calculation that may have changed since the analysis was conducted.

**Check 1 — Cross-encoder nDCG figures and retrieval depth k.**
The numbers 0.8977 (SciDocs), 0.9499 (HotpotQA), and 0.8877 (BRIGHT) and
the associated k values (top-20 for SciDocs and BRIGHT; top-10 for HotpotQA)
should be confirmed against the modern-baseline summary CSVs.

**Check 2 — Query counts.**
The query counts 500 (SciDocs), 497 (HotpotQA), and 71 (BRIGHT) should be
confirmed against the dataset split or experiment log that was used for the
modern-baseline runs, not the full dataset size.

**Check 3 — FAS-balance vs Bradley–Terry noise deltas.**
The effect sizes +0.049 [+0.044, +0.054] (SciDocs) and +0.264 [+0.246,
+0.282] (HotpotQA) at 15% flip probability should be confirmed against the
bootstrap output CSVs for the noise-sensitivity comparison.

**Check 4 — SciDocs ms1 cyclicity figures.**
The values 87.5% cyclic queries and average largest SCC = 9.3 should be
confirmed against the structural-metrics table for SciDocs under ms1 vote
construction.

**Check 5 — Repaired Copeland hybrid ΔnDCG on SciDocs ms1.**
The values ΔnDCG = −0.0001, 95% CI [−0.0008, +0.0006] should be confirmed
against the bootstrap delta-nDCG table for SciDocs ms1, specifically the
Copeland hybrid row.

**Check 6 — FiQA qrels tier structure.**
The statement that FiQA relevance judgements are limited to a single graded
tier should be confirmed by inspecting the FiQA qrels file directly. If any
grade-0 or grade-2 entries exist, the exclusion rationale needs updating.

**Check 7 — Noise-level range.**
The range 5%–30% flip probability should be confirmed against the parameter
grid used in the noise-sensitivity experiments.

**Check 8 — Bootstrap replications count.**
The figure of 2,000 bootstrap replications should be confirmed against the
experiment configuration used for both the repair-effect and the
noise-sensitivity bootstrap runs, as the two analyses may have used different
settings.

**Check 9 — Average largest SCC = 9.3 under ms1 on SciDocs.**
This figure appears in the Related Work and Baselines sections. Confirm it
is the mean across all queries, not the median, and confirm the dataset is
the 500-query SciDocs split used in the main experiments.

**Check 10 — ms1_drop_mutual edge count claim.**
The statement that ms1_drop_mutual retains more preference edges than ms2
while achieving near-acyclicity should be confirmed against the edge-count
columns in the structural-metrics table (ms2 avg edges: 46.6;
ms1_drop_mutual avg edges: 178.2 on SciDocs).
