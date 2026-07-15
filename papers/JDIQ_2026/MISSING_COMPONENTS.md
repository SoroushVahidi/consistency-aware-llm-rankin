# Missing Components — JDIQ 2026 Submission

**Prepared:** 2026-07-12  
**Baseline:** `MANUSCRIPT_OUTLINE.md`, `MASTER_EVIDENCE_INVENTORY.csv`, `CANONICAL_PAPER_STORY.md`

---

## Mandatory before submission

| ID | Component | Hours est. | New experiments? | Writing only? | Exists but needs regeneration? | Dependency |
|----|-----------|------------|------------------|---------------|-------------------------------|------------|
| M1 | **LaTeX manuscript skeleton** (`acmart` + JDIQ formatting) | 4–6 | No | Setup only | No | `JDIQ_GUIDELINE_SUMMARY.md` |
| M2 | **Full manuscript prose** (all §1–§13) | 80–120 | No | Yes | No | Outline, story, claim matrix |
| M3 | **Regenerate canonical tables** from `pub_vote_cmp_all4` | 8–12 | No | No | **Yes** — scripts exist | `build_paper_evidence_package.py` |
| M4 | **Fig 1: Pipeline schematic** (new) | 6–8 | No | No | New figure | §3 outline |
| M5 | **Regenerate Figs 2–5** from `build_manuscript_assets.py` | 8–12 | No | No | **Yes** — script exists | `pub_vote_cmp_all4` |
| M6 | **Fig 6: Failure class distribution** (new) | 4–6 | No | No | New figure | `manual_failure_summary.csv` |
| M7 | **Table 2–3: Dataset and method inventory** | 4–6 | No | Partial | Partial — compile from existing | §4 outline |
| M8 | **ACM bibliography** (40–60 refs) | 12–16 | No | Yes | Partial — `LITERATURE_ALIGNMENT.md` | Related work |
| M9 | **CCS concepts and keywords** | 1–2 | No | Yes | No | JDIQ guidelines |
| M10 | **Data availability statement** | 2–4 | No | Yes | Partial — `created_data_audit` | CARB schema |
| M11 | **CARB data card** (for supplementary release) | 16–24 | No | Yes | **Yes** — schema drafted | `phase10/PROPOSED_DATASET_SCHEMA.md` |
| M12 | **Reproducibility README** (anonymous artifact) | 8–12 | No | Yes | Partial — `REPRODUCTION_Q1.md` | Scripts |
| M13 | **Anonymized submission package** | 4–6 | No | No | No | M1–M12 |
| M14 | **Threats to validity section** | 4–6 | No | Yes | **Yes** — `THREATS_TO_VALIDITY.md` | §11 outline |
| M15 | **Protocol disclosure subsection** (experiment families) | 4–6 | No | Yes | Partial — audits exist | `CANONICAL_EVIDENCE_MAP.md` |

**Mandatory subtotal:** ~165–240 hours (~4–6 weeks full-time)

---

## Strongly recommended

| ID | Component | Hours est. | New experiments? | Writing only? | Exists but needs regeneration? | Dependency |
|----|-----------|------------|------------------|---------------|-------------------------------|------------|
| R1 | **Fig 7: SCC vs ΔnDCG scatter** | 4–6 | No | No | New figure | failure_class per-query data |
| R2 | **Fig 8: CARB schema diagram** | 3–4 | No | No | New figure | CARB schema |
| R3 | **Supplementary Appendix A–H** (extended tables) | 12–16 | No | Partial | **Yes** — CSVs exist | Section map |
| R4 | **Cover letter** (JDIQ DQ framing; IJCS evolution) | 2–4 | No | Yes | No | Story doc |
| R5 | **Reviewer-response mapping** (internal; for resubmission prep) | 8–12 | No | Yes | **Yes** — `reviewer_response_audit` | IJCS reviews |
| R6 | **HotpotQA ms1 subgroup analysis writeup** | 4–6 | No | Yes | **Yes** — bootstrap data exists | §6, §10 |
| R7 | **Code release polish** (clean public repo or Zenodo) | 16–24 | No | No | Partial | `requirements.txt` |
| R8 | **CARB feature-only release package** | 24–32 | No | No | **Yes** — records exist | Data card M11 |
| R9 | **Graphical abstract** | 4–6 | No | No | New | `figures/graphical_abstract/` |
| R10 | **Internal consistency check** (all numbers traceable) | 8–12 | No | No | Audit pass | All tables |

**Recommended subtotal:** ~85–122 hours (~2–3 weeks)

---

## Optional

| ID | Component | Hours est. | New experiments? | Writing only? | Exists but needs regeneration? | Notes |
|----|-----------|------------|------------------|---------------|-------------------------------|-------|
| O1 | Prior-only paired significance in canonical protocol | 8–16 | **Maybe** | No | Partial | Only if reviewer demands |
| O2 | Real-pipeline memory benchmark | 16–24 | **Yes** | No | No | Low scientific value |
| O3 | Larger LLM campaign | 40–80+ | **Yes** (API cost) | No | No | Not needed for JDIQ story |
| O4 | Standalone CARB resource paper | 60–80 | No | Yes | Partial | Separate submission |
| O5 | Additional datasets (multilingual) | 80+ | **Yes** | No | No | Out of scope |
| O6 | Selector decisive evaluation | 24–40 | **Maybe** | No | Partial | Exploratory contribution |
| O7 | Modern baselines aligned to canonical protocol | 24–40 | **Maybe** | No | Partial | Protocol alignment hard |
| O8 | Interactive CARB explorer (web) | 40–60 | No | No | No | Nice-to-have |

---

## Summary by category

| Category | Items | Hours (range) |
|----------|-------|---------------|
| Mandatory | 15 | 165–240 |
| Strongly recommended | 10 | 85–122 |
| Optional | 8 | 288+ |

---

## New experiments needed?

**No** for initial JDIQ submission. All mandatory evidence exists in the repository.

The only items that *might* require new computation:

- O1: Prior-only paired test in canonical vote-suite protocol (can likely be derived from existing per-query CSVs if gitignored run trees are available locally)
- O2/O3/O7: Explicitly optional; not recommended before first submission

---

## Critical path

```
M1 (skeleton) → M2 (prose) ∥ M3 (tables) ∥ M5 (figures) ∥ M6 (failure fig)
                     ↓
              M10 + M11 (data availability + CARB card)
                     ↓
              M12 + M13 (repro package + anonymized submit)
```

**Bottleneck:** M2 (full prose writing) — 80–120 hours  
**Parallelizable:** Tables, figures, supplementary, CARB packaging

**Estimated weeks to submission:** 6–8 weeks (one author, part-time); 4–5 weeks (full-time focused)
