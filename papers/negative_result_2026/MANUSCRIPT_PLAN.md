# Manuscript Plan: Negative-Result Paper on Structural Consistency vs. Retrieval Effectiveness

*Status: planning document, not a manuscript draft. All numbers cited here
are pulled from `reports/repository_scale_headroom_analysis/` (this
branch's repository-scale meta-analysis) and directly-quoted, verified
passages of `papers/JDIQ_2026/manuscript/main.tex`. See
`CLAIMS_AND_EVIDENCE.md` for the full evidence chain per claim.*

## Positioning decision: separate companion paper, not a JDIQ revision

**Recommendation: write this as a separate paper**, not a revision of the
JDIQ 2026 manuscript, for three reasons:

1. **The JDIQ manuscript is finalized and submission-ready.** Its own
   `PROJECT_STATUS.md`-equivalent documents mark it complete
   (`papers/JDIQ_2026/CANONICAL_PAPER_STORY.md`,
   `papers/JDIQ_2026/CONTRIBUTION_AUDIT.md`). Its scope is explicitly a
   "data-quality audit" of preference-graph construction (normalization,
   vote semantics, pooling) — a different central question from this
   paper's core contribution (oracle-selectability and predictability of
   the repair decision). Folding the new material in would materially
   expand an already-complete, already-scoped manuscript rather than
   sharpen it.
2. **The new contribution is genuinely additive, not corrective.** The
   JDIQ manuscript's central empirical finding — repair does not reliably
   move nDCG in aggregate — is **reused as a premise here, unmodified and
   uncontested** (Claim 1/2 below cite it directly rather than
   re-deriving it). This paper does not change or challenge that finding;
   it asks the next question the JDIQ manuscript's own aggregate framing
   cannot answer (is there a *per-query* opportunity a selector could
   realize?) and answers it: no, not practically. That is a natural
   companion contribution, not an erratum.
3. **Explicit repository instruction: do not silently replace or rewrite
   the JDIQ manuscript's historical result.** A revision-in-place risks
   exactly that, especially given the manuscript is already
   submission-frozen (`papers/JDIQ_2026/submission/`).

**This paper is a consolidation-adjacent companion paper**: it cites JDIQ
as established prior work (this repository's own), extends the empirical
question posed there, and consolidates four independent internal
selector-attempt results (three prior, one new) that JDIQ does not
discuss at all. It should cross-reference JDIQ explicitly in its
Introduction and Related Work, not present the two findings as
independent discoveries.

## Recommended title

**"When Structure Doesn't Predict Utility: Oracle-Selectability Limits for
Repairing LLM-Derived Preference Graphs"**

Alternative candidates (recorded, not selected): *"Consistency Is Not a
Retrieval Surrogate: A Negative Result on Selective Preference-Graph
Repair"*; *"How Much Could a Perfect Selector Save? Bounding the Value of
Preserve-vs-Repair Decisions in LLM Preference Graphs."* The recommended
title was chosen because it names the mechanism (oracle-selectability
bound), not just the negative conclusion, and signals a quantitative
result rather than a purely qualitative one — matching the paper's actual
contribution (a bound, not just an observation).

## Central thesis (one paragraph)

Enforcing structural consistency (acyclicity) in LLM-derived pairwise
preference graphs is often assumed to be a reasonable proxy for improving
downstream retrieval quality, since repair resolves contradictions the
original ranking signal cannot represent. We test this assumption at
scale — four retrieval benchmarks, two repair algorithms (greedy and exact
ILP), three vote-construction regimes, and 122,203 query-by-regime
observations reducing to 419 independent queries — and show it does not
hold in a form worth acting on. Structural repair is reliably active (it
changes graphs) but does not reliably improve nDCG in aggregate, replicating
and extending an existing finding. Going further, we ask whether even a
*perfect, per-query* oracle that always chose the better of preserve or
repair would be worth building a predictor for, and show the answer is no:
the oracle's average advantage (0.0025 nDCG) is roughly eight times smaller
than this same research program's own established minimum-detectable-effect
threshold (0.0207), is concentrated almost entirely in one already-known,
already-controllable variable (vote-construction cyclicity), and is not
recoverable from any pre-repair signal we could measure (all associations
below conventional "small effect" size). Four independent attempts at
learning this decision — three prior, informal, and one new, rigorous,
repository-scale analysis — converge on the same conclusion by different
routes. The result is not that consistency enforcement is useless, but
that it should not be treated as a retrieval-quality surrogate, and that
per-query selective repair is not, on current evidence, a productive
research direction at the whole-graph granularity.

## Relationship to prior work in this repository

| Document | Relationship |
|---|---|
| `papers/JDIQ_2026/manuscript/main.tex` | Cited, unmodified, as the source of the aggregate null result (Claim 1/2) |
| `docs/research/RESEARCH_TRAJECTORY.md` | The internal narrative this paper formalizes for external audiences; already updated with the NO-GO status |
| `reports/repository_scale_headroom_analysis/` | This paper's own primary evidence source (all Claims 3-5) |
| `docs/research/NOVELTY_AND_RELATED_WORK.md` | Base material for `RELATED_WORK_POSITIONING.md`, extended with the "negative empirical studies" category |

## What this plan does NOT do

- It does not rewrite, renumber, or alter any file under `papers/JDIQ_2026/`.
- It does not claim external literature verification for any citation not
  already verified elsewhere in this repository (see
  `RELATED_WORK_POSITIONING.md`'s explicit unverified-citation policy).
- It does not commit to a submission venue. That decision requires
  information (venue scope, page limits, review timeline) not available
  from repository artifacts alone and should be made by the author.
