# Final JIS evidence package (canonical)

This directory is the **single official evidence bundle** for drafting the Journal of Information Science manuscript **as of the repository state that produced it**. It is assembled only from **existing committed artifacts** under `outputs/pub_vote_cmp_all4/` (plus figures already produced by the publication evidence pipeline).

---

## Why this package is canonical

1. **Breadth:** It is the only committed publication-suite bundle with **four BEIR-style retrieval datasets** (SciDocs, FiQA, HotpotQA, BRIGHT), three vote constructions (`ms2`, `ms1`, `ms1_drop_mutual`), and the full triad of **aggregate graph/nDCG table**, **bootstrap ΔnDCG table**, and **qrels-aligned structural (BEW/PIC) summary**, together with per-condition analysis JSON.
2. **Internal consistency:** All files in `tables/` and `analysis/` are generated from the **same root run** (`outputs/pub_vote_cmp_all4`) via `scripts/build_paper_evidence_package.py` and the analysis scripts—unlike older bundles that disagree numerically on overlapping rows.
3. **Repository audit alignment:** `reports/repo_publication_audit.md` and `reports/canonical_results_inventory.csv` already recommend this root over `outputs/pub_vote_cmp_v2/` for a four-dataset story.

**Do not merge** rows from `pub_vote_cmp_v2`, `outputs/q1_journal_package/`, or `reports/paper_tables/table_01_repair_effects.csv` into manuscript tables without an explicit footnote that those artifacts trace to a **different committed run** (see “Conflicting packages” below).

---

## Package layout

| Path | Role |
|------|------|
| `tables/table_graph_ndcg_and_consistency.csv` | Per dataset × vote variant: cyclicity, SCC/edge structure, mean BEW/PIC pre/post, FAS weight removed, mean nDCG for hybrid methods (prior, unrepaired/repaired Copeland and balance). |
| `tables/table_bootstrap_delta_ndcg.csv` | Paired bootstrap summaries (2000 reps) for ΔnDCG (repaired − unrepaired) for Copeland and balance, including SCC-high/low strata where `n_queries > 0`. **Primary significance-style evidence for retrieval deltas in this package.** |
| `tables/table_consistency_qrels_bew.csv` | Compact qrels-aligned mean BEW/PIC pre/post and mean FAS weight removed (same interpretation caveats as in `MANUSCRIPT_SUMMARY.md`: alignment diagnostics, not independent “truth”). |
| `analysis/*.json` | Machine-readable delta payloads feeding the bootstrap table (one file per dataset × variant × {copeland, balance}). |
| `summaries/MANUSCRIPT_SUMMARY.md` | Interpretation notes copied from the paper package (conservative, no extra claims). |
| `summaries/SUMMARY_cli_table.md` | Markdown table from `scripts/summarize_publication_vote_suite.py` (means; cross-check against CSVs). |
| `figures/*.png` | Publication plots: cyclicity/SCC, bootstrap ΔnDCG, BEW pre/post, mean nDCG hybrids, and four-dataset ms1 Copeland bar chart (`fig_ndcg_copeland_ms1_four_datasets.png` from `scripts/build_manuscript_assets.py`). |

---

## Datasets included (this package)

- **SciDocs**, **FiQA**, **HotpotQA**, **BRIGHT** — as present in `table_graph_ndcg_and_consistency.csv` (query counts vary by dataset × variant; see `n_queries` column).

Large per-query CSV trees under `outputs/pub_vote_cmp_all4/{scidocs,fiqa,hotpotqa,bright}/` are **gitignored** by policy; aggregates here are the committed trace.

---

## Methods / constructions included

