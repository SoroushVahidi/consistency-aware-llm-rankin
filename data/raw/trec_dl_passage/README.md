# TREC Deep Learning track — passage ranking (raw)

This benchmark is **judged qrels and topics** layered on **MS MARCO-style passage ids**. The repo exports topics, qrels, and **only the passage texts needed for judged documents** (not the full MS MARCO corpus).

## Prerequisites

1. Optional dependency:

   ```bash
   pip install 'consistency-ranker[ir]'
   ```

2. **MS MARCO passage store (optional but typical):** you can reuse `data/raw/msmarco_passage/documents.jsonl` from `msmarco_passage` so passage text for judged doc ids does not require a second full download. See `scripts/download_datasets.py --help` for `--trec-dl-docs-from-msmarco` and `--trec-dl-year` (2019 or 2020).

## Automatic export (ir-datasets)

```bash
pip install 'consistency-ranker[ir]'
python scripts/download_datasets.py --dataset trec_dl_passage --trec-dl-year 2019
```

If `ir-datasets` cannot download (network, NIST/TREC terms, or missing cache), the script prints instructions and may leave a placeholder note in this directory.

## References

- [TREC DL overview (browser)](https://pages.nist.gov/trec-browser/trec28/deep/overview)
- [NIST DL track](https://www.nist.gov/publications/overview-trec-2019-deep-learning-track)

## Next step

```bash
python scripts/prepare_datasets.py --dataset trec_dl_passage
```
