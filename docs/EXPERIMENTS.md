# Experiment scripts (quick index)

| Script | Purpose |
|--------|---------|
| `scripts/download_datasets.py` | Fetch raw JSONL (Hugging Face BEIR/HotpotQA/BRIGHT/MS MARCO; optional **ir-datasets** for `trec_dl_passage` / `robust04`) |
| `scripts/prepare_datasets.py` | Build processed JSONL + pairwise prefs |
| `scripts/generate_score_file.py` | BM25 / TF–IDF / MiniLM score files |
| `scripts/build_votes_file.py` | Multi-ranker vote JSONL |
| `scripts/postprocess_votes_drop_mutual_pairs.py` | Drop mutual 2-cycle vote pairs (middle-ground graph) |
| `scripts/diagnose_vote_graph_cycles.py` | Cycle / mutual-edge stats for a votes file |
| `scripts/run_real_experiment.py` | Full real-data ranking + metrics; **Markov graph** (`markov_graph`, `markov_graph_repaired`) on preference graphs; **RRF** + **CombSUM** + **`borda_fuse`** when `--score-prior-files` is set; optional **`--repair-weighting`** `plain` (default) / `metric_aware` / `both` (LambdaRank-style edge reweighting before greedy FAS; `both` adds `*_ma` methods) |
| `scripts/run_publication_vote_suite.py` | Full publication vote comparison (up to four datasets; ms2 / ms1 / ms1_drop_mutual) |
| `scripts/analyze_publication_vote_deltas.py` | Bootstrap ΔnDCG (repaired − unrepaired) |
| `scripts/build_paper_evidence_package.py` | Tables + figures + `MANUSCRIPT_SUMMARY.md` under `<root>/paper_package/`; optional `--datasets` for extra benchmarks under the same root |
| `scripts/generate_q1_tables.py` | Build `outputs/q1_journal_package/` from a chosen `--pub-root` (defaults to v2; use `pub_vote_cmp_all4` for four-dataset alignment) |
| `scripts/build_manuscript_assets.py` | Copy figures into `figures/manuscript/` and regenerate curated plots |
| `scripts/generate_paper_tables.py` | Build manuscript-ready CSV bundle in `reports/paper_tables/` |
| `scripts/summarize_publication_vote_suite.py` | Markdown-style aggregate table |

**Pinned evidence (in git):** `outputs/pub_vote_cmp_all4/paper_package/` (canonical breadth); `outputs/pub_vote_cmp_v2/paper_package/` (historical two-dataset run — see `reports/repo_publication_audit.md` before mixing numbers).

**Dependencies:** `datasets>=2.18,<4.0` (see `pyproject.toml`) for Hugging Face datasets. Optional **`ir-datasets`** (`pip install 'consistency-ranker[ir]'`) for TREC DL passage and Robust04 exports.
