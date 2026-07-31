# Read this first (for humans and AI assistants)

> **SUPERSEDED as the primary AI-orientation entry point (2026-07-31).**
> This file's role is now filled by **`docs/AGENT_GUIDE.md`** (operational
> "what to do") and **`docs/CONTRIBUTIONS.md`** (what exists and its
> status) — read those first. This file's code-map (§5) and environment
> notes (§7) below remain accurate and are kept for reference, but do not
> use §1-4/§6 as your primary orientation; they duplicate, with slightly
> different framing, information `docs/CONTRIBUTIONS.md` now maintains
> canonically.

**This file is being reconciled with `../PROJECT_STATUS.md`, which now
self-declares as "the canonical entry point for humans and agents" and
should be read first if the two ever disagree — re-verify against Git/code
directly per that file's own instructions rather than trusting either
document blindly.** The orientation below still describes the repository's
code layout accurately; the *evidence* pointers in step 2 were stale (still
pointing at a March-2026 pipeline the current manuscript does not use) and
have been corrected in place, 2026-07-30, as part of a repository hygiene
pass (`reports/repo_hygiene_audit_20260729T235053Z/`).

This repository is a **research codebase** for *consistency-aware ranking* from pairwise preferences using **graph repair** (Minimum Weighted Feedback Arc Set, MWFAS).

## Fast orientation (5 minutes)

1. **What the paper claims (safely)**  
   See [`Q1_POSITIONING_AND_CLAIMS.md`](Q1_POSITIONING_AND_CLAIMS.md) — written for the historical `pub_vote_cmp_*` package (see item 2); not yet re-validated against the current `full_calibrated_core` evidence base.

2. **Where the current real-data evidence lives**
   - **Current classical-study canonical evidence** (backs the submitted
     `papers/JDIQ_2026/manuscript/main.tex`, four datasets: SciDocs, FiQA,
     HotpotQA, BRIGHT):
     [`../reports/full_calibrated_core/`](../reports/full_calibrated_core/),
     extended by
     [`../reports/normalization_protocol_audit_20260714/`](../reports/normalization_protocol_audit_20260714/),
     [`../reports/candidate_pool_conditional_audit_20260714/`](../reports/candidate_pool_conditional_audit_20260714/),
     and the larger-pool/exact-repair/baseline-fairness families cited in
     [`../reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md`](../reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md).
     See [`REPRODUCTION_CANONICAL.md`](REPRODUCTION_CANONICAL.md) for the exact
     pipeline map and reproduction commands.
   - **Current real-LLM exploratory evidence** (small, 6-real-query pilot;
     SciDocs + FiQA only; Azure/Gemini/Cohere/Fireworks pairwise judgments):
     [`../reports/repair_frontier_20260729T144742Z/`](../reports/repair_frontier_20260729T144742Z/),
     [`../reports/extraction_study_20260729T151610Z/`](../reports/extraction_study_20260729T151610Z/),
     [`../reports/repair_diagnostic_20260729T162748Z/`](../reports/repair_diagnostic_20260729T162748Z/).
     Read this as *directional*, not a second large-*n* confirmatory study —
     see
     [`../reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md`](../reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md).
   - **Historical evidence package** (earlier phase of this project, last
     regenerated 2026-03-24; **not** referenced by the current manuscript):
     [`../outputs/pub_vote_cmp_all4/paper_package/`](../outputs/pub_vote_cmp_all4/paper_package/)
     (four datasets) and
     [`../outputs/pub_vote_cmp_v2/paper_package/`](../outputs/pub_vote_cmp_v2/paper_package/)
     (two datasets, older still). Kept for historical/ablation comparison
     only — do not cite as the paper's current evidence.

3. **Manuscript-ready figures (curated copy in repo root)**  
   See [`../figures/manuscript/README.md`](../figures/manuscript/README.md) and [`../figures/graphical_abstract/README.md`](../figures/graphical_abstract/README.md).

4. **How to reproduce**
   [`REPRODUCTION_CANONICAL.md`](REPRODUCTION_CANONICAL.md) — the current
   guide, covering every table cited in `main.tex`.
   [`REPRODUCTION_Q1.md`](REPRODUCTION_Q1.md) reproduces the historical
   package only (item 2 above) and is kept for historical reference; do not
   follow it expecting the current manuscript's numbers.
   [`EXPERIMENTS.md`](EXPERIMENTS.md) is a general script index, still current.

5. **Code map**  
   - Core library: `src/consistency_ranker/`  
   - MWFAS: `greedy_fas.py`, `mwfas_solver.py` (greedy + exact ILP via the free, open-source
     **SCIP**/PySCIPOpt solver — `method="scip"`/`"exact"`/`"ilp"`, no license required; a
     `method="gurobi"` legacy backend also exists but is never required); optional
     **metric-aware** reweighting before FAS: `metric_aware_repair.py`,
     `scripts/run_real_experiment.py --repair-weighting …`  
   - Datasets: `data/dataset_registry.py`, loaders under `data/`  
   - Publication pipeline: `scripts/run_publication_vote_suite.py` → `build_paper_evidence_package.py`

6. **Evidence audit (claims vs evidence)**
   - [`../reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md`](../reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md) — **current** integrated audit (classical `full_calibrated_core` backbone + real-LLM exploratory studies)
   - [`../reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md`](../reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md) — independent meta-audit of the above
   - [`../reports/_archive/publication_audit_20260406/repo_publication_audit.md`](../reports/_archive/publication_audit_20260406/repo_publication_audit.md) — **historical** (2026-04-06) canonical-package recommendation for the now-superseded `pub_vote_cmp_all4`/`v2` split; kept for provenance (moved to `_archive/` in repo Stage 2, 2026-07-30)
   - [`../reports/README.md`](../reports/README.md) — index of CSV/claim matrices (see its own historical banner)

7. **Environment notes (exact solver)**
   - The canonical exact MWFAS solver is free and open-source: `pip install
     "consistency-ranker[exact]"` (installs PySCIPOpt/SCIP). No license or environment
     variables needed.
   - A `method="gurobi"` legacy backend exists only for users who already have a licensed
     Gurobi install; it is never required and no test or reproduction step depends on it.
     If you do use it, do **not** point `GRB_LICENSE_FILE` at an expired license file if
     the default works.

## What not to confuse

- **Code support for a dataset** ≠ **local raw/processed files present** — data must be downloaded/prepared (see `README.md`).
- **Registry ids** include `nfcorpus`, `msmarco_passage`, `trec_dl_passage`, `robust04` (see `src/consistency_ranker/data/dataset_registry.py`). `trec_dl_passage` and `robust04` need optional **ir-datasets** for automated download; MS MARCO passage uses a **streamed** cap via `--max-docs`.
- **Stub vs exact:** `mwfas_solver.solve(..., method="ilp")` (aliases: `"exact"`, `"scip"`) is a **real** linear-ordering MIP solved by the free, open-source SCIP solver (not a stub, and not tied to Gurobi — `method="gurobi"` is a separate, optional legacy backend).
