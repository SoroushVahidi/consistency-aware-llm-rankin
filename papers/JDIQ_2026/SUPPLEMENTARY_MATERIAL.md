# Supplementary Material Plan — JDIQ 2026

> **SUPERSEDED (as of 2026-07-14) -- DO NOT ATTACH AS-IS TO A SUBMISSION.**
> This plan predates the finished manuscript and includes a "Failure
> taxonomy deep dive" component and a "CARB release," both sourced from the
> six-way rule-based failure taxonomy that the finished manuscript's
> Limitations section explicitly excludes as evidence. Attaching that
> component to an actual submission would contradict the paper's own
> stated evidence base. Before assembling real supplementary material,
> rebuild this plan from `manuscript/main.tex`'s actual sections and cited
> tables (see `docs/REPRODUCTION_CANONICAL.md` for the current
> table-to-source mapping).

**Prepared:** 2026-07-12  
**Delivery format:** ACM supplementary material upload + optional Zenodo archive  
**Principle:** Main paper self-contained; supplement provides depth, reproducibility, and CARB release.

---

## Package structure

```
papers/JDIQ_2026/supplementary/
├── README.md                          # Index and reproduction instructions
├── CARB/
│   ├── DATA_CARD.md                   # Dataset documentation
│   ├── SCHEMA.md                      # From created_data_audit phase10
│   ├── LICENSE.md                     # CC-BY 4.0 (proposed)
│   ├── carb_v0.1_features.parquet     # Feature-only release (to be built)
│   └── carb_v0.1_query_index.csv     # Query IDs and regime labels
├── artifact/
│   ├── REPRODUCTION.md                # Step-by-step commands
│   ├── environment.yml                # Python 3.11+ deps
│   ├── run_canonical_suite.sh         # Wrapper script
│   └── checksums.sha256               # Output verification
├── appendices/
│   ├── APPENDIX_A_baseline_per_dataset.pdf
│   ├── APPENDIX_B_extraction_fusion.pdf
│   ├── APPENDIX_C_exact_vs_greedy.pdf
│   ├── APPENDIX_D_selector.pdf
│   ├── APPENDIX_E_runtime.pdf
│   ├── APPENDIX_F_carb_features.pdf
│   ├── APPENDIX_G_claim_matrix.pdf
│   └── APPENDIX_H_extended_bootstrap.pdf
├── claim_matrix/
│   └── final_claim_support_matrix.csv
├── failure_taxonomy/
│   ├── manual_failure_summary.csv
│   ├── minimal_intervention_summary.csv
│   ├── counterfactual_repair_per_query.csv
│   └── FAILURE_TAXONOMY_GUIDE.md
└── runtime_memory/
    ├── existing_efficiency_measurements.csv
    ├── runtime_per_query.csv
    └── EFFICIENCY_NOTES.md
```

---

## Component 1: CARB benchmark release

**Source:** `experiments/created_data_audit_20260711_232004/`

| Item | Status | Action |
|------|--------|--------|
| Schema definition | **Drafted** | Copy `phase10/PROPOSED_DATASET_SCHEMA.md` |
| Release structure | **Drafted** | Copy `phase10/PROPOSED_RELEASE_STRUCTURE.md` |
| Feature dictionary | **Complete** | Include `phase6/global_feature_dictionary.csv` |
| Data card | **Missing** | Write `CARB/DATA_CARD.md` (mandatory) |
| License | **Missing** | Choose CC-BY 4.0 for features; document restrictions |
| Actual feature files | **Not packaged** | Build from `reports/failure_mining/` canonical records |
| Raw doc text | **Withhold** | Per release audit — IDs only |
| LLM prompts/caches | **Withhold** | Per release audit |
| Leakage-prone fields | **Document** | Flag ndcg, oracle labels in data card |

**CARB positioning in JDIQ:** Supplementary resource accompanying the research paper. Not a standalone resource paper (unless optional O4 pursued later).

**Record counts:**

- 440 independent queries
- 1020 query×regime records
- 366 method outputs per record
- 14+ feature groups

---

## Component 2: Artifact / reproduction package

**Source:** `docs/REPRODUCTION_Q1.md`, `scripts/`

| Item | Path | Purpose |
|------|------|---------|
| Vote suite runner | `scripts/run_publication_vote_suite.py` | Reproduce 4-dataset experiments |
| Evidence packager | `scripts/build_paper_evidence_package.py` | Generate Tables 4–5 |
| Figure builder | `scripts/build_manuscript_assets.py` | Generate Figs 2–5 |
| Failure mining | `scripts/run_failure_mining.py` | Per-query records |
| Environment | `requirements.txt`, `pyproject.toml` | Dependency pinning |
| Synthetic smoke test | `scripts/run_synthetic.py` | Offline verification |

**Reproduction tiers:**

| Tier | What | Time | API cost |
|------|------|------|----------|
| T0 | Unit tests (`pytest`) | ~5 min | $0 |
| T1 | Synthetic experiment | ~2 min | $0 |
| T2 | Canonical table rebuild from committed CSVs | ~1 min | $0 |
| T3 | Full vote suite (requires local run trees / HF data) | Hours | $0 |
| T4 | Real-LLM pilots | — | **Do not rerun** ($) |
| T5 | Failure-mining LLM v3 | — | **Do not rerun** ($) |

