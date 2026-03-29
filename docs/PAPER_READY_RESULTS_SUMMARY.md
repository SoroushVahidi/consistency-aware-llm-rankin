# Paper-ready results summary (routing study only)

## Executive status: **blocked**

This document was requested to summarize **only** canonical routing-study evidence for GSM8K, Hard GSM8K, MATH500, AIME, and GPQA. In the current workspace, **none** of the required routing output directories exist under `outputs/`, so **no** manuscript tables, CSVs, or figures were produced. Inventing or partially filling tables would violate the project’s evidence rules.

**Blocker log (machine-readable):** `outputs/paper_tables/ROUTING_ARTIFACT_BLOCKER.txt`

**Paths verified missing:**

- `outputs/real_policy_eval/`
- `outputs/real_routing_model/`
- `outputs/multi_action_models/`
- `outputs/baselines/`
- `outputs/oracle_routing_eval/` (or equivalent oracle routing summaries)

Retrieval, ranking, qrels, SciDocs, HotpotQA, BRIGHT, FiQA, and cross-encoder artifacts were **not** used for this summary.

---

## 1. Strongest positive result

**Not measured in-repo for routing.** No routing accuracy/cost files were loaded.

---

## 2. Strongest negative result

**Not measured in-repo for routing.**

---

## 3. What changed after adding `reasoning_then_revise`

**Not measured in-repo.** Requires routing experiment outputs that compare pipelines before/after that method exists in the canonical bundles.

---

## 4. Where routing works

**Not measured in-repo.**

---

## 5. Where action mismatch dominates

**Not measured in-repo.** Metrics such as `action_disagreement_rate` would need to appear in routing artifacts (e.g. per-run summaries or JSON); none were available.

---

## 6. Current limitation: label degeneracy / insufficient disagreement

**Cannot assess from routing outputs** until routing tables with disagreement / revise-helpful statistics are committed. This remains a **hypothesis-level** discussion for the manuscript until data exist.

---

## 7. Exact claims: measured_now vs exploratory_only

With **no** routing artifacts, there are **no** routing-specific claims that qualify as `measured_now` in this repository snapshot.

---

## Claim discipline (manuscript)

### measured_now

- **Routing (GSM8K, Hard GSM8K, MATH500, AIME, GPQA):** none in this repo snapshot. Do not cite routing numbers from this pass.
- **Other domains:** any numbers elsewhere in the repo (e.g. retrieval/qrels packages) are **out of scope** for this routing-only summary and must not be blended into the routing story without a separate, explicit evidence map.

### exploratory_only

- Narratives about adaptive test-time compute, routing, and revise policies **as motivation** — fine as **exploratory / future work** if clearly labeled and not tied to nonexistent tables.

### not_yet_claim_ready

- All items in sections 1–6 above for the **routing** paper thread.
- Any cross-dataset comparison of `reasoning_then_revise` vs static baselines, oracle gap, Pareto-dominant methods, or disagreement-driven failures — **not yet claim_ready** until `outputs/real_policy_eval/` (and siblings) contain reproducible summaries.

---

## Output files (Step 6)

| Expected output | Status |
|-----------------|--------|
| `outputs/paper_tables/main_cross_dataset_table.csv` | **Not created** (blocked) |
| `outputs/paper_tables/baseline_comparison_table.csv` | **Not created** (blocked) |
| `outputs/paper_tables/{dataset}_cost_accuracy.*` | **Not created** (blocked) |

**Created instead:** `outputs/paper_tables/ROUTING_ARTIFACT_BLOCKER.txt` — validation record only.

---

## Next step for authors

Populate the canonical `outputs/` routing trees, then add a small generator script (ingest-only, no API) that reads those summaries and writes the two CSV tables plus per-dataset cost–accuracy and Pareto exports. Re-run validation before regenerating this markdown.