- **Vote constructions:** `ms2` (majority-style aggregation), `ms1` (per-ranker inclusion, high cyclicity in most datasets), `ms1_drop_mutual` (mutual 2-cycle drop post-filter).
- **Hybrid reranking family:** RRF-based hybrids with α=0.3 as in `scripts/build_paper_evidence_package.py` (`hybrid_rrf_*` method IDs in upstream per-query CSVs). Methods surfaced in the aggregate table: prior-only, unrepaired/repaired **Copeland**, unrepaired/repaired **balance** (weighted balance variant).
- **Repair:** Greedy **minimum weighted feedback arc set (FAS)**-style edge removal as implemented in the pipeline (not “exact ILP MWFAS” on real data; see `docs/SAFE_CLAIMS_FOR_PAPER.md`).

**Not in this package:** LLM pairwise judges as the preference source; Borda/score-sum as primary real-data baselines; `real_full` qrels-derived preference graphs (different protocol—see `outputs/real_full/PROVENANCE.md`).

---

## Conflicting or superseded packages (do not treat as interchangeable)

| Location | Status relative to this manuscript |
|----------|--------------------------------------|
| `outputs/pub_vote_cmp_v2/paper_package/` | **Superseded for breadth** (two datasets only). **Numerically conflicts** with `all4` on overlapping SciDocs/HotpotQA rows (nDCG scale, cyclicity %, bootstrap CIs). Cite **either** v2 **or** all4, never blend silently. |
| `outputs/q1_journal_package/` | **Stale relative to all4** unless regenerated with `scripts/generate_q1_tables.py --pub-root outputs/pub_vote_cmp_all4`. Default inputs in repo history align with **v2**-era numbers. |
| `reports/paper_tables/table_01_repair_effects.csv`, `table_05_failure_context.csv` | Derived from **q1_journal_package / v2-aligned** paths in `scripts/generate_paper_tables.py`. **Do not use** as “final” if the paper adopts **all4** as canonical (SciDocs ms1 Copeland bootstrap differs materially). |
| `outputs/real_full/` | **Different experiment family** (preference from qrels / qrels_flip vs `votes_file` publication suite). Useful as **background or appendix** with protocol caveats, not as the same headline ΔnDCG story. |
| `outputs/noise_sweep_*`, `outputs/margin_multiseed_*`, `docs/tables/*.csv` | **Synthetic / legacy** supporting material; not the four-dataset retrieval vote-graph headline. |
| `figures/graphical_abstract/` | **Optional** manuscript asset; not part of the numeric evidence chain. |

---

## How this folder was produced

- **Tables and `analysis/` JSON:** copied from `outputs/pub_vote_cmp_all4/`.
- **Figures:** copied from `outputs/pub_vote_cmp_all4/paper_package/plots/` where present, plus `fig_ndcg_copeland_ms1_four_datasets.png` generated from `tables/table_graph_ndcg_and_consistency.csv` via `scripts/build_manuscript_assets.py` (no new experiments; visualization only).

For regeneration from a fresh `pub_vote_cmp_all4` run (requires un-ignored per-query outputs and network for data), see `docs/jis_reproducibility.md`.

---

## Conservative reading hints (for authors)

- **Structural repair** (BEW/PIC movement, FAS weight removed) can be **non-zero** under `ms1` while **bootstrap ΔnDCG** is **inactive, mixed, or dataset-dependent**. This is **not** a contradiction in the metrics—it is the paper’s central empirical tension.
- On **SciDocs `ms1` Copeland**, the **all4** bootstrap interval for mean ΔnDCG **straddles zero** (see `table_bootstrap_delta_ndcg.csv`). Claims of **“statistically significant harm”** on that row are **not supported by all4**; they **were** supported by the **v2** table row (see conflict note above).
- **HotpotQA `ms1` Copeland** in all4 shows a **positive** mean Δ with a reported CI whose **lower bound is 0.0** in the committed CSV; interpret with care (and avoid over-claiming strict positivity).

---

*Packaged for JIS submission evidence freezing; see also `reports/jis_claims_mapping.md`, `docs/jis_paper_scope.md`, and `reports/jis_repo_audit.md`.*
