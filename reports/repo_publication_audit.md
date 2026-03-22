# Publication-readiness audit (repository evidence)

**Audit date:** 2026-03-22 (generated from committed files in-repo).  
**Auditor role:** Conservative; no numbers below are invented—all cited paths exist in git unless noted.

---

## Executive summary

| Question | Answer |
|----------|--------|
| **Recommended canonical package** | `outputs/pub_vote_cmp_all4/paper_package/` |
| **Why** | Only committed bundle with **four datasets** (SciDocs, FiQA, HotpotQA, BRIGHT), **three vote variants** (ms2, ms1, ms1_drop_mutual), and **paired** tables: graph/nDCG + bootstrap ΔnDCG + BEW/PIC. |
| **Reproducibility caveat** | Large per-dataset run trees under `outputs/pub_vote_cmp_all4/{scidocs,fiqa,hotpotqa,bright}/` are **gitignored**; reproducibility from **raw** intermediates requires re-running `scripts/run_publication_vote_suite.py` + `scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_all4`. |
| **Conflicting package** | `outputs/pub_vote_cmp_v2/paper_package/` uses the **same table schema** but **different numeric outcomes** for overlapping SciDocs/HotpotQA rows than all4 — **do not mix** in one table without explanation. |
| **Q1 journal package** | `outputs/q1_journal_package/` matches **v2-era** numbers (see `scripts/generate_q1_tables.py` default `--pub-root outputs/pub_vote_cmp_v2`). **Stale** vs a four-dataset paper unless regenerated. |
| **Best paper type** | **Conditional-effects / measurement** (optionally framed as **negative or null results on retrieval** for several regimes, with **positive** structural consistency metrics when repair runs). Not a **uniformly positive** results paper. |

---

## 1) Inventory of result packages and manuscript summaries

A machine-readable subset is in **`reports/canonical_results_inventory.csv`**. Expanded notes:

### A. Publication vote suites (main story)

| Path | Family | Datasets | What’s inside |
|------|--------|----------|----------------|
| `outputs/pub_vote_cmp_all4/paper_package/` | Vote-graph + hybrid reranking | 4 | `table_graph_ndcg_and_consistency.csv`, `table_bootstrap_delta_ndcg.csv`, `table_consistency_qrels_bew.csv`, plots, `MANUSCRIPT_SUMMARY.md` |
| `outputs/pub_vote_cmp_all4/analysis/` | JSON deltas for bootstrap aggregation | 4 | `*_delta_{balance,copeland}.json` |
| `outputs/pub_vote_cmp_all4/SUMMARY.md` | Summarizer output | 4 | Markdown table of means |
| `outputs/pub_vote_cmp_v2/paper_package/` | Same schema, older run | 2 (SciDocs, HotpotQA) | Same three CSVs + plots + `MANUSCRIPT_SUMMARY.md` (stronger narrative claims tied to **v2** numbers) |

### B. Q1 journal aggregation

| Path | Source script | Default input |
|------|---------------|---------------|
| `outputs/q1_journal_package/` | `scripts/generate_q1_tables.py` | `outputs/pub_vote_cmp_v2` unless `--pub-root` overridden |

### C. Real-data trees (non–vote-suite protocol)

| Path | Family | Notes |
|------|--------|------|
| `outputs/real_full/` (partially tracked) | `run_real_experiment.py` with **qrels** / **qrels_flip** | Preference source ≠ `votes_file`; **not** the same headline story as publication suite. See `outputs/real_full/PROVENANCE.md`. |

### D. Synthetic / robustness

| Path | Family |
|------|--------|
| `outputs/noise_sweep_*`, `outputs/noise_sweep_variant_followup/*`, `outputs/margin_multiseed_*` | Synthetic noise / multiseed |
| `docs/tables/*.csv` | Historical table exports (bootstrap, synthetic, exact vs greedy, etc.) |

### E. Reports subtree

| Path | Role |
|------|------|
| `reports/paper_tables/` | Generated paper tables + README |
| `reports/experiment_inventory.json` | Machine-readable experiment index |

---

## 2) Canonical evidence package — conclusion

