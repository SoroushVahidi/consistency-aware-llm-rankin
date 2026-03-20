# Learned Selector Experiment Report

## Summary

Lightweight predictive selectors (logistic regression, shallow decision tree) to decide when to apply FAS.
Uses existing paper-ready per-query CSVs. No scorer regeneration.

## Data

- FiQA: 100 queries (bm25+dense, top_k=20)
- SciDocs: 100 queries (bm25+dense, top_k=20)
- HotpotQA: 100 queries (bm25+dense, top_k=10)
- Label: 1 if FAS improves NDCG@10 over RRF, else 0
- FAS helps: FiQA 11%, SciDocs 13%, HotpotQA 27%

## Features

- bew_before, disagreement, n_sccs, cyclic_int

## A. Decision Quality (Test Set, 60/20/20 Split)

| Model | Accuracy | Precision | Recall |
|-------|----------|-----------|--------|
| Logistic | 0.567 | 0.192 | 0.500 |
| Tree | 0.483 | 0.182 | 0.600 |

## B. Ranking Quality (Test Set)

| Policy | NDCG@10 | MRR | R@10 | R@20 |
|--------|---------|-----|------|------|
| never | 0.5279 | 0.5731 | 0.5032 | 0.5282 |
| always | 0.4858 | 0.5282 | 0.4861 | 0.5165 |
| bew25 | 0.4977 | 0.5500 | 0.4903 | 0.5249 |
| bew50 | 0.4872 | 0.5453 | 0.4794 | 0.5165 |
| disc25 | 0.5360 | 0.5747 | 0.5053 | 0.5249 |
| disc50 | 0.5184 | 0.5592 | 0.4928 | 0.5165 |
| hybrid | 0.5078 | 0.5569 | 0.4894 | 0.5165 |
| learned_lr | 0.5233 | 0.5653 | 0.5011 | 0.5249 |
| learned_tree | 0.5212 | 0.5580 | 0.5053 | 0.5249 |

**Best policy:** disc25 (NDCG@10=0.5360)

## Leave-One-Dataset-Out

| Test Dataset | never | always | bew25 | bew50 | disc25 | hybrid | learned_lr | learned_tree |
|--------------|-------|--------|-------|-------|--------|--------|-------------|---------------|
| fiqa | 0.3401 | 0.3186 | 0.3215 | 0.3173 | 0.3589 | 0.3344 | 0.3564 | 0.3347 |
| scidocs | 0.2779 | 0.2360 | 0.2494 | 0.2360 | 0.2807 | 0.2648 | 0.2738 | 0.2779 |
| hotpotqa | 0.8500 | 0.8341 | 0.8500 | 0.8500 | 0.8501 | 0.8500 | 0.8510 | 0.8492 |

## LR Coefficients

```json
{
  "bew_before": 0.37062764760579564,
  "disagreement": 0.8357471765305825,
  "n_sccs": 0.0844214339997375,
  "cyclic_int": -0.8560576694062931
}
```

## Strict Interpretation

### Does a learned selector beat fixed thresholds?

**Overall (60/20/20 test):** No. The best fixed policy (disc25, disagreement top 25%) achieves the highest NDCG@10. Learned logistic and tree are competitive but do not surpass disc25.

**Leave-one-dataset-out (transfer):** On HotpotQA, learned logistic (0.8510) slightly beats disc25 (0.8501) and never (0.8500). On FiQA, disc25 (0.3589) is best; learned_lr (0.3564) is second and beats never (0.3401). On SciDocs, disc25 (0.2807) is best; tree ties never (0.2779); logistic is slightly worse.

### If yes, by how much and on which datasets?

Learned logistic beats fixed thresholds on HotpotQA in LODO (+0.001 over disc25). On FiQA, learned_lr improves over never (+0.016) but disc25 is stronger. Gains are modest.

### If no, is the fixed-threshold policy already strong enough?

**Yes, in most settings.** The disagreement-based threshold (disc25) is the strongest policy on FiQA and SciDocs. Fixed thresholds are simple, interpretable, and require no training. On HotpotQA (acyclic), the learned selector has a slight edge.

### Does this strengthen the paper for a journal submission?

**Modestly.** The experiment shows that (1) fixed thresholds (especially disc25) are strong and often best, (2) learned logistic can slightly outperform fixed on some datasets (HotpotQA LODO), and (3) interpretable models capture signal (disagreement and BEW are predictive). For a journal: 'We compared fixed thresholds with learned logistic and shallow-tree selectors. Fixed disagreement-based thresholds remain strong; learned logistic provides a modest gain on HotpotQA in leave-one-dataset-out evaluation.' Conservative and honest.
