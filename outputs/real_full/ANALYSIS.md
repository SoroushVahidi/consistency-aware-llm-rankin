# Evidence-Based Analysis of Real-Data Experiment Results

**Source files inspected:**
- `outputs/real_full/scidocs/scidocs_summary.csv`
- `outputs/real_full/scidocs/scidocs_experiment_summary.json`
- `outputs/real_full/scidocs/scidocs_per_query.csv`
- `outputs/real_full/fiqa/fiqa_summary.csv`
- `outputs/real_full/fiqa/fiqa_experiment_summary.json`
- `outputs/real_full/fiqa/fiqa_per_query.csv`
- `outputs/real_full/hotpotqa/hotpotqa_summary.csv`
- `outputs/real_full/hotpotqa/hotpotqa_experiment_summary.json`
- `outputs/real_full/hotpotqa/hotpotqa_per_query.csv`
- `outputs/real_full/bright/bright_summary.csv`
- `outputs/real_full/bright/bright_experiment_summary.json`
- `outputs/real_full/bright/bright_per_query.csv`
- `outputs/real_full/scidocs/timings/scidocs_timings.csv`
- `outputs/real_full/fiqa/timings/fiqa_timings.csv`
- `outputs/real_full/hotpotqa/timings/hotpotqa_timings.csv`
- `outputs/real_full/bright/timings/bright_timings.csv`

---

## ⚠ Critical Data Provenance Note

All four `*_summary.csv`, `*_per_query.csv`, and `*_experiment_summary.json` files
reflect the **`qrels_flip` preference source** (15% random edge flips), confirmed by
`preference_source=qrels_flip` in every per-query row and `"preference_source": "qrels_flip"`
in every experiment summary JSON. The `qrels` (oracle/baseline) run was executed
first and **its output files were overwritten** by the subsequent `qrels_flip` run,
which wrote to the same directory. Consequently, only the `qrels_flip` condition
is directly available for cross-method comparison; the clean `qrels` nDCG baseline
per method cannot be read back from these files.

---

## 1. Which datasets completed successfully

All four completed with zero skipped queries:

| Dataset  | Queries processed | Skipped | Source file |
|----------|-------------------|---------|-------------|
| SciDocs  | 500               | 0       | `scidocs_experiment_summary.json` |
| FiQA     | 648               | 0       | `fiqa_experiment_summary.json` |
| HotpotQA | 500               | 0       | `hotpotqa_experiment_summary.json` |
| BRIGHT   | 100               | 0       | `bright_experiment_summary.json` |

---

## 2. Methods compared on each dataset

Identical 11-method set on all four datasets
(from column `method` in every `*_summary.csv`):

1. `score_sum`                              — baseline
2. `borda`                                  — baseline
3. `pagerank`                               — baseline
4. `greedy_fas_topological`                 — FAS-repair
5. `greedy_fas_weighted_balance`            — FAS-repair
6. `greedy_fas_copeland`                    — FAS-repair
7. `greedy_fas_score_augmented_topological` — FAS-repair
8. `hybrid_rrf_fas_regularized`             — hybrid FAS
9. `hybrid_rrf_balance_a05`                 — hybrid FAS
10. `hybrid_rrf_copeland_a03`               — hybrid FAS
11. `hybrid_rrf_priority_topo_a03`          — hybrid FAS

---

## 3. Metrics reported on each dataset

All metrics appear in every `*_summary.csv` under identical column names:

| Metric column | Description |
|---|---|
| `ndcg_mean` | Mean nDCG@k (primary metric, k = top_k) |
| `tau_mean` | Mean Kendall τ vs qrels reference ranking |
| `bew_mean` | Mean backward-edge weight vs qrels reference |
| `pic_mean` | Mean pairwise inconsistency count vs qrels reference |
| `map_mean` | Mean AP@k |
| `precision_at_k_mean` | Mean Precision@k |
| `recall_at_k_mean` | Mean Recall@k |
| `pairwise_accuracy_mean` | Mean pairwise accuracy vs relevance labels |
| `runtime_mean_s` | Mean per-query wall time (s) |
| `cyclic_pct` | % of queries with cyclic preference graphs |
| `fas_removed_weight_mean` | Mean FAS edge weight removed per query |
| `graph_ref_bew_pre/post_mean` | Mean graph–reference BEW before/after FAS |

