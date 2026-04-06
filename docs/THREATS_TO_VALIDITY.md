# Threats to Validity

## 1) Dataset limitations

1. Canonical vote-derived package centers on SciDocs + HotpotQA, while the
   real-LLM addendum now includes SciDocs + HotpotQA + bounded FiQA evidence.
2. Query counts after eligibility filtering remain limited in some regimes
   (notably bounded FiQA processed-query count).
3. Domain coverage is broader than before but still narrower than a typical
   broad IR benchmark suite.

Mitigation path:
- expand real-LLM query budgets and add additional datasets (e.g., BRIGHT)
  under the same reporting template.

---

## 2) LLM preference noise / bias issues

1. Canonical committed publication package uses ranker-score-derived votes,
   while a separate real-LLM addendum now reports direct OpenAI pairwise runs.
2. LLM-centric interpretation should still be scoped as bounded and
   regime-conditional rather than universal.

Mitigation path:
- continue expanding direct `llm_pairwise` evidence with matched query budgets
  and transparent prompt/model configuration.

---

## 3) Graph-construction assumptions

1. Vote-construction choices (`min_support`, margin thresholds,
   mutual-pair dropping) materially change graph topology.
2. Findings are conditional on these constructions and should not be treated as
   algorithm-intrinsic constants.

Mitigation path:
- broader vote-construction ablations in canonical package.

---

## 4) External validity limits

1. Three-ranker setup in canonical vote suite may not reflect stronger or
   different retriever pools.
2. Current findings may not transfer unchanged to other retrieval tasks,
   annotation regimes, or candidate set definitions.

Mitigation path:
- add stronger rankers and cross-domain datasets to canonical evidence.

---

## 5) Computational cost limits

1. Greedy FAS is the active backend for real runs.
2. Exact ILP MWFAS is not yet implemented in `src/consistency_ranker/mwfas_solver.py`.
3. Cost-performance tradeoffs vs exact optimization are therefore unresolved.

Mitigation path:
- implement ILP backend and compare exact-vs-greedy on bounded slices.

---

## 6) Reproducibility caveats

1. Dependency versions are lower-bounded, not fully locked.
2. Some larger real-data trees are intentionally excluded from git; canonical
   package includes compact tables/summary artifacts.
3. Prior to this hardening pass, overwrite safety in key scripts was weaker.

Mitigation path:
- lock dependency set; keep overwrite-safe defaults; archive run manifests and
  exact command logs for camera-ready results.

