# Manuscript Outline

*See `MANUSCRIPT_PLAN.md` for positioning/title/thesis and
`CLAIMS_AND_EVIDENCE.md` for the evidence backing every claim referenced
below by number. See `FIGURE_AND_TABLE_PLAN.md` for exact figure/table
placement.*

## 1. Abstract
See `ABSTRACT_DRAFTS.md` for candidate text. Must state: a plausible
assumption was tested (consistency-as-retrieval-surrogate); structural
repair succeeds on its own objective; downstream gains do not follow
(Claim 1/2); oracle selection has negligible practical headroom (Claim 3);
available features do not justify selective repair (Claim 4); the result
discourages treating structural consistency as a retrieval surrogate for
future LLM-ranking work.

## 2. Introduction
- Open with the implicit assumption under test (Manuscript positioning
  section of `MANUSCRIPT_PLAN.md`): if pairwise LLM preferences are
  inconsistent, enforcing transitivity/acyclicity should improve the
  final ranking.
- State plainly this is a comprehensive empirical test of that assumption,
  not a new algorithm, reranking method, learned selector, uncertainty
  method, or the first observation that LLM judgments can be cyclic.
  Explicitly disclaim each of these (per `RELATED_WORK_POSITIONING.md`).
- Preview the two-stage question: (a) does whole-graph repair help in
  aggregate [answer: no, established, Claim 1/2]; (b) even if not in
  aggregate, is there a per-query opportunity worth learning to exploit
  [answer: statistically real, practically negligible, Claim 3/4].
- State the relationship to the JDIQ manuscript explicitly (companion
  paper, not a revision — `MANUSCRIPT_PLAN.md`).

## 3. Background and problem formulation
- Preference graphs from LLM pairwise judgments; cycles as non-transitivity.
- Minimum Weighted Feedback Arc Set (MWFAS) repair, greedy and exact (ILP).
- Formal definition of the repair effect per query:
  \(\Delta_q = M_q(\text{repair}) - M_q(\text{preserve})\), both terms
  computed offline from the same graph (supervised effect measurement,
  not causal inference — carry over the methodological clarification
  already established in `docs/research/RESEARCH_TRAJECTORY.md` §8).
- Oracle headroom definition:
  \(H = \mathbb{E}[\max(M_q(\text{preserve}), M_q(\text{repair}))] -
  \max(\mathbb{E}[M_q(\text{preserve})], \mathbb{E}[M_q(\text{repair})])\).

## 4. Experimental design
- Table 1 (dataset/regime coverage). Four datasets, three vote-construction
  regimes, two repair algorithms, five candidate pools, multiple pool
  sizes/cutoffs, 9+ pair/extraction methods, 122,203 query-by-regime rows,
  419 independent queries.
- Explicit statement of the query-level vs. query-by-regime unit of
  analysis distinction and why it matters (pseudo-replication avoidance —
  `docs/research/REPRODUCIBILITY_AND_ARTIFACTS.md` and
  `reports/repository_scale_headroom_analysis/README.md`'s own caution
  note).
- Predeclared primary analysis vs. sensitivity checks (see
  `FIGURE_AND_TABLE_PLAN.md` sensitivity section).

## 5. Does structural repair improve retrieval?
- Reuse JDIQ's established result verbatim, cited not re-derived (Table 2).
- Figure 1 (structural activity vs. downstream significance).
- State Claim 1 and Claim 2 formally here.

## 6. Is selective whole-graph repair theoretically worthwhile?
- Oracle headroom analysis (Table 3, Figures 4-5).
- Practical-significance section: 0.0025 vs. 0.0207 MDE, ratio ≈ 0.12,
  and the explicit "statistically nonzero ≠ practically important"
  argument (Claim 3).
- State clearly the oracle bound is an upper bound unavailable to any real
  policy, and a learned policy would recover only a fraction of it (see
  `CLAIMS_AND_EVIDENCE.md` Claim 3 for the exact cautious phrasing —
  no fabricated "recoverable benefit" number).

## 7. Is repair utility predictable?
- Feature-association analysis (Table 5, Figure 6).
- Selector-attempt synthesis (Table 6, Figure 7) — all four attempts,
  including the misleading-metric cases (high ROC-AUC/low PR-AUC, fixed
  thresholds beating learned models).
- State Claim 4 with the required cautious language ("not predictably
  encoded," not "impossible").

## 8. Why consistency and retrieval quality diverge
- Regime decomposition (headroom collapses ms1 → ms1_drop_mutual → ms2).
- Benefit/harm symmetry analysis (Table 4, Figure 3): counts near-symmetric
  (28.2% vs 27.2%) but magnitudes are not quite (harm magnitude somewhat
  larger than benefit magnitude on average — report exact numbers from
  Table 4, do not round this asymmetry away).
- Explicitly hypotheses-labeled subsection (Claim 5): cyclicity plausibly
  increases variance/opportunity for both help and harm rather than
  reliably signaling directional benefit; cycle removal addresses
  structural contradiction without necessarily correcting the evaluated
  top-k relevance ordering; some inconsistent edges may be irrelevant to
  the evaluated cutoff; repair may remove genuine but non-transitive or
  context-dependent preference information. Label every sentence in this
  subsection as hypothesis, not established result.

## 9. Related work
Per `RELATED_WORK_POSITIONING.md`: cycle detection; graph denoising;
probabilistic aggregation; FAS/Kemeny repair; active pair acquisition;
uncertainty-aware reranking; algorithm selection; negative empirical
studies. Precise scope statement (LLM-derived pairwise preference graphs;
the four datasets/settings evaluated; whole-graph repair; downstream IR
ranking metrics) — do not claim no prior work has ever found repair
useful in any setting.

## 10. Limitations
Full list in `LIMITATIONS.md`; summarized here in the manuscript's own
words at submission time.

## 11. Conclusion
- Restate the thesis (see `MANUSCRIPT_PLAN.md`).
- Explicit forward-looking statement: whole-graph preserve-vs-repair
  policy learning is not recommended as a next step; component/edge-level
  intervention remains a distinct, unevaluated question requiring its own
  oracle-headroom gate before any investment (mirrors
  `docs/research/DECISION_LOG.md` entry D6's reopening criteria).
