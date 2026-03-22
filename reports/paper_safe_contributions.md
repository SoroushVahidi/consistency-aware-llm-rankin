# Paper-safe contribution statement (conservative)

**One paragraph (submission-ready framing):**

> We study pairwise preference graphs built from **multi-ranker score votes** (BM25, TF‑IDF, MiniLM) over shared candidate pools, and apply **greedy feedback-arc-set (FAS) repair** to enforce acyclicity before hybrid Copeland / balance reranking. Across **four retrieval benchmarks** and **three vote-construction regimes**, we show that **vote aggregation controls cycle incidence** (majority-style graphs are near-acyclic; per-ranker edges induce frequent cycles), and that **repair measurably reduces qrels-aligned structural inconsistency** (backward-edge weight and pairwise inconsistency against a label-derived reference) when cycles are present. **Effects on nDCG@k are not uniform**: under near-acyclic constructions repair is **inactive** (identical rankings); under other constructions we observe **dataset- and regime-dependent** changes in mean ΔnDCG, including **near-null**, **negative**, and **occasionally positive** bootstrap intervals—so we do **not** claim a general retrieval improvement from repair. The contribution is **measurement and conditional analysis** of structure–effectiveness alignment under transparent, reproducible vote-graph protocols.

**Bullets to keep near the abstract (optional):**

- Preference source = **score-derived votes**, not LLM pairwise judgments.
- Metrics: **nDCG@k** plus **graph–qrels consistency** diagnostics (BEW/PIC); diagnostics share labels with nDCG—state limitation.
- Inference: **query-level bootstrap** of mean ΔnDCG (not hierarchical).

**Do not imply:** causal benefit to end users, LLM alignment, or guaranteed ranking gains.