**Anonymous review:** Host artifact on anonymous Zenodo/OpenScience Framework or state "available upon acceptance."

---

## Component 3: Reproducibility package

| Document | Source | Content |
|----------|--------|---------|
| `REPRODUCTION.md` | `docs/REPRODUCTION_Q1.md` | Commands, seeds, expected outputs |
| `PROTOCOL_COMPARTMENTS.md` | `CANONICAL_EVIDENCE_MAP.md` | Five experiment families; do-not-mix rules |
| `CHECKSUMS.md` | New | SHA-256 of canonical CSVs |
| `VERSION_PIN.md` | `pyproject.toml` | Python 3.11+, package version |

**Canonical output checksums (committed files):**

- `table_graph_ndcg_and_consistency.csv`
- `table_bootstrap_delta_ndcg.csv`
- `table_consistency_qrels_bew.csv`

---

## Component 4: Runtime and memory evidence

**Source:** `experiments/failure_class_audit_20260711_212157/phase_reports/`

| Item | Status | Supplement location |
|------|--------|-------------------|
| Synthetic runtime (scale_sweep) | Exists | `runtime_memory/` |
| Per-query runtime (failure_class) | Exists | `runtime_memory/runtime_per_query.csv` |
| Real-pipeline memory | **Missing** | Note absence in `EFFICIENCY_NOTES.md` |
| Efficiency audit report | Exists | Include `EFFICIENCY_EVIDENCE_AUDIT.md` |

**Claim discipline:** Report runtime as "practical on synthetic workloads"; do not claim real-pipeline memory is validated.

---

## Component 5: Claim matrix

**Source:** `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`

Include in supplement for reviewer transparency:

- 15 claims with classification (safe / contradicted / etc.)
- Evidence artifact pointers
- Notes on qualification

Optional: include `reviewer_response_state_audit` criticism status table for internal use (not necessarily in public supplement).

---

## Component 6: Failure taxonomy deep dive

**Source:** `experiments/failure_class_audit_20260711_212157/`

| File | Content |
|------|---------|
| `manual_failure_summary.csv` | Class frequencies |
| `minimal_intervention_summary.csv` | Counterfactual fixes |
| `counterfactual_repair_per_query.csv` | Per-query counterfactuals |
| `cluster_profiles.csv` | Automatic clusters |
| `failure_predictor_results.csv` | Predictive models |
| `regret_decomposition_summary.csv` | Regret analysis |
| `FAILURE_TAXONOMY_GUIDE.md` | **New** — class definitions for users |

---

## Component 7: Appendices (PDF)

| Appendix | Content | Primary source |
|----------|---------|----------------|
| A | Per-dataset baseline tables | `final_baseline_comparison.csv` |
| B | Extraction/fusion sensitivity | `extraction_fusion_complete.csv` |
| C | Exact vs greedy repair | `repair_comparison_real.csv` |
| D | Selector features and policy | `selector_llm_extension/`, `method_improvement_audit/` |
| E | Runtime evidence | `failure_class_audit/EFFICIENCY_*` |
| F | CARB feature dictionary | `global_feature_dictionary.csv` |
| G | Claim-evidence matrix | `final_claim_support_matrix.csv` |
| H | Extended bootstrap (SCC-stratified) | `table_bootstrap_delta_ndcg.csv` |
| I | Counterfactual validity | `counterfactual_validity_summary.csv` |

---

## Component 8: Repository organization (for public release)

Proposed public repo layout post-acceptance:

```
consistency-aware-llm-rankin/     # or separate artifact repo
├── README.md                     # Paper title, citation, quick start
├── papers/JDIQ_2026/             # This workspace (manuscript + plans)
├── src/                          # Library code
├── scripts/                      # Reproduction scripts
├── outputs/pub_vote_cmp_all4/    # Canonical results (paper_package only)
├── data/carb/v0.1/               # CARB feature release
├── requirements.txt
└── CITATION.cff
```

**Private (not released):**

- `outputs/openai_*/` API caches
- `reports/failure_mining_llm_v3/llm_cache/`
- `Consistency_Aware_Reranking*_IJCS.zip`
- Experiment audit workspaces (optional; can release as research transparency)

---

## Upload checklist

- [ ] Single ZIP < 100 MB (ACM typical limit; verify current JDIQ limit)
- [ ] README with file manifest
- [ ] CARB data card with license
- [ ] No API keys or credentials
- [ ] No author-identifying metadata (anonymous review)
- [ ] Checksums for canonical CSVs
- [ ] Reproduction script tested on clean environment

---

## Relationship to main paper

| Main paper | Supplement |
|------------|------------|
| Tables 4–7, 9–10 (summary) | ST1–ST10 (full breakdown) |
| Figs 1–6 | SF1–SF5 |
| §9 CARB overview | CARB/ full schema + data card |
| §13 one-paragraph availability | REPRODUCTION.md full guide |
| §11 threats summary | Claim matrix + protocol compartments |

---

*This plan defines structure only. No files have been moved or packaged yet.*
