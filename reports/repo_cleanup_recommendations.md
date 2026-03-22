# Repository cleanup recommendations (publication coherence)

## Priority 1 — Single numerical truth for the paper

1. **Pick one publication root** for all manuscript numbers: **`outputs/pub_vote_cmp_all4/paper_package/`** (broadest coverage: four datasets, same scripts as v2).
2. **Regenerate** `outputs/q1_journal_package/` with:
   ```bash
   python scripts/generate_q1_tables.py --pub-root outputs/pub_vote_cmp_all4 --out-dir outputs/q1_journal_package
   ```
   so `summary_report.md` and CSVs **match** the four-dataset package (currently defaults to **v2**).
3. **Update** `docs/SAFE_CLAIMS_FOR_PAPER.md` and `docs/RESULTS_FOR_PAPER.md` to cite **`pub_vote_cmp_all4`** tables, or add a banner: *“Numeric examples in §1 refer to `pub_vote_cmp_v2` unless updated; see `reports/repo_publication_audit.md`.”*

## Priority 2 — Explain v2 vs all4 divergence

4. Add **`reports/PROVENANCE_pub_runs.md`** (or extend `outputs/real_full/PROVENANCE.md` pattern) documenting:
   - commit hash / date of each `run_publication_vote_suite.py` invocation
   - CLI flags: `--max-queries`, `--top-k`, rankers, seeds
   - why **SciDocs ms1** ΔnDCG differs between v2 and all4 (different score files, code version, or candidate pool).
5. **`.gitignore`** currently omits per-dataset trees under `pub_vote_cmp_all4/*/`. For **full reproducibility**, either:
   - commit a **`run_manifest.json`** + **hashes** of score/vote files, or
   - document that **paper_package CSVs** are the reproducible artifact and full reruns require regenerating ignored intermediates.

## Priority 3 — Documentation hygiene

6. Set **`README.md` “Key finding”** to cite **only** the chosen canonical package path (avoid mixing v2 and all4 numbers in one sentence).
7. Archive **`outputs/pub_vote_cmp_v2/paper_package/`** as **historical** in README (already partially done)—consider renaming folder to `pub_vote_cmp_v2_legacy` only if links updated everywhere.

## Priority 4 — Tests / CI

8. Add a **smoke test** that `table_graph_ndcg_and_consistency.csv` and `table_bootstrap_delta_ndcg.csv` **parse** and have **expected columns** (no numeric assertions unless golden file chosen).

## Non-goals

- Do not delete v2 outputs until the paper explicitly migrates; keep for comparison audits.