### Recommended canonical package

**`outputs/pub_vote_cmp_all4/paper_package/`**

### Why this one

1. **Coverage:** Four datasets; v2 only has two in the same table set.
2. **Consistency:** Same three CSVs + plots produced by **`scripts/build_paper_evidence_package.py`** (same codepath; `--root` selects the run).
3. **README / orientation:** `README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, and `figures/manuscript/README.md` point here as the **latest** bundle.

### Why others are exploratory / superseded / partial

| Package | Verdict |
|---------|---------|
| **`pub_vote_cmp_v2`** | **Superseded for breadth**; still useful as **historical comparison** but **conflicts** with all4 on overlapping rows. |
| **`q1_journal_package`** | **Partial / stale** relative to `all4` unless regenerated with `--pub-root outputs/pub_vote_cmp_all4`. |
| **`real_full`** | **Different experiment family** (label-derived prefs vs ranker votes)—supplementary at best. |
| **Synthetic outputs** | **Exploratory**; not the main retrieval story. |

### Protocol differences (what differs between packages)

| Dimension | v2 vs all4 (overlapping datasets) |
|-----------|-----------------------------------|
| **Datasets** | v2: 2; all4: 4. |
| **Query subsets** | n_queries often match (e.g. SciDocs 119–120, HotpotQA 52) but **graph stats and nDCG means differ** → **not** the same underlying `*_per_query.csv` aggregation. |
| **Vote construction** | Same **names** (ms2/ms1/ms1_drop_mutual) but **different cyclicity %** (e.g. SciDocs ms2: **1.68%** cyclic in v2 vs **0%** in all4) → different vote graphs. |
| **Evaluation** | Same **metric family** (hybrid RRF methods in `table_graph`); absolute nDCG scales differ materially (e.g. SciDocs mean_ndcg_prior ~**0.42** in v2 vs ~**0.31** in all4 for comparable rows). |
| **Likely causes** | **(c)** different vote/score construction inputs, **(d)** code/version drift between runs, **(f)** stale v2 vs refreshed all4, **(g)** unknown without run manifests—see `reports/repo_cleanup_recommendations.md`. |

**Classification:** **(c) + (d) + (f)** are most plausible from repository structure; **(a)** only partially (extra datasets in all4).

---

## 3) Claims vs evidence

Full matrix: **`reports/claim_support_matrix.csv`**.

**High-signal classifications:**

| Claim | Evidence | Support |
|-------|----------|---------|
| Vote construction affects cyclicity | `table_graph_ndcg_and_consistency.csv` (all4) | **Strong** |
| FAS reduces BEW/PIC when weight removed | `table_consistency_qrels_bew.csv` | **Strong** (with caveat: same qrels) |
| Repair always improves nDCG | Bootstrap tables | **Contradicted** |
| SciDocs ms1 Copeland harm (CI strictly negative) | **v2** bootstrap row | **Strong** in v2 only |
| Same harm (strict CI) | **all4** bootstrap row | **Weak** — CI **straddles** zero |

---

## 4) Headline results (committed `all4` only)

**Machine-readable:** `reports/repaired_vs_unrepaired_master_table.csv` (join of `table_graph_ndcg_and_consistency.csv`, `table_bootstrap_delta_ndcg.csv`, `table_consistency_qrels_bew.csv`).

### Evidence-based interpretation (all4)

| Pattern | Where | Evidence |
|---------|-------|----------|
| **Repair inactive (ΔnDCG=0)** | ms2 and ms1_drop_mutual for most Copeland/balance rows | Bootstrap rows with mean 0 and CI [0,0] |
| **Repair near-null / NS** | SciDocs ms1 Copeland | mean Δ −1.27e−4; CI straddles 0 |
| **Repair positive (interval)** | HotpotQA ms1 Copeland | mean Δ **+0.0167**; CI **[0, 0.0405]** in committed CSV |
| **Structural reduction** | ms1 rows with non-zero `mean_fas_weight_removed` | `table_consistency_qrels_bew.csv` |

**Strongest statistical “headline” in all4 (retrieval):**  
**HotpotQA × ms1 × Copeland** shows the largest positive mean ΔnDCG with a bootstrap interval that does not go negative in the committed file (`ci95_low` = 0.0). **Interpret conservatively:** one dataset × one vote regime; **FiQA ms1** has a positive mean but CI straddles zero.

**Strongest negative narrative in v2 (not replicated at same magnitude in all4):**  
SciDocs ms1 Copeland in **v2** (`table_bootstrap_delta_ndcg.csv`): **−0.00912** with CI strictly below zero.

---

## 5) Paper type (honest)

**Best fit:** **Conditional-effects / measurement paper** (and optionally **negative–null** on broad “repair helps retrieval” claims).

**Not supported as primary framing:** **Uniformly positive** retrieval improvements from FAS repair.

---

## 6) Package inconsistency — resolution plan

1. **Declare** `all4/paper_package` the **canonical** manuscript numbers for multi-benchmark claims.  
2. **Treat** `v2` as **historical** or **sensitivity**—if cited, label **run ID / date** once available.  
3. **Regenerate** `q1_journal_package` from `all4` or stop citing it until regenerated.  
4. **Add provenance** (commit manifest or documented CLI) for future runs—see cleanup doc.

---

## 7) Artifacts produced by this audit

| File | Purpose |
|------|---------|
| `reports/repo_publication_audit.md` | This document |
| `reports/canonical_results_inventory.csv` | Package inventory |
| `reports/claim_support_matrix.csv` | Claim classification |
| `reports/repaired_vs_unrepaired_master_table.csv` | Merged all4 table |
| `reports/paper_safe_contributions.md` | Safe contribution paragraph |
| `reports/repo_cleanup_recommendations.md` | Cleanup steps |

---

## 8) Claims to **avoid** in the manuscript (unless qualified)

- “FAS repair improves retrieval ranking quality **in general**.”
- “Consistency-aware reranking **boosts nDCG** across benchmarks.”
- “Results from **`pub_vote_cmp_v2`** and **`pub_vote_cmp_all4`** can be **interchanged** without caveat.”
- “**LLM** pairwise preferences” (main suite uses **ranker scores**).

---

## 9) Final deliverable (for the author)

### A) Single best paper framing

**Measurement + conditional analysis** of how **vote-graph construction** interacts with **FAS repair** and **hybrid reranking**, with **retrieval effectiveness** (nDCG) **non-uniform** and **structural** inconsistency metrics **responding** when repair removes cyclic tension—reported across **four benchmarks** with **bootstrap** uncertainty.

### B) Single best canonical result package

**`outputs/pub_vote_cmp_all4/paper_package/`**

### C) Three strongest supported claims

1. **Vote aggregation regime (ms2 vs ms1 vs ms1_drop_mutual) strongly affects cycle incidence and graph structure** — `table_graph_ndcg_and_consistency.csv`.
2. **When FAS removes weight, qrels-aligned BEW/PIC often move in the expected direction** — `table_consistency_qrels_bew.csv` (with the **same-qrels** caveat).
3. **Repaired vs unrepaired Copeland ΔnDCG is often zero under near-acyclic constructions** — `table_bootstrap_delta_ndcg.csv` (ms2 / ms1_drop_mutual rows).

### D) Three claims to avoid

1. Universal **retrieval improvement** from repair.  
2. **Interchangeable** use of **v2** and **all4** numbers without acknowledging **protocol drift**.  
3. **LLM-based** preference claims for the main suite.

### E) Exact files to cite (manuscript)

**Primary (all4):**

- `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`
- `outputs/pub_vote_cmp_all4/paper_package/MANUSCRIPT_SUMMARY.md`
- `outputs/pub_vote_cmp_all4/SUMMARY.md`

**Supporting (context / limitations):**

- `README.md` (scope and caveats)
- `docs/Q1_POSITIONING_AND_CLAIMS.md`, `docs/SAFE_Q1_CLAIMS.md`, `docs/THREATS_TO_VALIDITY.md`
- `figures/manuscript/README.md` (figure provenance)

**If discussing historical v2-only claims:**

- `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv`  
  (must clearly label as **separate run** from all4)

---

*End of audit.*
