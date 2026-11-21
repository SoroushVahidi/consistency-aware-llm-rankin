# Prospective LLM opportunity audit v1

Classification: prospective exploratory study with a preregistered gate;
not manuscript evidence. Read PROTOCOL.md before execution. Historical and
JDSA manuscript files are never changed. Raw benchmark material, responses,
query-level outputs and model files remain in a private run outside Git.

## Components

- `common.py`: frozen prompts/parser, identities, requests and durable storage.
- `prepare.py`: identity exclusions, disjoint rosters, BM25 and diagnostic pools,
  pinned official sources, model file/LFS identity checks and immutable manifest.
- `gate.py`: fixed content/reversal/position/repeat/paraphrase/resource criteria.
- `worker.py`: local-only inference, validation gate, conditional main acquisition,
  per-response checkpoints, budgets, safe explicit resume and per-query analysis.
- `analyze.py`: existing Copeland/greedy/SCIP/nDCG/statistics, seven-way attribution,
  all-query/conditional denominators, dataset/stratum breakdowns and paired tests.
- `launch.sh`: persistent tmux-compatible invocation with a 12-hour outer limit.
- `test_prospective.py`: offline correctness and safety checks without model calls.

Existing infrastructure reused: `scripts/generate_score_file.py:BM25Ranker`,
`baseline_ranking.copeland_ranking`, `greedy_fas.greedy_fas`,
`mwfas_solver._solve_scip` (PySCIPOpt 6.2.1), `evaluation.ndcg_at_k`,
`statistical_inference.sign_flip_pvalue/holm_adjust/proportion_interval`.
New code handles a prospective instrument and run lifecycle; it does not
replace the established ranking or solver implementations.

## Portable preparation and launch

Set `WORKSPACE`, `RUN`, `MODEL_SNAPSHOT`, `INFERENCE_PYTHON`, `ANALYSIS_PYTHON`
to explicit local paths. These are task-specific variables; do not override
system HOME or CODEX_HOME. Use existing environments read-only. Inference
requires CUDA-compatible torch/transformers; analysis requires the repository
dependencies and PySCIPOpt 6.2.1. No install into shared environments.

From the experiment worktree:

```bash
"$ANALYSIS_PYTHON" -m experiments.jdsa_prospective_v1.prepare \
  --workspace "$WORKSPACE" --run "$RUN" --model-path "$MODEL_SNAPSHOT" \
  --analysis-python "$ANALYSIS_PYTHON"
tmux new-session -d -s jdsa-prospective-v1 \
  bash experiments/jdsa_prospective_v1/launch.sh "$RUN" "$INFERENCE_PYTHON"
```

The worker executes development first. Only an identity-bound passing gate
allows evaluation responses. A failed gate terminates with diagnostic files
and no main launch. Do not remove the gate, substitute a model or edit a frozen
prompt to force continuation. A corrected instrument requires a separate
version, development protocol, and run.

## Monitor and resume

Observe startup and approximately two minutes of main progress, then stop
monitoring. A queued/starting validation is not a passed gate or main launch.

```bash
cat "$RUN/PROGRESS.json"
cat "$RUN/INSTRUMENT_VALIDATION.json"
cat "$RUN/MAIN_LAUNCH.json"
tmux has-session -t jdsa-prospective-v1
nvidia-smi
```

Later explicit resume, after confirming the original worker is no longer
running and no unrelated GPU compute process is present:

```bash
tmux new-session -d -s jdsa-prospective-v1-resume \
  bash experiments/jdsa_prospective_v1/launch.sh "$RUN" "$INFERENCE_PYTHON" --resume
```

No retries of recorded invalid/abstaining responses. Completed response IDs
are immutable; only interrupted in-flight attempts may be explicitly reissued,
within the frozen attempt/time ceilings. Recovered interrupted sessions are
charged conservatively, including time since their last heartbeat; an overnight
resume may therefore be refused rather than silently resetting the budget.
Never delete locks/checkpoints or reset the manifest to bypass a stop.

Private handoff artifacts: `RUN_MANIFEST.json`, `inputs/FROZEN_QUERY_IDS.json`,
`provenance/*`, `INSTRUMENT_VALIDATION.json`, `MAIN_LAUNCH.json`, `PROGRESS.json`,
`private/responses.sqlite3` (plus WAL/SHM), `results/*`, `ANALYSIS_SUMMARY.json`,
`FAILURE.json` if present, and `logs/EXIT_CODE`. SQLite must be backed up using
its backup API or with the worker stopped, not by copying only the live main DB.

No automatic submission, manuscript update, raw publication or PR merge.
The model is a single cached 2024 Qwen family, not a frontier-model panel.
Natural and label-enriched conditions have different candidate contracts;
their differences are descriptive, not isolated causal interventions.
