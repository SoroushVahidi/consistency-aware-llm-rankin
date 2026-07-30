# Expanded Selective-Repair Experiments: Conflict-Aware Multi-Scorer Ranking

## Setup

- **Pipeline:** Validated fair comparison (all methods use same candidate set)
- **Datasets:** fiqa, scidocs; n=100 queries; top_k=20; mode=summed_margin
- **Scorers:** bm25, dense; optionally cross_encoder (ms-marco-MiniLM-L6-v2)
- **Methods:** bm25_raw, dense_raw, [cross_encoder_raw], rrf_fusion, greedy_fas, selective_repair (percentile-based BEW thresholds)
- **Selective repair:** RRF base; apply FAS only for top X% of queries by BEW (highest conflict)

---

## 1. Overall Results

### 2-Scorer (bm25 + dense)

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|------------|-----------|-----------------|
| fiqa | 100 | 0.255 | **0.407** | 0.349 | 0.332 | 0.335 |
| scidocs | 100 | 0.210 | **0.357** | 0.281 | 0.274 | 0.270 |

- **FiQA:** selective_top25 (0.335) < RRF (0.349). Selective does not beat RRF with 2 scorers.
- **SciDocs:** RRF (0.281) > selective (0.270) > FAS (0.274). Selective does not beat RRF.

### 3-Scorer (bm25 + dense + cross_encoder)

| Dataset | n | bm25_raw | dense_raw | cross_enc | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|-----------|------------|-----------|-----------------|
| fiqa | 100 | 0.255 | **0.407** | 0.318 | 0.339 | 0.337 | **0.361** |
| scidocs | 100 | 0.210 | **0.357** | 0.246 | 0.266 | 0.261 | 0.263 |

- **FiQA:** selective_top25 (0.361) **beats** RRF (0.339) and FAS (0.337). +6.5% over RRF.
- **SciDocs:** selective (0.263) ≈ FAS (0.261), below RRF (0.266).

---

## 2. High-BEW Subset (top 25% by conflict)

### 2-Scorer

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|------------|-----------|-----------------|
| fiqa | 25 | 0.271 | 0.379 | **0.377** | 0.321 | 0.321 |
| scidocs | 25 | 0.293 | **0.408** | 0.349 | 0.308 | 0.308 |

On high-BEW with 2 scorers, RRF or dense wins; FAS does not help.

### 3-Scorer

| Dataset | n | bm25_raw | dense_raw | cross_enc | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|-----------|------------|-----------|-----------------|
| fiqa | 25 | 0.332 | **0.408** | 0.166 | 0.281 | **0.369** | **0.369** |
| scidocs | 25 | 0.238 | **0.376** | 0.233 | 0.275 | 0.261 | 0.261 |

- **FiQA 3-scorer high-BEW:** FAS (0.369) **beats** RRF (0.281) by +31%. Dense (0.408) remains best.
- **SciDocs:** RRF (0.275) > FAS (0.261).

---

## 3. High-Disagreement Subset (top 25%)

### 2-Scorer

| Dataset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|------------|-----------|-----------------|
| fiqa | 25 | 0.141 | 0.297 | 0.225 | **0.256** | 0.240 |
| scidocs | 25 | 0.076 | 0.270 | 0.148 | **0.207** | 0.145 |

FAS beats RRF on high-disagreement when scorers disagree. Selective does not always improve.

### 3-Scorer

| Dataset | n | bm25_raw | dense_raw | cross_enc | rrf_fusion | greedy_fas | selective_top25 |
|---------|---|----------|-----------|-----------|------------|-----------|-----------------|
| fiqa | 25 | 0.148 | 0.223 | 0.149 | 0.161 | **0.266** | 0.243 |
| scidocs | 25 | 0.077 | 0.247 | 0.116 | 0.146 | 0.140 | 0.121 |

- **FiQA 3-scorer high-disagreement:** FAS (0.266) **beats** RRF (0.161) by +65%.
- **SciDocs:** RRF (0.146) > FAS (0.140).

---

## 4. Selective-Repair Summary

| Config | selective_top25 | RRF | FAS | selective beats RRF? |
|--------|-----------------|-----|-----|----------------------|
| fiqa 2-scorer | 0.335 | 0.349 | 0.332 | No |
| fiqa 3-scorer | **0.361** | 0.339 | 0.337 | **Yes (+6.5%)** |
| scidocs 2-scorer | 0.270 | 0.281 | 0.274 | No |
| scidocs 3-scorer | 0.263 | 0.266 | 0.261 | No |

---

## 5. BRIGHT / HotpotQA

Processed data (queries.jsonl, documents.jsonl, qrels.jsonl) is not present for HotpotQA or BRIGHT. They would need to be prepared with `prepare_datasets.py` and score files generated before running experiments. Skipped for this report.

---

## 6. Strict Judgment

### Does the selective-repair story hold at larger scale (100 queries)?

**Partially.** On FiQA with 3 scorers, selective repair (top 25% BEW) beats RRF and FAS overall (0.361 vs 0.339 vs 0.337). On SciDocs and with 2 scorers, it does not. The effect is dataset- and setup-dependent.

### Does it generalize beyond SciDocs?

**No.** The earlier 50-query SciDocs result (selective beating RRF) did not replicate at 100 queries with percentile-based thresholds. FiQA now shows the stronger selective-repair benefit, especially with 3 scorers, while SciDocs does not.

### Does adding a stronger scorer improve the usefulness of conflict-aware repair?

**Yes.** With 3 scorers (bm25 + dense + cross_encoder), FiQA selective repair improves over RRF: 0.361 vs 0.339. With 2 scorers, selective did not beat RRF on FiQA. More scorers create more conflict (cycles), and selective FAS helps when applied only to high-conflict queries.

### Is the work now better suited for a Q1 journal, a workshop/findings paper, or a stronger conference submission?

**Workshop/findings or short conference paper.** Reasons:

- **Strengths:** Clear methodology (validated fair comparison, selective repair), cross-encoder adds a third scorer, FiQA 3-scorer shows selective repair gains. The story is coherent: conflict-aware repair helps when many scorers disagree and when applied selectively.
- **Limitations:** Results are dataset-dependent (FiQA yes, SciDocs no). Only two datasets; no BRIGHT/HotpotQA. Selective gains are modest (6.5% over RRF on FiQA). Dense is still best overall.

**Recommendation:** A workshop or findings paper (e.g., EMNLP Findings, RepL4NLP) is appropriate. A Q1 journal would need more datasets, ablations, and stronger gains. A top-tier conference would need broader generalization and a clearer main contribution.

---

## 7. Files and Commands

- `scripts/run_expanded_selective_repair.py` — main experiment script
- `scripts/generate_cross_encoder_scores.py` — cross-encoder score generation
- Outputs: `outputs/expanded_selective/<dataset>_summary_<scorers>_n100.csv`

```bash
# 2-scorer
python scripts/run_expanded_selective_repair.py --dataset fiqa --max-queries 100 --scorers bm25,dense

# 3-scorer (requires cross_encoder.jsonl)
python scripts/generate_cross_encoder_scores.py --dataset fiqa --top-k 20 --max-queries 100
python scripts/run_expanded_selective_repair.py --dataset fiqa --max-queries 100 --scorers bm25,dense,cross_encoder
```