---

## 4. Best method on each dataset (with exact numbers)

All values from `*_summary.csv`, column `ndcg_mean` (primary metric). All results
are for `preference_source=qrels_flip`.

**SciDocs** (500 queries, top-k=20, 98.8% cyclic):
- `score_sum`: ndcg_mean = **1.0000**, tau_mean = 0.3325, bew_mean = 9.6100
- `borda`:     ndcg_mean = **1.0000**, tau_mean = 0.3325, bew_mean = 9.6100
- *(tied for first)*

**FiQA** (648 queries, top-k=20, 100% cyclic):
- `score_sum`: ndcg_mean = **0.9998**, tau_mean = 0.5678, bew_mean = 30.8364

**HotpotQA** (500 queries, top-k=10, 54.4% cyclic):
- `score_sum`: ndcg_mean = **1.0000**, tau_mean = 0.3248, bew_mean = 2.6260
- `borda`:     ndcg_mean = **1.0000**, tau_mean = 0.3248, bew_mean = 2.6260
- *(tied for first)*

**BRIGHT** (100 queries, top-k=20, 100% cyclic):
- `score_sum`: ndcg_mean = **1.0000**, tau_mean = 0.4466, bew_mean = 18.0900

---

## 5. Best non-FAS baseline on each dataset

(FAS-free baselines: `score_sum`, `borda`, `pagerank`)

| Dataset  | Best baseline   | nDCG_mean | τ_mean | Source column |
|----------|-----------------|-----------|--------|---------------|
| SciDocs  | score_sum/borda | 1.0000    | 0.3325 | scidocs_summary.csv |
| FiQA     | score_sum       | 0.9998    | 0.5678 | fiqa_summary.csv |
| HotpotQA | score_sum/borda | 1.0000    | 0.3248 | hotpotqa_summary.csv |
| BRIGHT   | score_sum       | 1.0000    | 0.4466 | bright_summary.csv |

`pagerank` is the weakest non-FAS baseline on every dataset:
SciDocs 0.9291, FiQA 0.9009, HotpotQA 0.9362, BRIGHT 0.9129.

---

## 6. Best FAS-based / repaired method on each dataset

FAS-based methods: `greedy_fas_*` and `hybrid_rrf_*`.

| Dataset  | Best FAS method              | nDCG_mean | τ_mean | Source |
|----------|------------------------------|-----------|--------|--------|
| SciDocs  | greedy_fas_weighted_balance  | 0.9980    | 0.5693 | scidocs_summary.csv |
|          | (also: greedy_fas_copeland, hybrid_rrf_fas_regularized, hybrid_rrf_balance_a05, hybrid_rrf_copeland_a03 — all 0.9980) | | | |
| FiQA     | greedy_fas_weighted_balance  | 0.9657    | 0.5873 | fiqa_summary.csv |
|          | (also: hybrid_rrf_fas_regularized, hybrid_rrf_balance_a05 — all 0.9657) | | | |
| HotpotQA | greedy_fas_weighted_balance  | 0.9842    | 0.6787 | hotpotqa_summary.csv |
|          | (also: greedy_fas_copeland, hybrid_rrf_fas_regularized, hybrid_rrf_balance_a05, hybrid_rrf_copeland_a03 — all 0.9842) | | | |
| BRIGHT   | greedy_fas_weighted_balance  | 0.9795    | 0.5920 | bright_summary.csv |
|          | (also: hybrid_rrf_fas_regularized, hybrid_rrf_balance_a05 — all 0.9795) | | | |

Note: `greedy_fas_topological` is the **worst** FAS method on every dataset:
SciDocs 0.8375, FiQA 0.7583, HotpotQA 0.8202, BRIGHT 0.7482.
`greedy_fas_score_augmented_topological` is similarly poor: negative τ on HotpotQA (−0.0332).

---

## 7. Did any FAS-based method beat the strongest baseline on any dataset?

**No.** On all four datasets under `qrels_flip`, `score_sum` achieves equal or higher
nDCG@k than every FAS-based method. The gaps (best FAS vs best baseline):

