# PROMPT_MODE_SCOPE_AUDIT

## Inventory (see REAL_LLM_FILE_INVENTORY.md rows 14-18)

All committed OpenAI pointwise/listwise runs have real quantitative output:

| Mode | Dataset | n queries | nDCG | MAP | Precision | Recall |
|---|---|---|---|---|---|---|
| pointwise | scidocs | 20 | 0.826 | 0.754 | 0.130 | 1.000 |
| pointwise | hotpotqa | 10 | 0.826 | -- | -- | -- |
| listwise | scidocs | 20 | -- | -- | -- | -- |
| listwise | hotpotqa | 10 | 0.899 | 0.867 | 0.130 | 1.000 |
| pointwise (temp=0.3, robustness) | scidocs | 5 | -- | -- | -- | -- |
| listwise (temp=0.3, robustness) | scidocs | 5 | -- | -- | -- | -- |

(`--` = file present but this audit did not additionally parse every field;
see the linked CSVs directly for full numbers.)

## Do they have quantitative outputs?

Yes -- unlike the failure-mining Cohere/Azure corpus (which was largely a
ranking-comparison side-channel, see PROVIDER_COUNT_RESOLUTION.md), the
pointwise/listwise runs compute their own independent nDCG/MAP/precision/
recall/BEW/PIC directly, with no dependency on the mechanical vote-regime
pipeline.

## Do they support manuscript claims?

The manuscript already describes them correctly and narrowly: "Separate
OpenAI pointwise and listwise runs are used only as auxiliary scope checks on
SciDocs and HotpotQA" (sec:llm-config). This framing is accurate -- nothing
in this audit found the pointwise/listwise numbers used for any headline
repair/cyclicity/ΔnDCG claim.

## Do they belong in the main paper, or should they move to supplementary?

At n=20 (scidocs) and n=10 (hotpotqa) queries, with no repeated-seed or
bootstrap uncertainty reporting found for these specific runs (unlike the
pairwise pilot, which has `BOOTSTRAP_SUMMARY.md`/`*_bootstrap_summary.csv`
per dataset), these are single-point estimates. They are legitimate as a
qualitative "prompt style doesn't obviously break the method" scope check but
are not statistically load-bearing at this sample size. Recommendation:
**move to supplementary / an appendix table**, keeping only a one-sentence
pointer in the main text (which is already close to what sec:real-llm-scope
currently does) rather than a dedicated main-text subsection or table,
consistent with how they are already used (not currently over-claimed, so
this is a "harmless but document" / presentation-only recommendation, not a
correctness issue).

## Robustness-check variants (temp=0.3)

`outputs/openai_robustness_checks/scidocs_{pointwise,listwise}_temp03_q5_k15/`
(n=5 each) are not cited anywhere in `main.tex`. They exist as evidence the
authors checked temperature sensitivity but chose not to report it. No action
required; noted here for completeness per the inventory instruction ("whether
it is actually used in the manuscript").
