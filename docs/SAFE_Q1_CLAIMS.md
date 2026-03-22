# Safe Q1 Claims and Wording Guardrails

## Supported claims (safe)

1. Vote-construction regime strongly changes cyclicity/SCC structure in
   preference graphs (`ms2` vs `ms1` vs `ms1_drop_mutual`).
2. Greedy FAS repair reduces graph-level inconsistency metrics (BEW/PIC) in
   high-cyclicity settings.
3. Repaired-vs-unrepaired Copeland can be significantly negative on SciDocs
   under `ms1`; effects are near-zero/inactive in near-acyclic settings.
4. Harm concentration in larger-SCC queries is observable in current canonical
   datasets.
5. Structural consistency improvement does not guarantee retrieval improvement.

Primary evidence:
- `outputs/q1_journal_package/table_main_performance.csv`
- `outputs/q1_journal_package/table_structural_consistency.csv`
- `outputs/q1_journal_package/table_significance.csv`
- `outputs/q1_journal_package/table_regime_analysis.csv`

---

## Unsafe / too-strong claims (avoid)

1. “FAS repair improves retrieval quality overall.”
2. “Results already generalize to direct LLM preference judgments.”
3. “Exact MWFAS was validated and outperforms greedy on real datasets.”
4. “Method is production-ready for large-scale online reranking.”
5. “Two-dataset canonical package is sufficient for broad generalization.”

---

## Recommended conservative wording

- Use: “In the evaluated vote-construction regimes, FAS repair reduced
  graph-level inconsistency but did not uniformly improve nDCG.”
- Use: “Under high-cyclicity `ms1` on SciDocs, repaired Copeland showed a
  statistically negative mean ΔnDCG.”
- Use: “Under near-acyclic regimes, repaired and unrepaired rankings were often
  identical (inactive repair effect).”
- Use: “These results are demonstrated on the current canonical dataset set and
  should be interpreted as conditional, not universal.”

---

## Recommended novelty statement

“The primary novelty is a controlled, evidence-backed characterization of when
cycle repair changes retrieval behavior: vote construction governs cyclicity,
repair reliably changes structural consistency, and retrieval impact is
conditional rather than uniformly positive.”

---

## Recommended limitations paragraph

“Our canonical evidence package covers two benchmark datasets and vote-derived
pairwise preferences from three rankers. While we observe consistent structural
effects of FAS repair and regime-dependent retrieval effects, these findings do
not yet establish broad generalization to direct LLM judgment data, additional
domains, or exact MWFAS solvers. Structural consistency metrics are computed
relative to qrels-derived references and should be interpreted as diagnostic
alignment measures rather than independent ground-truth fidelity.”

