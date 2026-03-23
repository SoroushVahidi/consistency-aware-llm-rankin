# Final manuscript tables (JIS)

This folder holds **deduplicated**, **manuscript-oriented** copies of tables. **Primary real-data results** trace to **`outputs/pub_vote_cmp_all4`** only (see conflict notes below).

---

## Naming convention

- **`T*`** — **Main paper** (real-data publication vote suite, four datasets).
- **`A*`** — **Appendix / supplement** (synthetic, inventory, or non-headline).

---

## File list

| File | Contains | Source | Main vs appendix |
|------|----------|--------|------------------|
| `T01_main_real_vote_graph_ndcg_structural_metrics.csv` | Dataset × vote variant: `n_queries`, cyclicity %, mean largest SCC, mean edges, BEW/PIC pre/post deltas, FAS weight removed, mean nDCG for prior / unrepaired & repaired Copeland & balance hybrids. | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` | **Main** (Table 1 candidate). |
| `T02_main_real_bootstrap_delta_ndcg_pairs.csv` | Bootstrap mean ΔnDCG (repaired − unrepaired) for Copeland & balance; SCC-high/low rows where `n_queries>0`. | `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` | **Main** (Table 2 candidate — inferential summary). |
| `T03_main_real_qrels_alignment_bew_pic_pre_post.csv` | Mean BEW/PIC pre/post and FAS weight removed (qrels-aligned structural summary). | `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv` | **Main** (Table 3 candidate — structural diagnostics). |
| `A01_appendix_synthetic_multiseed_stability.csv` | Synthetic multiseed stability (margin noise sweep seeds). | `reports/paper_tables/table_03_synthetic_multiseed_stability.csv` | **Appendix** (synthetic only). |
| `A02_appendix_synthetic_noise_sweep.csv` | Synthetic noise sweep summary. | `reports/paper_tables/table_04_synthetic_noise_sweep.csv` | **Appendix** (synthetic only). |
| `A03_appendix_committed_artifact_paths.csv` | Inventory of selected committed artifact paths (existence / row counts). | `reports/paper_tables/table_06_artifact_inventory.csv` | **Supplement** (transparency / checklist). |

---

## Excluded duplicates (and why)

The following **were not copied** to avoid **contradicting** the canonical all4 bootstrap story:

| Original path | Reason |
|---------------|--------|
| `reports/paper_tables/table_01_repair_effects.csv` | Built from **`outputs/q1_journal_package`** / **v2-aligned** bootstrap inputs in `scripts/generate_paper_tables.py`. Labels **SciDocs ms1 Copeland** as **significant harm**, which **conflicts** with **`T02`** (all4 CI **straddles** zero). |
| `reports/paper_tables/table_05_failure_context.csv` | Same **v2-aligned** SciDocs ms1 row as table_01; **not** all4-consistent. |
| `reports/paper_tables/table_02_proxy_baseline_leaderboard.csv` | **Proxy / leaderboard** extract from **`outputs/real_full`** style runs—**different protocol** from the vote suite; also extremely **degenerate** nDCG values in places. Use only after **explicit** non-vote-suite framing (not copied here by default). |

Authors who **need** proxy baselines or failure-context prose should **regenerate** from the **same root** they adopt for the manuscript or import manually with **protocol footnotes**.

---

## LaTeX

No separate `.tex` table files were present in-repo for these CSVs at packaging time. Authors may use `pgfplots` / `booktabs` importers or convert CSV externally—**numbers** should match **`T01`–`T03`** byte-for-byte unless deliberately recomputed.

---

*Aligned with `outputs/final_jis_package/README.md` and `reports/jis_claims_mapping.md`.*
