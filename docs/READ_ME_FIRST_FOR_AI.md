# Read this first (for humans and AI assistants)

This repository is a **research codebase** for *consistency-aware ranking* from pairwise preferences using **graph repair** (Minimum Weighted Feedback Arc Set, MWFAS).

## Fast orientation (5 minutes)

1. **What the paper claims (safely)**  
   See [`Q1_POSITIONING_AND_CLAIMS.md`](Q1_POSITIONING_AND_CLAIMS.md).

2. **Where the latest real-data evidence lives**  
   - **Four-dataset publication package (SciDocs, FiQA, HotpotQA, BRIGHT):**  
     [`../outputs/pub_vote_cmp_all4/paper_package/`](../outputs/pub_vote_cmp_all4/paper_package/)  
   - **Tables:** `table_graph_ndcg_and_consistency.csv`, `table_bootstrap_delta_ndcg.csv`, `table_consistency_qrels_bew.csv`  
   - **Plots:** `paper_package/plots/*.png`  
   - **Narrative summary:** `paper_package/MANUSCRIPT_SUMMARY.md`  
   - **Older two-dataset package (historical):** [`../outputs/pub_vote_cmp_v2/paper_package/`](../outputs/pub_vote_cmp_v2/paper_package/)

3. **Manuscript-ready figures (curated copy in repo root)**  
   See [`../figures/manuscript/README.md`](../figures/manuscript/README.md) and [`../figures/graphical_abstract/README.md`](../figures/graphical_abstract/README.md).

4. **How to reproduce**  
   [`REPRODUCTION_Q1.md`](REPRODUCTION_Q1.md) and [`EXPERIMENTS.md`](EXPERIMENTS.md).

5. **Code map**  
   - Core library: `src/consistency_ranker/`  
   - MWFAS: `greedy_fas.py`, `mwfas_solver.py` (exact **Gurobi** ILP + greedy)  
   - Datasets: `data/dataset_registry.py`, loaders under `data/`  
   - Publication pipeline: `scripts/run_publication_vote_suite.py` → `build_paper_evidence_package.py`

6. **Publication audit (claims vs evidence)**  
   - [`../reports/repo_publication_audit.md`](../reports/repo_publication_audit.md) — canonical package, v2 vs all4, safe framing  
   - [`../reports/README.md`](../reports/README.md) — index of CSV/claim matrices

7. **Environment notes (Wulver / cluster)**  
   - Use conda env `feedback-weighted-maximization` when running Gurobi-backed exact solver.  
   - Do **not** point `GRB_LICENSE_FILE` at an expired license file if the default works.

## What not to confuse

- **Code support for a dataset** ≠ **local raw/processed files present** — data must be downloaded/prepared (see `README.md`).
- **Stub vs exact:** `mwfas_solver.solve(..., method="ilp")` is a **real Gurobi** formulation (not a stub), subject to solver availability.

## Session / audit notes (optional)

- [`WULVER_EXECUTION_SUMMARY.md`](WULVER_EXECUTION_SUMMARY.md) — what was run on Wulver and what was pushed.
- [`PAPER_PACKAGE_STATUS_AFTER_WULVER.md`](PAPER_PACKAGE_STATUS_AFTER_WULVER.md) — four-dataset package status.
- [`../reports/repo_cleanup_recommendations.md`](../reports/repo_cleanup_recommendations.md) — optional repo coherence steps (e.g. regenerate Q1 tables from `pub_vote_cmp_all4`).
