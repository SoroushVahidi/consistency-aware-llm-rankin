# MS MARCO passage ranking — raw data

This directory holds **normalized JSONL** produced by `scripts/download_datasets.py` (loader `msmarco_passage`), not the original MS MARCO gzip layout.

## Automatic download (recommended)

From the repo root:

```bash
pip install 'datasets>=2.18,<4.0'
python scripts/download_datasets.py --dataset msmarco_passage --max-docs 100000 --max-queries 5000
```

The full corpus is on the order of **millions** of passages. Always set `--max-docs` (and optionally `--max-queries`) unless you intend a full export. Download **streams** from Hugging Face `BeIR/msmarco` and writes incrementally.

## References

- [MS MARCO datasets](https://microsoft.github.io/msmarco/Datasets.html)
- [Passage ranking task](https://microsoft.github.io/MSMARCO-Passage-Ranking/)

## Licensing

Use of MS MARCO data is subject to the terms published by Microsoft / the MS MARCO project; the BEIR mirror on Hugging Face is a convenience for retrieval research.

## Next step

```bash
python scripts/prepare_datasets.py --dataset msmarco_passage
```
