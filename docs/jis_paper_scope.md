# JIS manuscript scope (conservative, repository-aligned)

This document **freezes** what the repository can honestly support **today**, using **`outputs/pub_vote_cmp_all4`** (mirrored in `outputs/final_jis_package/`) as the **canonical** real-data evidence bundle. It does **not** change scientific intent of the codebase; it **limits** overstated manuscript claims.

---

## What this paper **is** about

- **Pairwise preference aggregation for retrieval reranking:** How **different vote-graph constructions** (`ms2`, `ms1`, `ms1_drop_mutual`) change **cyclicity**, **graph structure**, and **downstream hybrid rankings** when a **greedy feedback-arc-set-style repair** is applied.
- **Measurement / diagnostic study:** Empirical description of **when repair is inactive**, **when it moves qrels-aligned structural metrics (BEW, PIC)**, and **when bootstrap ΔnDCG** (repaired − unrepaired) is **null, mixed, or dataset-dependent**—across **four** retrieval datasets in the canonical bundle.
- **Honest tension:** Demonstrating that **structural consistency reductions** and **retrieval metric movement** need **not** align in direction or interpretability.

---

## What this paper is **not** about

- **Not** a claim that graph repair **always improves** nDCG@k or user utility.
- **Not** an **LLM pairwise judgment** paper: the canonical suite’s preferences are **derived from conventional ranker scores** in the documented pipeline, not from an LLM-as-judge protocol committed for these tables.
- **Not** a proof about **exact (ILP) MWFAS** superiority on real data.
- **Not** a **universal cross-BEIR** empirical law: four datasets are evidence **for those four**, not for all benchmarks.
- **Not** interchangeable with **`outputs/real_full`** headline results without stating the **different preference construction** (`qrels` / `qrels_flip` vs `votes_file` publication suite—see `outputs/real_full/PROVENANCE.md`).

---

## Scientific question best supported by the repository

> Under controlled **vote-graph construction** choices for **retrieval-derived pairwise preferences**, how do **cycle prevalence** and **greedy FAS-style repair** relate to **qrels-aligned structural inconsistency** and to **bootstrap summaries of ΔnDCG** for **hybrid Copeland / balance rerankers**—and how **consistent** is that relationship **across datasets**?

---

## Safest contribution angle for JIS

1. **Methodological / empirical characterization:** Vote rules create **different cyclicity regimes**; repair’s **activity** tracks those regimes.
2. **Structural vs retrieval decoupling:** Repair can **change** graph–qrels tension metrics **without** delivering a **uniform** retrieval benefit—and can be **inactive** when graphs are already near-acyclic.
3. **Conditional downstream effects:** For **`ms1`**, Copeland **ΔnDCG** is **not uniform** across SciDocs, FiQA, HotpotQA, and BRIGHT in the committed bootstrap table; manuscript should foreground **heterogeneity** and **intervals**, not a single headline direction.
4. **Synthetic appendix role (optional):** Separately, synthetic experiments (e.g., `reports/jis_final_tables/A01_*`, `A02_*`) can support **internal** claims about **greedy FAS vs classical baselines** under synthetic generative assumptions—clearly **separated** from the vote-suite story.

---

## Experiments / results **included** in the paper (recommended)

| Block | Repository locus | Role |
|-------|------------------|------|
| Four-dataset publication vote suite | `outputs/final_jis_package/` (copy of `pub_vote_cmp_all4/paper_package` + analysis JSON) | **Main empirical block:** graph stats, nDCG means, BEW/PIC, bootstrap ΔnDCG. |
| Synthetic robustness (optional main text or appendix) | `reports/jis_final_tables/A01_*`, `A02_*` (from `reports/paper_tables/`) | Noise / multiseed **synthetic** behavior. |
| Threats / limitations prose | `docs/THREATS_TO_VALIDITY.md`, `docs/jis_reproducibility.md` | Honest scope and reproducibility caveats. |

---

## Experiments / results **excluded** or **non-primary** (recommended)

| Block | Repository locus | Reason |
|-------|------------------|--------|
| **`pub_vote_cmp_v2` numeric story** | `outputs/pub_vote_cmp_v2/paper_package/` | **Superseded** by all4 for breadth; **conflicts** on overlapping cells—use only as **historical** comparison if needed. |
| **`q1_journal_package` as authoritative** | `outputs/q1_journal_package/` | **Stale vs all4** unless regenerated with `--pub-root outputs/pub_vote_cmp_all4`. |
| **`reports/paper_tables/table_01` / `table_05`** | `reports/paper_tables/` | **Tied to v2-era** aggregation in generator script; **misleading** if all4 is canonical (SciDocs ms1 Copeland bootstrap differs). |
| **`real_full` as same claim as vote suite** | `outputs/real_full/` | **Different protocol**; supplementary at best with explicit separation. |
| **LLM file mode** | Documented in code paths but **no committed canonical LLM pairwise results** matching the vote-suite tables | Do not imply LLM evidence. |

---

## Why this framing is honest and defensible

- It follows the **most comprehensive committed bundle** (`pub_vote_cmp_all4`) while **documenting numerical conflict** with older v2/q1 tables (`reports/repo_publication_audit.md`, `outputs/final_jis_package/README.md`).
- It treats **bootstrap intervals** in the CSV as the **upper bound on inferential language** for retrieval deltas—avoiding **v2-only** “strictly significant harm” language when citing **all4**.
- It separates **synthetic** and **real-data** evidentiary roles, matching how files are produced in-repo (`scripts/generate_paper_tables.py`, `scripts/build_paper_evidence_package.py`).

---

*Companion files: `reports/jis_claims_mapping.md`, `reports/jis_editorial_summary.md`, `docs/jis_reproducibility.md`.*
