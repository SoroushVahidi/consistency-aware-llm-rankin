# TREC Robust 2004 — raw data

**Robust04** is a classic ad hoc retrieval collection. In this repo, normalized JSONL is produced via **`ir-datasets`** when available.

## Automatic export

```bash
pip install 'consistency-ranker[ir]'
python scripts/download_datasets.py --dataset robust04
```

The first successful run triggers `ir-datasets` acquisition flows; **licensing and redistribution** follow TREC / NIST and the `ir-datasets` documentation (see also the [Hugging Face ir-datasets card](https://huggingface.co/datasets/irds/trec-robust04)).

## If automation is not possible

If `ir-datasets` is not installed or downloads fail, use the message from `download_datasets.py` and place `queries.jsonl`, `documents.jsonl`, and `qrels.jsonl` here in the same schema as other BEIR-style raw exports (see `data/raw/bright/README.md` field names).

## Next step

```bash
python scripts/prepare_datasets.py --dataset robust04
```
