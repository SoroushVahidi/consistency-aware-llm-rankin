---
license: cc-by-4.0
language: en
tags:
- information-retrieval
- ranking
- ndcg
- research-results
pretty_name: Larger-Pool Ranking nDCG Results
---

# Larger-Pool Ranking nDCG Results (v1.0.0)

**Creator:** Soroush Vahidi. **Version:** 1.0.0, 2026. This is a numerical supplement to the submitted *SN Computer Science* manuscript “Structural Consistency Does Not Reliably Predict Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval.” The supplement itself is not represented as journal-reviewed or accepted.

The release contains **93,504 original nDCG measurements** for 16 ranking methods over 66 larger-pool configurations and **342 selected benchmark queries** (SciDocs 120, FiQA-2018 120, HotpotQA 52, BRIGHT 50). There are 5,844 query-configuration units; those repeated views are not independent trials. The public pair-metrics table reports other method keys and selected comparisons. This release gives access to completed, previously unpublished method-level results; it does not claim new experiments or a positive repair effect.

## Data and use

`data/novel_ndcg.csv.gz` is the 93,504-row result table. `data/configurations.csv` gives the 66 cell definitions. `validation/summary_reproduction.csv` gives 1,056 method-by-cell summaries. `comparison/public_vs_new.csv.gz` records the scoped public-overlap check; it is not another measurement table. See [SCHEMA.md](SCHEMA.md), [REPRODUCE.md](REPRODUCE.md), and [RIGHTS_AND_ATTRIBUTION.md](RIGHTS_AND_ATTRIBUTION.md).

Each result is candidate-set-relative nDCG@k, computed with gain `2^relevance - 1`; values are paired within query and configuration. The original cohort required complete stored retrieval scores. Eighteen of 360 target queries lacked usable depth, leaving 342. Rows within a query share source judgments and are correlated. The original historical run had a dirty source tree; a later clean implementation reproduced 66/66 cells and 93,504/93,504 exact keyed values. The clean run does not reconstruct the historical dirty tree or eight historically unhashed processed inputs.

The tables contain numerical results, configuration metadata and deterministic query-ID hashes. They contain no benchmark question/answer text, corpus documents, qrels, rankings, raw query/document IDs, model prompts or responses. Hashes can be linked to public source IDs; they are not anonymization. Obtain benchmark source material separately under its own terms.

**Licenses:** Soroush Vahidi's original data, analyses, metadata and documentation in this directory are CC BY 4.0; the original validation script is MIT. Neither license grants rights to third-party benchmark data. `LICENSE-DATA`, `LICENSE-CODE` and `RIGHTS_AND_ATTRIBUTION.md` define the scope.

**Recommended citation:** Soroush Vahidi (2026), *Larger-Pool Ranking nDCG Results*, version 1.0.0, numerical supplement to “Structural Consistency Does Not Reliably Predict Retrieval Utility,” https://github.com/SoroushVahidi/consistency-aware-llm-rankin/tree/ranking-pool-ndcg-v1.0.0/datasets/ranking-pool-ndcg-results/v1.0.0 . No DOI has been assigned to this supplement.

**Distributions of this same release:** [GitHub canonical directory](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/tree/ranking-pool-ndcg-v1.0.0/datasets/ranking-pool-ndcg-results/v1.0.0), [Hugging Face dataset](https://huggingface.co/datasets/SoroushVahidi/ranking-pool-ndcg-results), [Kaggle distribution mirror](https://www.kaggle.com/datasets/soroushvahidi/ranking-pool-ndcg-results). These are three distributions of one historical research dataset, not three independent studies.
