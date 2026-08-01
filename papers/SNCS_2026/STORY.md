# STORY.md -- Internal Narrative Plan (Stage 2)

This is a planning document, not manuscript prose. It exists so that every
section drafted in `manuscript/main.tex` argues toward the same point in the
same order. It should be read alongside `MANUSCRIPT_PLAN.md` (the Stage-1
scope contract this narrative must stay inside) and `EVIDENCE_MAP.md` (what
backs each empirical claim below).

## 1. The assumption in graph-based ranking work

When several ranking signals -- different rankers, different reranking
paradigms, or repeated pairwise judgments -- disagree about a query's
candidate documents, a common representation is a query-specific weighted
directed preference graph: an edge $u \to v$ records support for ranking $u$
ahead of $v$. Because the graph is built from several partially disagreeing
sources, it can contain directed cycles: $u \to v \to w \to u$. A large body
of rank-aggregation, feedback-arc-set, and preference-repair work treats
removing or minimizing such cycles -- restoring acyclicity -- as a natural,
often implicit, structural objective.

## 2. Why that assumption is plausible

The intuition has real support. A cycle is a case where the evidence
disagrees with itself: $u$ is preferred to $v$, $v$ to $w$, and yet $w$ back
to $u$. No single total order can honor all three edges simultaneously.
Feedback-arc-set repair resolves that contradiction with the least possible
disruption to the evidence, as measured by removed edge weight. It is
reasonable to expect that a graph that no longer contradicts itself is a
"better" input to ranking extraction, and therefore that repairing it should
help, or at least not hurt, the ranking that is ultimately read off the
graph.

## 3. The precise question this paper tests

Does enforcing acyclicity in a derived multi-ranker preference graph -- via
either heuristic (greedy cycle-peeling) or exact (SCIP-based minimum-weight
feedback-arc-set) repair -- produce a statistically reliable improvement in
downstream retrieval effectiveness (nDCG), once construction choices, paired
inference, and multiplicity correction are made explicit? And if it does
not, what follows for treating structural graph consistency as a proxy for
retrieval utility?

This is deliberately not "does repair help retrieval" stated loosely --
that framing invites a trivial-sounding answer and does not specify what
would count as evidence either way. The precise version fixes the
evaluation protocol (paired, Holm-corrected nDCG) and asks about a
*reliable*, *general* effect, not any effect on any single dataset or cell.

## 4. Why prior evidence does not answer this cleanly

Three gaps in the available evidence keep the question open:

- **Repair method confound.** Almost all preference-repair evaluations use
  heuristic repair (e.g. greedy cycle-peeling, linear-arrangement
  heuristics). A null or weak retrieval effect under heuristic repair is
  always open to the objection that the heuristic under-repairs the graph,
  so the null could be an artifact of suboptimal repair rather than
  evidence about repair itself.
- **Construction is entangled with repair.** Whether a graph is cyclic at
  all, and how much repair has to do, depends heavily on upstream choices
  (score normalization, vote-construction regime, candidate pooling) that
  are usually not varied or reported alongside the repair result. Without
  holding construction explicit, an apparent repair effect (or its absence)
  cannot be attributed to repair specifically.
- **Structural and retrieval metrics are conflated in reporting.** Studies
  that report cyclicity reduction, removed edge weight, or agreement with
  ground-truth pairwise preferences alongside a retrieval metric often do
  not test whether the two move together with corrected statistical
  inference; an improvement in one is implicitly read as evidence for the
  other.

## 5. The controlled comparisons used

The evidence base for this paper (`reports/full_calibrated_core/` and the
studies listed in `EVIDENCE_MAP.md`) holds construction explicit and
compares:

- **unrepaired** vs. **greedy-repaired** vs. **exactly repaired** (SCIP
  MWFAS) preference graphs, on the same underlying candidate sets and
  ranker scores;
- across **three vote-construction regimes** (`ms2`, `ms1`,
  `ms1_drop_mutual`) that vary how much contradictory structure is retained
  before repair ever runs;
- across **four retrieval benchmarks** (SciDocs, FiQA, HotpotQA, BRIGHT)
  spanning distinct domains;
