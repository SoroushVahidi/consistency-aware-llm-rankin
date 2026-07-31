# Reasoning-Heavy Benchmark Feasibility: HotpotQA and BRIGHT

## Current State

### HotpotQA
- **Loader:** `src/consistency_ranker/data/hotpotqa_loader.py` — `download_hotpotqa()` loads from HuggingFace `hotpot_qa` (fullwiki)
- **Download:** `scripts/download_datasets.py --dataset hotpotqa` — writes queries.jsonl, documents.jsonl, qrels.jsonl to `data/raw/hotpotqa/`
- **Prepare:** `scripts/prepare_datasets.py --dataset hotpotqa` — converts to processed format
- **Registry:** `hotpotqa` in dataset_registry with `processed_path=data/processed/hotpotqa/`
- **Status:** No raw or processed files present. Download and prepare not yet run.

### BRIGHT
- **Loader:** `src/consistency_ranker/data/bright_loader.py` — `download_bright()` attempts HuggingFace `xlangai/BRIGHT` (task, e.g. biology)
- **Download:** `scripts/download_datasets.py --dataset bright` — may fail with `BrightNotAvailableError` (gated/licensed dataset)
- **Prepare:** `scripts/prepare_datasets.py --dataset bright` — expects raw files
- **Registry:** `bright` with `processed_path=data/processed/bright/`
- **Status:** No raw or processed files. BRIGHT may require manual download and/or HuggingFace login.

---

## What Is Missing

| Step | HotpotQA | BRIGHT |
|------|----------|--------|
| Download raw | `download_datasets.py --dataset hotpotqa` | `download_datasets.py --dataset bright` (or manual) |
| Prepare processed | `prepare_datasets.py --dataset hotpotqa` | `prepare_datasets.py --dataset bright` |
| BM25 scores | `generate_bm25_scores.py` — needs dataset support | Same — needs `choices` in script |
| Dense scores | `generate_dense_scores.py` — needs dataset support | Same |
| Paper-ready pipeline | `run_paper_ready_experiments.py` — uses `get_config(dataset)` | Same — registry has `bright` |

**Code changes needed:**
1. **generate_bm25_scores.py** — add `hotpotqa` and `bright` to `choices`
2. **generate_dense_scores.py** — add `hotpotqa` and `bright` to `choices`
3. **generate_cross_encoder_scores.py** — add to `choices` if using 3-scorer
4. **Dataset schema** — HotpotQA/BRIGHT may have different document structure (e.g. title+text). Loaders already produce `Document` with `doc_id`, `text`, `title`. BM25/dense use `text`; should work if schema matches.

---

## Estimated Effort

| Task | HotpotQA | BRIGHT |
|------|----------|--------|
| Download + prepare | ~30 min (if HuggingFace works) | 1–2 hr (manual if gated) |
| Extend BM25/dense scripts | ~15 min (add 2 dataset names) | Same |
| Run small subset (50 queries) | ~1 hr (BM25 + dense gen) | Same |
| Full pipeline run | ~2 hr | Same |

**Total for small subset:** ~2–3 hr for HotpotQA; ~3–4 hr for BRIGHT if manual download needed.

---

## Small Subset Experiment: Realistic Now?

**Yes, for HotpotQA.** Steps:
1. `python scripts/download_datasets.py --dataset hotpotqa --max-queries 100 --max-docs 5000`
2. `python scripts/prepare_datasets.py --dataset hotpotqa`
3. Add `hotpotqa` to `generate_bm25_scores.py` and `generate_dense_scores.py` choices
4. Generate BM25 and dense scores
5. Run `run_paper_ready_experiments.py --dataset hotpotqa --max-queries 50`

**For BRIGHT:** Depends on download. If `download_bright` works, same flow. If gated, manual download + file placement required.

---

## Which Is the Better Next Target?

| Criterion | HotpotQA | BRIGHT |
|-----------|----------|--------|
| **Reasoning-heavy** | Multi-hop QA; needs reasoning over multiple docs | Explicitly designed for implicit reasoning |
| **Retrieval setup** | Fullwiki: retrieve from 5M+ Wikipedia passages | Task-specific corpora (e.g. biology) |
| **Ease of integration** | HuggingFace `hotpot_qa`; typically no gating | May be gated; manual steps possible |
| **Schema fit** | Query = question; doc = passage; qrels from supporting facts | Query = question; doc = passage; similar |
| **Corpus size** | Very large (fullwiki) | Smaller per-task corpora |
| **Existing use in IR** | Common in retrieval benchmarks | Newer, less common |

**Recommendation: HotpotQA first.** Lower friction (no gating), well-known benchmark, and multi-hop nature fits a “reasoning-heavy” setting. BRIGHT is more explicitly reasoning-focused but has higher setup cost. Run HotpotQA with a small subset (50–100 queries, limited docs) to validate the pipeline, then add BRIGHT if needed.
