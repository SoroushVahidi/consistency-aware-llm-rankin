# JIS reproducibility statement (honest, repo-aligned)

This describes what a reader **can** and **cannot** reproduce from a **checkout of this repository alone**, relative to the **canonical** evidence in `outputs/final_jis_package/` (copy of `outputs/pub_vote_cmp_all4` aggregates).

---

## What is reproducible **without network** (from committed files)

- **Read and verify** all CSV and JSON artifacts under `outputs/final_jis_package/` and `outputs/pub_vote_cmp_all4/paper_package/` and `outputs/pub_vote_cmp_all4/analysis/`.
- **Regenerate manuscript-oriented figures** that depend only on committed CSVs, e.g.  
  `python scripts/build_manuscript_assets.py --pub-root outputs/pub_vote_cmp_all4/paper_package`  
  (requires a local Python env with `matplotlib`; **no BEIR download**).
- **Re-run unit tests** after `pip install -e ".[dev]"` (see `AGENTS.md`); tests validate code integrity, not full data re-download.
- **Regenerate** some **report tables** from committed inputs via `scripts/generate_paper_tables.py` **if** its configured input paths still exist (note: several helpers target **`outputs/q1_journal_package`**, which may **not** match all4 unless paths are updated—see caveat below).

---

## What depends on **precomputed outputs** already in git

- The **publication vote suite aggregate tables** are **committed** under `outputs/pub_vote_cmp_all4/paper_package/`. They are **not** recomputed on every clone from raw per-query CSVs because:
  - Per-dataset trees `outputs/pub_vote_cmp_all4/{scidocs,fiqa,hotpotqa,bright}/**` are **gitignored** (large `*_per_query.csv` files).
- Therefore, **bit-identical regeneration** of those aggregates from **git alone** requires **re-running** the publication pipeline to recreate ignored intermediates (see next section).

---

## What depends on **external / raw datasets**

- **BEIR datasets** (SciDocs, FiQA, HotpotQA, BRIGHT) are fetched via **Hugging Face Hub** when executing real-data scripts (`scripts/run_publication_vote_suite.py`, related loaders).  
- A machine **without Hub access** cannot be assumed to recreate vote files or per-query CSVs.

---

## Commands corresponding to the **canonical** reported results (as documented in-repo)

1. **Publication vote suite (creates ignored per-query trees + `analysis/` JSON + `paper_package/`):**  
   `python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_all4`  
   (Exact CLI flags as used in the original run may vary; see `scripts/run_publication_vote_suite.py` and cluster scripts under `scripts/`.)
2. **Build tables + plots from a completed root:**  
   `python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_all4`
3. **Optional figure bundling:**  
   `python scripts/build_manuscript_assets.py --pub-root outputs/pub_vote_cmp_all4/paper_package`
4. **Q1-style aggregated tables (legacy default v2):**  
   `python scripts/generate_q1_tables.py`  
   **Caveat:** Default `--pub-root` historically points at **`outputs/pub_vote_cmp_v2`**. For alignment with **all4**, authors must pass `--pub-root outputs/pub_vote_cmp_all4` **and** ensure upstream CSV/JSON inputs exist; otherwise `outputs/q1_journal_package/` remains **stale** relative to the canonical bundle.

---

## Limitations for **full end-to-end** rerun from zip/repo alone

- **Ignored large artifacts** under each dataset subdirectory are **required** to rebuild `paper_package/` from scratch.
- **Network** for dataset download and possibly embedding/model artifacts (depending on ranker configuration in the run script) is **not optional** for a faithful rerun.
- **Numerical identity** across time is **not guaranteed** if library versions, query subsets, or score files change; the repository already documents **drift between v2 and all4** (`reports/repo_publication_audit.md`).
- **Synthetic** tables (`reports/jis_final_tables/A01_*`, `A02_*`) trace to committed `outputs/noise_sweep_*` / `outputs/margin_multiseed_*` style runs; rerunning requires executing `scripts/run_synthetic.py` loops as in `docs/REPRODUCTION_Q1.md` / `AGENTS.md`.

---

## Recommended wording for a JIS “Data and code availability” paragraph

> Aggregated result tables and analysis JSON for the four-dataset publication vote suite are **archived in the repository** under `outputs/pub_vote_cmp_all4/paper_package/` and `outputs/pub_vote_cmp_all4/analysis/`. **Per-query run artifacts** are excluded from version control by policy; reproducing those aggregates **from scratch** requires rerunning the publication suite scripts with **BEIR data access**. **Older** bundled tables under `outputs/pub_vote_cmp_v2/` and `outputs/q1_journal_package/` may **disagree numerically** with the four-dataset bundle; the manuscript uses **`outputs/final_jis_package/`** as the **canonical** snapshot.

---

*See also: `docs/REPRODUCTION_Q1.md` (broader, Q1-oriented), `outputs/real_full/PROVENANCE.md` (non-vote-suite runs).*
