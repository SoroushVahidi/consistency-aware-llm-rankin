# Simulated Reviews

Date: 2026-08-01
Manuscript: `manuscript/main.tex`

These reviews are intentionally skeptical. They simulate three independent reviewers and then record what was revised without changing the frozen scientific evidence.

## Reviewer A: Information Retrieval

Recommendation: Minor Revision
Confidence: 4/5

Major strengths:
- The paper asks a clear IR evaluation question: whether structural preference-graph repair improves nDCG, not merely whether it removes cycles.
- The evaluation uses paired query-level tests and Holm correction, which is appropriate for multiple retrieval comparisons.
- The manuscript includes simple graph-free baselines, preventing an unfair comparison only among graph methods.

Major weaknesses:
- The main evidence uses BM25, TF-IDF, and MiniLM score-derived votes rather than a large, dedicated LLM-ranking benchmark.
- The candidate-pool construction is one RRF-centered policy in the primary analysis, which may affect the apparent competitiveness of RRF and CombSUM.
- Some Related Work sentences initially compressed too many citation roles into one sentence.

Questions for authors:
- How should readers interpret the finding for modern LLM reranking systems?
- Does the RRF-centered pool advantage graph-free fusion baselines?
- Why is nDCG primary rather than a broader multi-metric utility objective?

Possible rejection reasons:
- A reviewer seeking state-of-the-art reranking performance may find the ranker set too controlled.
- The real-LLM pilot is too small for confirmatory claims.

Possible acceptance reasons:
- The paper is not a SOTA reranking paper; it is a controlled audit of a structural assumption.
- The manuscript explicitly bounds the LLM pilot and reports MRR/MAP only as diagnostics.
- Baseline fairness and larger-pool robustness checks directly address key IR concerns.

Revision response:
- No scientific scope change was made. The LLM limitation was already explicit.
- Citation-cluster sentences in Related Work were split.
- The stale canonical-family smallest Holm-adjusted p-values were corrected.

## Reviewer B: Graph Algorithms

Recommendation: Minor Revision
Confidence: 4/5

Major strengths:
- The paper distinguishes MWFAS as a classical NP-hard problem from the empirical contribution.
- Exact SCIP repair is used appropriately as a diagnostic control, not sold as a scalable graph algorithm.
- The manuscript distinguishes greedy over-removal from retrieval utility, which is the right separation.

Major weaknesses:
- The greedy cycle-peeling heuristic is repository-specific and not the classical Eades-Lin-Smyth heuristic.
- The MIP formulation is stated compactly; a graph-algorithms reviewer may want more implementation detail.
- Exact scalability is not explored beyond the manuscript's query-graph sizes.

Questions for authors:
- Is exact repair included only for graphs where optimality is certified?
- Does exact repair remove less weight but still produce different feedback arc sets?
- Why not compare additional FAS approximations?

Possible rejection reasons:
- The paper is not an algorithms contribution and does not benchmark MWFAS algorithms broadly.

Possible acceptance reasons:
- The paper is clear that it is an empirical retrieval audit, not a new FAS algorithm paper.
- Exact repair closes a meaningful methodological objection to greedy-only repair studies.

Revision response:
- No algorithmic claims were added.
- The manuscript already states proven optimality requirements, solver role, and computational limitations.

## Reviewer C: Empirical CS and Statistics

Recommendation: Minor Revision
Confidence: 5/5

Major strengths:
- Query is the unit of inference.
- The paper avoids treating non-significance as equivalence.
- The real-LLM pilot uses cluster-level inference rather than row-level pseudo-replication.

Major weaknesses:
- The manuscript initially displayed stale smallest adjusted p-values in Table 4 and prose.
- Multiple prespecified families are corrected separately rather than under one omnibus family.
- Power is limited for smaller effects.

Questions for authors:
- Are family definitions prespecified and clearly separated?
- Are p-values and confidence intervals reproducible from stored artifacts?
- What effect sizes can the study actually rule out?

Possible rejection reasons:
- A reviewer could object that small effects remain undetected.
- A reviewer could object to multiple families if family boundaries were unclear.

Possible acceptance reasons:
- Family boundaries are explicit in Methodology and Results.
- The limitations section states that small effects below the detectable scale remain possible.
- The exact-repair comparison is a strong control against a common alternative explanation.

Revision response:
- Corrected the smallest Holm-adjusted p-values to 0.240 and 0.720.
- Updated `result_claims.yaml` and `RESULTS_CROSS_CHECK.md` with the correction.

## Net Editorial Simulation

Likely editorial outcome if reviewed by these three reviewers: Minor Revision.

Main reason: the paper is careful, transparent, and reproducible, but reviewers may ask for clarification of scope, modern LLM generality, and exact-repair scalability. Those points are already addressed in the manuscript without changing the evidence.
