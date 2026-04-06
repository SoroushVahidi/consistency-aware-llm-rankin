# LLM Manuscript-Evidence Consistency Audit (IJCS)

> Date: 2026-04-06
> Scope: manuscript-facing and claims-facing docs for real-LLM evidence consistency.

| file | issue found | action taken |
|---|---|---|
| `docs/safe_claims.md` | Already updated to 3-dataset conservative framing. | No further change. |
| `outputs/openai_real_llm_cross_dataset_summary.md` | Already contained 3-dataset table + conservative interpretation. | No further change. |
| `docs/LLM_PILOT_STATUS.md` | Stale 20q/10q runs, “no bootstrap CIs”, two-dataset language. | Replaced with current 3-dataset OpenAI status (SciDocs 50q, HotpotQA 20q, FiQA bounded 10 processed), bootstrap-computed status, and conservative wording. |
| `docs/LLM_REAL_PILOT_RESULTS.md` | Stale two-dataset pilot framing and outdated “no CIs” claims. | Rewritten to current bounded 3-dataset evidence package and conservative non-claims. |
| `docs/THREATS_TO_VALIDITY.md` | Stated only SciDocs+HotpotQA and LLM evidence as purely prospective. | Updated to reflect separate real-LLM addendum (with bounded FiQA) while keeping limitations conservative. |
| `docs/Q1_POSITIONING_AND_CLAIMS.md` | Rows still said LLM generalization unsupported due no real LLM data; FiQA treated as missing. | Updated relevant lines to reflect bounded real-LLM addendum and remaining generalization limits. |
| `docs/revision_strategy.md` | Multiple stale references to two datasets and missing bootstrap CI. | Updated counts, datasets, CI status, and conservative manuscript language. |
| `docs/related_work_positioning_note.md` | Stale “SciDocs 20q + HotpotQA 10q only” wording. | Updated to current OpenAI run coverage and conservative transfer framing. |
| `docs/SAFE_CLAIMS_FOR_PAPER.md` | Unsupported-claim rationale incorrectly said no LLM pairwise comparisons in repo. | Updated rationale to distinguish canonical score-derived package from bounded real-LLM addendum. |
| `docs/EVIDENCE_MAP.md` | Marked LLM generalization fully unsupported. | Updated to “partially supported (bounded)” with conservative caveat. |