- under both the **canonical** evaluation cells ($P=k$) and a
  **larger-pool** ($P>k$) design that gives repair room to change which
  documents even enter the evaluated top-$k$;
- with **Holm-corrected paired nDCG** as the single primary confirmatory
  test, and bootstrap intervals, alternative pools, added baselines, and
  power/minimum-detectable-effect analysis reported as robustness checks,
  not additional headline families.

## 6. Alternative explanations eliminated

- **"The heuristic just doesn't repair enough."** Eliminated by the exact
  SCIP repair arm: it reaches proven optimality on every nonempty canonical
  query graph and removes *less* total edge weight than greedy repair, yet
  the retrieval decision does not change. If under-repair were the reason
  for a null retrieval effect, exact repair should have revealed a gain
  greedy repair missed; it does not.
- **"It's a $P=k$ evaluation artifact -- repair can't even change what's
  evaluated."** Eliminated by the larger-pool ($P>k$) design: repair does
  change top-$k$ membership at a non-trivial rate once $P>k$, so repair is
  not evaluation-inert; the retrieval decision still does not change.
- **"The graph was never really cyclic to begin with."** Eliminated by
  reporting cyclicity and removed edge weight directly: repair is
  structurally active (nonzero, regime- and dataset-dependent removed
  weight) under the permissive construction regime.
- **"It's one dataset's idiosyncrasy."** Addressed, not eliminated with
  certainty, by spanning four domains; the paper does not claim this
  generalizes beyond the tested benchmarks and construction regimes.

## 7. What is observed structurally

Vote-construction regime, not the repair algorithm, is the dominant driver
of whether a graph is cyclic at all: cyclicity swings by tens of percentage
points between regimes on the same underlying documents, and raw
score-scale dominance (one ranker's raw margins overwhelming the others)
materially changes which votes and edges are even retained. Where the
permissive regime keeps contradictory structure, repair (greedy or exact)
is genuinely active: it removes a measurable share of total graph weight,
and under $P>k$ evaluation it changes top-$k$ set membership at a
double-digit mean rate. Exact repair reaches proven optimality and removes
less weight than greedy, confirming the graphs are not merely
"under-repaired" by the heuristic.

## 8. What is observed in retrieval effectiveness

Despite that genuine structural activity, no repaired-vs-unrepaired nDCG
cell family -- canonical, larger-pool, or exact-repair -- survives Holm
correction across the tested benchmarks and regimes. Point estimates are
sometimes positive, but the corrected paired tests do not support a general
effect, and simple graph-free baselines (CombSUM, RRF) remain competitive
with the best repaired hybrid.

## 9. What can and cannot be concluded

**Can conclude:** enforcing acyclicity in these derived preference graphs
produces real, measurable structural change, but that change does not
translate into a statistically supported general improvement in retrieval
effectiveness under the tested benchmarks, construction regimes, and
evaluation protocol -- including once heuristic suboptimality is ruled out
by exact repair. Structural consistency and retrieval utility behave as
distinct quality dimensions in this evidence.

**Cannot conclude:** that repair *never* helps retrieval in any setting;
that exact repair is *never* useful; that cycles are always harmless to
retrieval; that the four tested benchmarks and three tested construction
regimes represent every practically relevant setting; or that any
particular criterion exists for deciding, per query, when repair is worth
applying (a separate, already-negative research thread, excluded from this
paper's evidence base).

## 10. Why this matters for ranking, retrieval, and pairwise-judgment systems

Practitioners building pairwise-judgment or multi-ranker pipelines
(including LLM-as-judge and pairwise-reranking systems, where cyclic
preference graphs arise naturally) often reach for cycle repair as a
self-evidently good preprocessing step, reported via structural diagnostics
alone. This paper's evidence says that structural consistency should be
audited and reported as a property in its own right, separate from
retrieval utility, and that a system claiming a retrieval benefit from
consistency repair needs to demonstrate it directly with corrected,
paired retrieval evaluation -- structural improvement, even when confirmed
exact and not a heuristic artifact, is not by itself evidence of a
retrieval gain.
