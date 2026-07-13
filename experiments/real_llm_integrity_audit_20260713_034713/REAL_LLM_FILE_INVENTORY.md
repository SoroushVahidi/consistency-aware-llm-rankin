# REAL_LLM_FILE_INVENTORY

Every real-LLM (OpenAI / Azure OpenAI / Cohere / Gemini) experiment found in the
repository, located by searching source code and output directories rather than
inferring provider identity from filenames (each row's provider was confirmed
from a `provider`/`model` field inside the data itself). "Manuscript use" was
checked against `papers/JDIQ_2026/manuscript/main.tex` on origin/main.

## Pairwise

| # | Provider (verified from data) | Platform | Model | Datasets | Intended queries | Usable queries | Raw responses preserved? | Parsed output | Producing script | Parser | Manuscript use |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | openai | OpenAI API | gpt-4o-mini | scidocs | 50 | 50 | **No** (winner/loser only) | `outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl` | `scripts/run_llm_scidocs_real_pilot.py`-family driver | `src/rerankers/llm_pairwise.py::_parse_winner` (origin/main) | **Yes** -- primary paired pilot, SciDocs |
| 2 | openai | OpenAI API | gpt-4o-mini | scidocs | 30 | 30 | No | `outputs/openai_scidocs_real_pairwise_q30_k15/judgments.jsonl` | same | same | No (superseded by q50) |
| 3 | openai | OpenAI API | gpt-4o-mini | hotpotqa | 20 | 20 | No | `outputs/openai_hotpotqa_real_run_q20_k15/judgments.jsonl` | same | same | **Yes** -- primary paired pilot, HotpotQA |
| 4 | openai | OpenAI API | gpt-4o-mini | hotpotqa | 10 | 10 | No | `outputs/openai_hotpotqa_real_run_q10_k15/judgments.jsonl` | same | same | No (superseded by q20) |
| 5 | openai | OpenAI API | gpt-4o-mini | fiqa | 20 (target) | **10** | No | `outputs/openai_fiqa_real_run_q20_k15/judgments.jsonl` | same | same | **Yes** -- primary paired pilot, FiQA (manuscript's own footnote: "10 of a 20-query target contribute usable paired records") |
| 6 | openai | OpenAI API | gpt-4o-mini | scidocs | 1 (smoke) | 1 | No | `outputs/openai_smoke_scidocs_q1_k5/` | same | same | No (smoke test) |
| 7 | gemini | Google Gemini API | gemini-3.1-flash-lite-preview | scidocs | 5 (2 sampled before quota exhaustion) | 2 | No | `outputs/gemini_scidocs_real_pilot/judgments.jsonl` | same driver, gemini provider | `_parse_winner` (gemini branch) | Mentioned but explicitly **not treated as analyzed evidence** (manuscript sec. 4.8/Limitations) |
| 8 | cohere | Cohere API | command-r-plus-08-2024 | fiqa, hotpotqa, bright | 200 query-regime slots (25/dataset/regime x 3 regimes, minus one dataset x regime gap) | 200 (all attempted slots produced a `llm_cohere_pairwise` ranking) | **Yes**, for 3,005 of ~7,999 unique pairs per provider (see PARSER_AUDIT.md); remainder are within-corpus cache hits with no raw text | `reports/failure_mining_llm_v3/llm_call_records.jsonl`, `llm_cache/cohere_command-r-plus-08-2024/llm_pairwise_judgments.jsonl` | `scripts/run_failure_mining.py` (**uncommitted**, local only) | locally-modified `llm_pairwise.py` (`compare_pair` w/ `detail_sink`, uncommitted) | **Yes**, but see PROVIDER_COUNT_RESOLUTION.md -- the "repair inactive in 62/69/69" text does **not** use these judgments |
| 9 | azure | Azure OpenAI | gpt-4.1-mini | fiqa, hotpotqa, bright | 200 query-regime slots | 200 | Yes, same coverage pattern as row 8 | same files, `azure_gpt-4.1-mini/` | same (uncommitted) | same (uncommitted) | Yes, same caveat as row 8 |
| 10 | cohere/azure/gemini | -- | -- | fiqa, hotpotqa, bright | 25 query-regime slots (ms1 only, scidocs) | 25 | Cohere/Azure: yes (raw log present); Gemini: unavailable | `reports/selector_llm_extension/` | `scripts/run_repair_selector_overnight.py` (uncommitted) | same uncommitted parser | **Not cited by name anywhere in main.tex** |
| 11 | cohere/azure/gemini/cloudrift | -- | command-r-plus, gpt-4.1-mini, --, Qwen3.6-35B | fiqa, hotpotqa, bright | 275/provider | 275/provider (v1, earliest) | No raw prompt log (`llm_call_records.jsonl` only) | `reports/failure_mining_llm/` | same uncommitted driver, earlier version | same | No -- superseded by v3; **note: this earliest version includes a 4th provider (`cloudrift`/Qwen) that never appears in the manuscript's provider table at all** |
| 12 | cohere/azure/gemini | -- | -- | -- | 38/37/275 | partial | No raw prompt log | `reports/failure_mining_llm_v2/` | same, interrupted mid-run | same | No -- superseded |
| 13 | cohere/azure/gemini | -- | -- | -- | 3/3/6 | smoke | No | `reports/failure_mining_llm_smoke_v2/` | same | same | No -- smoke test |

## Pointwise / Listwise

| # | Provider | Model | Mode | Dataset | Queries | Quantitative output | Manuscript use |
|---|---|---|---|---|---|---|---|
| 14 | openai | gpt-4o-mini | pointwise | scidocs | 20 | `outputs/openai_scidocs_real_pointwise_q20_k15/pointwise_summary.csv` (nDCG 0.826) | Yes, auxiliary scope check |
| 15 | openai | gpt-4o-mini | pointwise | hotpotqa | 10 | `outputs/openai_hotpotqa_real_pointwise_q10_k15/pointwise_summary.csv` (nDCG 0.826) | Yes, auxiliary scope check |
| 16 | openai | gpt-4o-mini | listwise | scidocs | 20 | `outputs/openai_scidocs_real_listwise_q20_k15/listwise_summary.csv` | Yes, auxiliary scope check |
| 17 | openai | gpt-4o-mini | listwise | hotpotqa | 10 | `outputs/openai_hotpotqa_real_listwise_q10_k15/listwise_summary.csv` (nDCG 0.899) | Yes, auxiliary scope check |
| 18 | openai | gpt-4o-mini | pointwise/listwise, temp=0.3 | scidocs | 5 each | `outputs/openai_robustness_checks/scidocs_{pointwise,listwise}_temp03_q5_k15/` | Not cited by name; robustness-check scope only |

## Notes on this inventory

- **Provider identity was verified from data fields, not filenames**, per the
  task instruction. One case where this mattered: `reports/failure_mining_llm/`
  (row 11) contains a `cloudrift`/`Qwen/Qwen3.6-35B-A3B-FP8` provider that a
  filename-based search (matching only openai/azure/cohere/gemini directory
  names) would have missed entirely.
- Rows 8-9 (the v3 corpus) are **uncommitted** on origin/main. They exist only
  on the primary tree's `failure-mining-full-records` branch. This audit
  copied them into the worktree per explicit instruction; see PROVENANCE.txt.
- "Usable queries" for pairwise rows means "this provider produced *some*
  ranking output for that query-regime slot," not "the manuscript's
  repair/cyclicity classification used this provider's judgments" -- see
  PROVIDER_COUNT_RESOLUTION.md, which is a materially different question.
