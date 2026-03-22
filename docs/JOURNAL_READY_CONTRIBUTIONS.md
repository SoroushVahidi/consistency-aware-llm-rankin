# Journal-Ready Contributions (Conservative Draft)

## Candidate contribution statements (3–5)

1. **Methodological/experimental framework:**  
   A reproducible pipeline for constructing weighted pairwise-preference graphs,
   applying greedy FAS repair, and evaluating repaired/unrepaired ranking
   extractors under controlled vote-construction regimes.

2. **Empirical regime finding:**  
   A canonical two-dataset study showing that vote construction is the dominant
   driver of cyclicity (near-acyclic vs highly cyclic regimes), which in turn
   governs whether repair is inactive or retrieval-harmful.

3. **Structural-vs-retrieval decoupling evidence:**  
   Demonstration that graph-level inconsistency metrics (BEW/PIC) can improve
   after repair even when nDCG@k does not improve.

4. **Statistical conditionality result:**  
   Bootstrap-based evidence that repaired-vs-unrepaired Copeland effects are
   significantly negative in high-cyclicity SciDocs ms1 and concentrated in
   larger-SCC query strata.

5. **Publication artifactization:**  
   A committed paper-evidence bundle and manuscript-facing table-generation
   tooling (`outputs/q1_journal_package/`, `outputs/pub_vote_cmp_v2/paper_package/`,
   `reports/paper_tables/`).

---

## Novelty relative to likely baseline literature categories

### Relative to generic rank-fusion baselines
- Novelty is not “better fusion performance everywhere,” but conditional
  diagnosis of repair behavior under controlled cyclicity regimes.

### Relative to consistency-repair / graph-cleaning literature
- Novelty is explicit coupling of graph structure diagnostics with retrieval
  quality deltas and bootstrap uncertainty in a retrieval evaluation context.

### Relative to LLM preference aggregation narratives
- Novelty is framing consistency repair as a **regime-sensitive diagnostic and
  regularization tool**, avoiding unsupported universal benefit claims.

---

## Type labels (methodological vs empirical vs analytical)

- **Methodological:** pipeline design, vote constructions, repair/extraction protocol.
- **Empirical:** dataset-level and regime-level nDCG outcomes.
- **Analytical:** SCC-stratified and bootstrap-based conditional inference.

