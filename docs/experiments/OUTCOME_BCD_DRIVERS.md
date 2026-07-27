# Outcome B–D experiment drivers

Canonical offline-safe entry points for the deferred experimental subsystems
that support (but do not replace) Outcome F production-operating-point work.

| Driver | Subsystem | External calls | Report pattern |
|---|---|---|---|
| `scripts/run_adaptive_acquisition_experiment.py` | `consistency_ranker.adaptive_acquisition` | None (synthetic + optional cache replay) | `reports/adaptive_acquisition_*` |
| `scripts/run_prior_robust_experiment.py` | `consistency_ranker.prior_robust` | None (adversarial synthetic worlds) | `reports/prior_robust_*` |
| `scripts/run_reliability_aware_repair_experiment.py` | `consistency_ranker.reliability_repair` | None (synthetic + optional pilot cache) | `reports/reliability_aware_repair_*` |
| `scripts/run_linear_extension_extraction_experiment.py` | `dag_linear_extensions` / `soft_score_ranking` | None (synthetic + optional cached judgments) | `reports/linear_extension_extraction_*` |
| `scripts/run_multi_provider_llm_robustness.py` | `consistency_ranker.multi_provider_eval` | Live only with `--allow-provider-calls` | `reports/multi_provider_llm_robustness_*` |

## Shared CLI contracts

All five drivers support:

- `--output-dir` (timestamped default under `reports/`)
- `--overwrite` (refuse non-empty directories by default)
- `config.json` + `run_manifest.json` (git commit, argv, config)

Synthetic drivers additionally support `--quick` for tiny offline smokes.

The multi-provider driver is fail-closed: one of `--cache-only`, `--dry-run`,
or `--allow-provider-calls` is required.

## Historical method audit

The linear-extension method inventory lives at:

`docs/historical/linear_extension_method_audit.md`

It is historical documentation of which ranking-extraction methods were added
or transferred; it is not a runnable experiment.

## Evidence policy

Large report trees remain gitignored until explicitly frozen. Drivers must not
silently overwrite those trees. See `docs/ARTIFACT_POLICY.md`.

## Relation to Outcome F / multifactor / real counterfactual

| Driver | Role |
|---|---|
| Adaptive acquisition | Policy catalog / anytime trajectories under matched synthetic budgets; trajectory schema is reusable for a future real counterfactual benchmark |
| Prior-robust | Stress-tests prior dependence and exploration guards; informs when UHT needs robust fallbacks (Outcome D decision logic) |
| Reliability repair | Graph construction / cycle repair under unreliable judgments |
| Linear extension | DAG ranking-extraction stage comparison (hard topo vs soft scores) |
| Multi-provider | Provider/prompt/orientation robustness; live spend gated |

None of these drivers change production always-UHT defaults or enable learned routing.
