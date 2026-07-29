# Abstract Drafts

*Both drafts below satisfy the required framing: a plausible assumption
was tested; structural repair succeeds on its own objective; downstream
gains do not follow; oracle selection has negligible practical headroom;
available features do not justify selective repair; the result informs
future LLM-ranking research by discouraging structural consistency from
being treated as a retrieval surrogate. Neither draft claims a submission
venue or makes any claim not backed by `CLAIMS_AND_EVIDENCE.md`.*

## Draft A (longer, methods-forward)

> When large language models are used to produce pairwise preference
> judgments over retrieval candidates, the resulting preference graphs are
> frequently non-transitive. A natural response is to repair these graphs
> — resolving cycles via minimum weighted feedback-arc-set (MWFAS)
> optimization — before extracting a final ranking, on the implicit
> assumption that structural consistency is a reasonable proxy for
> retrieval quality. We test this assumption comprehensively: across four
> retrieval benchmarks, two repair algorithms (greedy and exact ILP), three
> vote-construction regimes, and 122,203 query-by-regime observations
> reducing to 419 independent queries, repair is reliably structurally
> active but does not reliably improve nDCG in aggregate — no repaired-
> versus-unrepaired comparison survives Holm correction in any tested
> family. Going further, we ask whether even a perfect, per-query oracle
> that always chose the better of preserving or repairing each graph would
> be worth building a predictor for. The oracle's average advantage
> (0.0025 nDCG, 95% CI [0.0020, 0.0030]) is real but roughly eight times
> smaller than this same evaluation framework's own established minimum-
> detectable effect (0.0207), is concentrated almost entirely in one
> already-observable variable (vote-construction cyclicity), and is not
> recoverable from any pre-repair signal we measured — every tested
> covariate's association with the repair effect falls well below
> conventional "small effect" thresholds. Four independent attempts at
> learning this decision, three prior and one new, converge on the same
> conclusion by different routes. We conclude that structural consistency
> should not be treated as a retrieval-quality surrogate, and that
> per-query selective repair, at the whole-graph granularity, is not
> currently a productive direction for LLM-ranking research.

## Draft B (shorter, conclusion-forward)

> Enforcing acyclicity in LLM-derived pairwise preference graphs is often
> assumed to improve downstream retrieval rankings by resolving judgment
> contradictions. We show, across four datasets, two repair algorithms,
> and 419 independent queries (122,203 query-by-regime observations), that
> this assumption does not hold in a form worth acting on. Repair reliably
> changes graph structure but produces no Holm-significant nDCG
> improvement in any tested condition, replicating and extending an
> existing result. We then ask a harder question: even though repair does
> not help on average, is there a per-query opportunity a perfect selector
> could exploit? The answer is a bounded yes-but-negligible: oracle
> headroom is statistically real (0.0025 nDCG, CI excludes zero) but
> roughly 8x below this evaluation framework's own minimum-detectable-
> effect threshold, almost entirely explained by one already-known
> variable, and not recoverable from any available pre-repair signal.
> Four independent modeling attempts confirm this. We argue structural
> consistency should not be used as a retrieval-quality surrogate, and
> that selective whole-graph repair is not a productive research direction
> on current evidence.

## Style notes for whichever draft is finalized

- Keep the numeric ratio (~8x) and the two headline numbers (0.0025 vs.
  0.0207) in the abstract — they are the paper's most citable, checkable
  claim and should not be paraphrased away.
- Do not use the word "impossible" or any equivalent absolute claim about
  predictability (Claim 4's required cautious language).
- The word "negative result" should appear explicitly at least once —
  per the manuscript positioning, this paper should read as a rigorous
  falsification, not an apologetic report of a failed effort.
