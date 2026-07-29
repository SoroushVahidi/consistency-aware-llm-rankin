# Related Work Positioning

*Extends `docs/research/NOVELTY_AND_RELATED_WORK.md` (written for the
now-terminated predictive-selector direction) with an explicit "negative
empirical studies" category and language calibrated for this paper's
actual, narrower, evidence-backed contribution. Same citation-verification
policy applies: no external bibliographic metadata below has been verified
against a live literature search — every named work is a placeholder
requiring verification before submission, not a confirmed citation.*

## What this paper is NOT claiming as novel

Per explicit instruction, the novelty is not:
- a new FAS solver (this repository uses existing greedy and exact/SCIP MWFAS methods);
- a new reranking method (no new ranking-extraction method is proposed);
- a new learned selector (no selector was built or trained by this paper — the opposite: it explains why building one is not currently justified);
- a new uncertainty method (no new uncertainty quantification is introduced);
- the first observation that LLM judgments can be cyclic (already well documented, both in prior literature per category 2 below and in this repository's own earlier work).

## Related-work categories

### 1. LLM pairwise reranking and preference-graph aggregation
Pairwise Ranking Prompting (Qin et al., cited and implemented in this
repository as `llm_pairwise`), Bradley-Terry MLE, Markov-chain/PageRank
aggregation (Dwork et al., 2001). *Requires verification:* PRP-Graph,
LLM-RankFusion.

### 2. LLM-as-a-judge non-transitivity
This repository's own cycle-detection measurements are direct evidence
non-transitivity is real and prevalent (1.68%–97.5% of graphs cyclic
depending on vote construction, per the JDIQ manuscript's normalization
study). *Requires verification:* "Investigating Non-Transitivity in
LLM-as-a-Judge," TrustJudge.

### 3. Preference-graph denoising and acyclicity enforcement
Exactly what this repository's FAS repair (greedy and exact) does; the
paper's Claim 1/2 test whether this denoising step helps the downstream
task. *Requires verification:* "Preference Graph Ensemble and Denoise" (GED).

### 4. Feedback-arc-set and Kemeny-style ranking
Dwork et al. (2001), Ailon-Charikar-Newman (2008) — both already compared
against this repository's approach in `docs/LITERATURE_ALIGNMENT.md` §0.1–0.3
(local Kemenization baseline implemented and compared; FAS-as-Kemeny
equivalence under majority-vote weights discussed there). This paper adds
no new algorithmic comparison in this category; it cites the existing one.

### 5. Active pair acquisition and adaptive comparison acquisition
Distinct from this paper's scope (whole-graph *repair* selection, not
*acquisition* of new comparisons), but directly relevant as internal
prior art: this repository's own active-acquisition pivot (see
`PROJECT_STATUS.md`'s "Consistency-aware pivot" section) found that a
proposed active pair-selection strategy lost to random selection on a
real oracle — a second, independent internal negative result in an
adjacent problem, worth a brief cross-reference in this paper's discussion
as converging evidence that intervening on LLM-derived preference
structure is harder to make pay off than naive intuition suggests.
*Requires verification:* "Active Learners as Efficient PRP Rerankers," AcuRank.

### 6. Uncertainty-aware adaptive reranking
Overlaps with category 5; no additional citation identified beyond those above.

### 7. Learned ranking from comparison graphs
*Requires verification:* GNNRank. Relevant to this paper's explicit
scoping note (§ below) that a graph-neural or other structure-aware model
was not tried — this paper's negative finding is about simple, tabular,
pre-repair covariates specifically, not an exhaustive search of the model
space (see Claim 4's required cautious language).

### 8. Algorithm selection and intervention-value prediction
The closest category to this paper's actual question (predict whether an
intervention — repair — helps or harms). *Requires verification:*
"Learning to Defer in Ranking Systems." This repository's own Outcome F
policy-selection package (`src/consistency_ranker/policy_selection/`) is
the closest internal prior art: an oracle selector had real headroom
(0.1965 on a corrected utility scale) yet no learned gate realized it —
directly analogous to, and independently corroborating, this paper's own
finding that oracle headroom does not translate into a trainable signal
in this problem family.

### 9. Negative empirical studies (new category for this paper)
This category does not exist in `docs/research/NOVELTY_AND_RELATED_WORK.md`
and is added specifically because this paper's contribution is itself a
negative empirical study. *Requires verification and is the single most
important category to fill in before submission*: prior negative-result
papers in IR/ranking that test and reject a plausible-sounding
intervention (analogous structure to this paper), to position this work
within that tradition rather than as an isolated result. No specific
citation is proposed here — flagged explicitly as an open literature-search
task, not filled with a guessed reference.

## Required scope precision (do not overclaim)

The manuscript must state precisely, every time a "no prior work" or
"first" framing is used: *no direct prior work identified, within this
paper's necessarily bounded search, for the specific combination of*
(a) LLM-derived pairwise preference graphs, (b) the four datasets and
settings evaluated here, (c) whole-graph repair specifically (not
component/edge-level intervention, not other repair objectives), and
(d) downstream IR ranking metrics (nDCG/MRR/Recall) specifically. The
paper must **not** claim that no prior work has ever found any form of
graph repair or consistency enforcement useful for any task — only that,
within this precisely bounded scope, this comprehensive test did not find
it useful.
