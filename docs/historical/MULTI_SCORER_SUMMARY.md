# Multi-Scorer Preference Aggregation

## Summary of Changes

### Files Modified

| File | Changes |
|------|---------|
| `src/consistency_ranker/data/unified_loader.py` | Added `preferences_from_multiple_score_rankings()`, `load_multi_scorer_rankings()`, and docstring updates |
| `scripts/run_real_experiment.py` | Added `--preference-source multi_scores`, `--scorers`, `--multi-score-weight-mode`; integrated multi-scorer loading and preference generation |
| `tests/test_data_pairwise.py` | Added `TestPreferencesFromMultipleScoreRankings` with 10 tests |

### New Functions

- **`preferences_from_multiple_score_rankings(query_id, scorer_rankings, weight_mode, min_margin)`**  
  Aggregates rankings from multiple scorers into pairwise preferences. Supports `majority_vote`, `summed_margin`, and `vote_plus_margin`.

- **`load_multi_scorer_rankings(scorer_paths)`**  
  Loads score rankings from multiple JSONL files. Returns `{scorer_name: {query_id: [(doc_id, score), ...]}}`. Missing files are skipped.

---

## Score File Expectations

### Location

Per-scorer score files live at:

```
data/processed/<dataset>/scores/<scorer_name>.jsonl
```

Examples:
- `data/processed/beir/fiqa/scores/bm25.jsonl`
- `data/processed/beir/fiqa/scores/dense.jsonl`
- `data/processed/beir/fiqa/scores/cross_encoder.jsonl`

### Format

Each line is a JSON object matching `CandidateRanking`:

```json
{"query_id": "q1", "ranked_doc_ids": ["d1", "d2", "d3"], "scores": [0.92, 0.71, 0.45]}
```

- `query_id`: string
- `ranked_doc_ids`: list of document IDs, best first
- `scores`: list of scalar scores, same length as `ranked_doc_ids`

### Requirements

- At least **2** scorer files must exist for `multi_scores` to run.
- Scorers can have different candidate sets; the union is used. For each pair `(i, j)`, only scorers that contain **both** docs contribute.
- Queries must appear in **all** loaded scorers to be eligible.

---

## Example Command

```bash
python scripts/run_real_experiment.py \
  --dataset fiqa \
  --preference-source multi_scores \
  --scorers bm25,dense \
  --multi-score-weight-mode majority_vote \
  --max-queries 50 \
  --top-k 20
```

With a cross-encoder:

```bash
python scripts/run_real_experiment.py \
  --dataset scidocs \
  --preference-source multi_scores \
  --scorers bm25,dense,cross_encoder \
  --multi-score-weight-mode vote_plus_margin \
  --max-queries 50
```

---

## Why Multi-Scorer Can Create Cycles

Each scorer alone produces a **total order** (transitive preferences): if A>B and B>C, then A>C. So a single scorer yields a DAG and no cycles.

When we **aggregate** multiple scorers:

- Scorer 1: A > B > C  
- Scorer 2: B > C > A  
- Scorer 3: C > A > B  

For pair (A,B): 2 vote A>B, 1 votes B>A → edge A→B  
For pair (B,C): 2 vote B>C, 1 votes C>B → edge B→C  
For pair (C,A): 2 vote C>A, 1 votes A>C → edge C→A  

Result: A→B→C→A, a **cycle**. Each scorer is transitive, but their majority votes can be intransitive. Consistency-aware reranking (greedy FAS) can then repair these cycles.

---

## Aggregation Modes

| Mode | Direction | Weight |
|------|-----------|--------|
| `majority_vote` | Majority of scorers | Number of votes for winner |
| `summed_margin` | Sign of sum of (score_i - score_j) across scorers | Absolute summed margin |
| `vote_plus_margin` | Majority | Votes + mean margin from agreeing scorers |