| Dataset  | Best baseline nDCG | Best FAS nDCG | Gap (FAS − baseline) |
|----------|--------------------|---------------|----------------------|
| SciDocs  | 1.0000             | 0.9980        | **−0.0020** |
| FiQA     | 0.9998             | 0.9657        | **−0.0341** |
| HotpotQA | 1.0000             | 0.9842        | **−0.0158** |
| BRIGHT   | 1.0000             | 0.9795        | **−0.0205** |

FAS-based methods are consistently below the strongest non-FAS baseline on nDCG.

However, on the **backward-edge-weight (BEW)** metric (graph self-consistency),
FAS methods do lead on some datasets:

- **FiQA** (bew): `hybrid_rrf_priority_topo_a03` = 29.898 vs `score_sum` = 30.836 — FAS wins by BEW
- **SciDocs** (bew): `greedy_fas_score_augmented_topological` = 7.388 vs `score_sum` = 9.610 — FAS wins by BEW
- **HotpotQA** (bew): `greedy_fas_score_augmented_topological` = 0.924 vs `score_sum` = 2.626 — FAS wins by BEW
- **BRIGHT** (bew): `hybrid_rrf_priority_topo_a03` = 16.22 vs `score_sum` = 18.09 — FAS wins by BEW

FAS reliably **reduces graph-internal inconsistency** (BEW), but this does not
translate into nDCG gains over score_sum.

---

## 8. Did qrels_flip help repaired/FAS methods relative to normal qrels?

**Cannot be directly compared from the available files.** The `qrels` run outputs
were overwritten by the `qrels_flip` run in the same output directory for all
four datasets. Only `qrels_flip` data is available in the current output files.

Indirect observations from the `qrels_flip` experiment:

- Graph repair (FAS) **does activate** under `qrels_flip` (cycles in 54.4–100% of
  queries; avg FAS removed weight per query: SciDocs 8.802, FiQA 37.702, HotpotQA 1.012, BRIGHT 20.21).
- FAS reduces graph-vs-reference inconsistency substantially:
  - SciDocs: graph_ref_bew_pre = 9.61 → post = 4.92 (49% reduction)
  - FiQA: 30.84 → 18.06 (41% reduction)
  - HotpotQA: 2.626 → 2.272 (13% reduction)
  - BRIGHT: 18.09 → 10.89 (40% reduction)
- **Despite this**, FAS does not outperform `score_sum` on nDCG on any dataset.

Under pure `qrels` (no flip), no cycles would be expected since qrel-derived
preferences are near-transitive — FAS would have essentially nothing to do,
and all methods would likely converge to the same nDCG ≈ 1.0. The `qrels_flip`
condition is the only regime where FAS is meaningfully exercised; it still does
not yield nDCG wins.

---

## 9. Which dataset gives the strongest evidence in favor of the consistency-repair idea?

**HotpotQA** (qrels_flip, 500 queries, top-k=10).

Reasons:
1. `greedy_fas_topological` achieves BEW = **0.932** vs `score_sum` BEW = 2.626 — the largest
   BEW improvement ratio (64% reduction) of any dataset.
2. FAS demonstrates the most structured cycle removal relative to graph size
   (avg FAS removed weight = 1.012 on a graph with avg 18.34 edges, only 54.4% cyclic).
3. Even in this best-case scenario, nDCG for `greedy_fas_topological` = 0.8202 vs
   `score_sum` = 1.0000, and `greedy_fas_weighted_balance` = 0.9842 — the closest
   any FAS method comes to the baseline nDCG on any dataset.

---

## 10. Which dataset gives the strongest evidence against the consistency-repair idea?

**FiQA** (qrels_flip, 648 queries, top-k=20, 100% cyclic).

Reasons:
1. Largest and densest graphs in the experiment (avg 107.88 edges per query at 20 nodes
   — near-complete graphs), 100% cyclic.
2. FAS does substantial work (avg removed weight = 37.702), yet:
   - `score_sum` nDCG = **0.9998** (essentially perfect)
   - Best FAS method nDCG = **0.9657** (`greedy_fas_weighted_balance`) — a gap of **−0.0341**
   - `greedy_fas_topological` nDCG = **0.7583** — **22 pp below** the baseline
3. The `greedy_fas_topological` method's Kendall τ = 0.3069 vs `score_sum` τ = 0.5678 —
   FAS actually disrupts the ranking quality more severely on FiQA than any other dataset.
