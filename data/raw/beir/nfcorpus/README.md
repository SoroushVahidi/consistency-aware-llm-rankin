# NFCorpus (BEIR) — raw data

NFCorpus is a biomedical retrieval benchmark in the [BEIR](https://openreview.net/forum?id=wCu6T5xFjeJ) family.

## Automatic download

```bash
pip install 'datasets>=2.18,<4.0'
python scripts/download_datasets.py --dataset nfcorpus
```

Source: Hugging Face `BeIR/nfcorpus` and `BeIR/nfcorpus-qrels`.

## References

- [NFCorpus (Heidelberg)](https://www.cl.uni-heidelberg.de/statnlpgroup/nfcorpus/)

## Next step

```bash
python scripts/prepare_datasets.py --dataset nfcorpus
```
