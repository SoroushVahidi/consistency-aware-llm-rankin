# Pinned inputs and research-use boundaries

This protocol uses existing local academic compute and official cached data;
no commercial inference API, paid cloud allocation, model fine-tuning, or raw
data/model-response publication. Benchmark labels are evaluation references,
not evidence that unjudged documents are semantically irrelevant.

## Model

Qwen/Qwen2.5-7B-Instruct:
`a09a35458c702b33eeacc393d103063234e8bc28`.
The complete local snapshot is independently pinned, rather than described
as the earlier campaign's different revision. Official public model metadata
and Apache-2.0 LICENSE are checked; each cached weight is SHA-256-checked against
the exact revision's official LFS identity. Tokenizer, vocabulary, chat template,
configuration and generation defaults are hashed too. BF16, no quantization or
remote code. The model is from 2024, so this is prospective query/acquisition
replication with one model, not a frontier-model or model-diversity benchmark.

Official sources:

- https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/tree/a09a35458c702b33eeacc393d103063234e8bc28
- https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/a09a35458c702b33eeacc393d103063234e8bc28/LICENSE

## Dataset identities

| Source | Immutable revision | Evaluation contract |
|---|---|---|
| BeIR/fiqa | 979c07a7cb5ccc6ca009792241fa1250b98055dd | Full short-document corpus; official test query IDs |
| BeIR/fiqa-qrels | 252958f2d646e22cab6d0c72dd3f0d5de6d0655a | Test qrels only; no train/test pooling |
| BeIR/scidocs | acebceec772628c6679d76d6cff30ad517d17f4e | Full corpus and official test query IDs |
| BeIR/scidocs-qrels | 735ea1048e37b1ebce14c6dc3d33a5edaf66d3dc | Official test qrels |
| xlangai/BRIGHT | 3066d29c9651a576c8aba4832d249807b181ecae | Earth science/economics short documents, gold_ids and excluded_ids |

The BEIR mirror cards declare CC-BY-SA-4.0; original content conditions still
apply. In particular FiQA's source noncommercial condition is not overridden
by mirror metadata. This is noncommercial academic research, with all source
text/qrels and prompts/responses retained privately; no redistribution is
authorized by this task. BRIGHT's card declares CC-BY-4.0; preserve attribution
and source notices. Runtime metadata receipts bind the official revision;
cached Arrow SHA-256 receipts bind the exact local bytes, not a claim of
re-downloading and independently transforming all source data.

No HotpotQA arm: the existing local conversion lacks a verified matching
official retrieval corpus/qrels identity. No synthetic substitute for benchmark
queries or outcomes. The 12 synthetic content canaries are transparently
labelled development instrumentation only, not retrieval evidence.

If an item-specific rights conflict is discovered, stop that version rather
than changing sample membership, silently substituting data or publishing raw
material. Later publication/sharing requires content-specific review.