4. The gap between BEW-optimal FAS methods and the oracle-quality nDCG is largest here,
   demonstrating that minimizing graph inconsistency (BEW goal of FAS) and maximizing
   ranking quality (nDCG goal of retrieval) are **decoupled** objectives in this dense-graph regime.

---

## 11. Consolidated results table

All values from `*_summary.csv`. Primary metric = ndcg_mean. All results are `qrels_flip`.

| dataset   | preference_source | best_method   | best_metric_value | best_FAS_method              | FAS_gap_to_best |
|-----------|-------------------|---------------|-------------------|------------------------------|-----------------|
| scidocs   | qrels_flip        | score_sum     | 1.0000 (nDCG)     | greedy_fas_weighted_balance  | −0.0020         |
| fiqa      | qrels_flip        | score_sum     | 0.9998 (nDCG)     | greedy_fas_weighted_balance  | −0.0341         |
| hotpotqa  | qrels_flip        | score_sum     | 1.0000 (nDCG)     | greedy_fas_weighted_balance  | −0.0158         |
| bright    | qrels_flip        | score_sum     | 1.0000 (nDCG)     | greedy_fas_weighted_balance  | −0.0205         |

Note: `best_FAS_method` is the same (`greedy_fas_weighted_balance` / `hybrid_rrf_fas_regularized`
are equal) on all datasets. The `FAS_gap_to_best` is negative in every row, meaning
FAS-based methods never beat the strongest baseline.

---

## 12. Final verdict

### Verdict: **STILL WEAK**

**Reasons:**

1. **No FAS method beats the strongest baseline on any dataset.** `score_sum`
   achieves nDCG@k ≥ 0.9998 on all four datasets; every FAS-based and hybrid
   method ranks strictly below it (gaps: −0.0020 to −0.0341 nDCG). There is
   zero empirical evidence that the consistency-repair idea improves ranking
   quality over a simple score-sum heuristic.

2. **Experiments are on proxy (synthetic) data, not real benchmark data.**
   The HuggingFace datasets were inaccessible (no network); all data was
   generated by `scripts/generate_proxy_datasets.py` using random vocabulary.
   Proxy preferences are drawn from randomly assigned relevance labels with no
   semantic content. The results therefore measure the methods' behavior on
   artificial graph structure, not real LLM-induced pairwise inconsistencies.
   This is a fundamental validity problem for a paper submission.

3. **Score_sum trivially dominates synthetic data.** Because proxy preferences
   are derived directly from synthetic qrels (which have no cycles in the clean
   condition), `score_sum` is effectively an oracle on this data. Even under
   `qrels_flip`, with 15% edge corruption and near-complete cyclic graphs,
   `score_sum`'s advantage persists because the majority-vote signal (sum of
   weights) still points in the right direction. Real LLM pairwise data would
   be significantly noisier and more cyclic, where FAS repair might show
   different behavior — but that experiment has not been run.

4. **FAS successfully reduces internal inconsistency (BEW) but this does not
   transfer to nDCG gains.** BEW reductions of 40–64% are observed across all
   datasets after FAS repair, yet nDCG simultaneously decreases compared to
   score_sum. This means the optimization target of FAS (graph self-consistency)
   is misaligned with the evaluation target (retrieval quality). Without
   re-aligning or providing real LLM preferences where natural cycles exist,
   this gap cannot be bridged by further ablations on proxy data.

5. **Only one preference source with meaningful cycle signal was tested.**
   `qrels_flip` is an artificial corruption, not a signal from real rankers
   or LLMs. The `votes_file` and `score_file` modes (which would use actual
   BM25/TF-IDF/MiniLM signals and generate real disagreement) were not run.

6. **No statistical significance testing was performed.** Bootstrap confidence
   intervals (`bootstrap_method_deltas.py`) were not run. The nDCG differences
   between FAS methods and baselines are absolute-value gaps without any
   significance estimates.

**To reach "moderate" evidence:**
- Run on real HuggingFace data with real LLM or multi-ranker vote preferences
- Demonstrate FAS nDCG gain ≥ baseline on at least one real dataset
- Add bootstrap significance tests

**To reach "strong" evidence:**
- All of the above plus multiple preference noise levels, multiple top-k values,
  and ablation across FAS variants on real data

---

*Analysis generated from files in `outputs/real_full/` on 2026-03-21.*
