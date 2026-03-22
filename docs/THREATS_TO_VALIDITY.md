# Threats to Validity

## 1) Dataset limitations

1. Canonical paper package currently centers on SciDocs + HotpotQA.
2. Query counts after eligibility filtering are limited in some regimes.
3. Domain coverage is narrower than a typical broad IR benchmark suite.

Mitigation path:
- add FiQA/BRIGHT canonical runs and report query-count sensitivity.

---

## 2) LLM preference noise / bias issues

1. Canonical committed publication package uses ranker-score-derived votes,
   not direct LLM pairwise judgments.
2. Any LLM-centric interpretation must be scoped as prospective unless direct
   LLM pairwise experiments are added.

Mitigation path:
- add dedicated `llm_pairwise_file` experiments with transparent prompt/model setup.

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

