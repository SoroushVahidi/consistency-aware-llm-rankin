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
| `scripts/run_publication_vote_suite.py` | Full publication vote comparison (up to four datasets; ms2 / ms1 / ms1_drop_mutual) |
| `scripts/analyze_publication_vote_deltas.py` | Bootstrap ΔnDCG (repaired − unrepaired) |
| `scripts/build_paper_evidence_package.py` | Tables + figures + `MANUSCRIPT_SUMMARY.md` under `<root>/paper_package/` |
| `scripts/generate_q1_tables.py` | Build `outputs/q1_journal_package/` from a chosen `--pub-root` (defaults to v2; use `pub_vote_cmp_all4` for four-dataset alignment) |
| `scripts/build_manuscript_assets.py` | Copy figures into `figures/manuscript/` and regenerate curated plots |
| `scripts/generate_paper_tables.py` | Build manuscript-ready CSV bundle in `reports/paper_tables/` |
| `scripts/summarize_publication_vote_suite.py` | Markdown-style aggregate table |

**Pinned evidence (in git):** `outputs/pub_vote_cmp_all4/paper_package/` (canonical breadth); `outputs/pub_vote_cmp_v2/paper_package/` (historical two-dataset run — see `reports/repo_publication_audit.md` before mixing numbers).

**Dependencies:** `datasets>=2.18,<4.0` (see `pyproject.toml`) for BEIR-style script datasets on the Hub.
