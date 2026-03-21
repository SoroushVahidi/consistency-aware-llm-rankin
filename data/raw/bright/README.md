# BRIGHT — Manual Download Instructions

BRIGHT could not be downloaded automatically. Follow these steps:

1. Visit https://huggingface.co/datasets/xlangai/BRIGHT
2. Accept any required licence / access terms.
3. Install the `datasets` library if not already installed:
       pip install datasets huggingface-hub
4. Log in to HuggingFace CLI (if the dataset is gated):
       huggingface-cli login
5. Download using Python:
       from datasets import load_dataset
       ds = load_dataset("xlangai/BRIGHT", "examples")
6. Save the JSONL files to this directory:
       data/raw/bright/
   Expected files:
       queries.jsonl       — one JSON object per line:
                             {query_id|id, text|query|question}
       documents.jsonl     — one JSON object per line:
                             {doc_id|id, text, title?}
       qrels.jsonl         — one JSON object per line:
                             {query_id|query-id, doc_id|corpus-id, relevance|score}

7. Then run:
       python scripts/prepare_datasets.py --dataset bright
