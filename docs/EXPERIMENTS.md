# Experiment scripts (quick index)

| Script | Purpose |
|--------|---------|
| `scripts/download_datasets.py` | Fetch raw JSONL from Hugging Face |
| `scripts/prepare_datasets.py` | Build processed JSONL + pairwise prefs |
| `scripts/generate_score_file.py` | BM25 / TF–IDF / MiniLM score files |
| `scripts/build_votes_file.py` | Multi-ranker vote JSONL |
| `scripts/postprocess_votes_drop_mutual_pairs.py` | Drop mutual 2-cycle vote pairs (middle-ground graph) |
| `scripts/diagnose_vote_graph_cycles.py` | Cycle / mutual-edge stats for a votes file |
| `scripts/run_real_experiment.py` | Full real-data ranking + metrics |
| `scripts/run_publication_vote_suite.py` | SciDocs + HotpotQA publication comparison (ms2 / ms1 / drop-mutual) |
| `scripts/analyze_publication_vote_deltas.py` | Bootstrap ΔnDCG (repaired − unrepaired) |
| `scripts/build_paper_evidence_package.py` | Tables + figures + `MANUSCRIPT_SUMMARY.md` |
| `scripts/summarize_publication_vote_suite.py` | Markdown-style aggregate table |

**Pinned evidence (in git):** `outputs/pub_vote_cmp_v2/paper_package/` (regenerate commands in that folder’s README).

**Dependencies:** `datasets>=2.18,<4.0` (see `pyproject.toml`) for BEIR-style script datasets on the Hub.
