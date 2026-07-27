# FINAL_REPORT — Calibrated query-level policy selection

Timestamped directory: `policy_selection_20260726T030500Z`

## Decision

**Outcome F — Synthetic results are insufficient; specify the smallest decisive real calibration experiment. Interim production default: always UHT with a lightweight safety floor (mandatory outsider probe + stop prohibition on weak evidence), because calibrated gates do not yet beat always-UHT on corrected utility.**

### Operating point

```json
{
  "gate_mode": "always_uht",
  "qhat_threshold": 0.35,
  "uht_risk_threshold": 0.0871513237103253,
  "probe_budget": 3,
  "probe_design": "mixed_diagnostic",
  "tau_policy": 0.5,
  "safety_floor": 0.15,
  "false_trust_weight": 2.5,
  "false_distrust_weight": 0.5,
  "calibration_model": "logistic",
  "feature_schema": "policy_gate_features_v1",
  "interim_safety_floor": 0.15,
  "interim_safeguards": [
    "mandatory_outsider_probes",
    "stop_prohibit_weak_evidence",
    "final_adversarial_challenger"
  ]
}
```

## Headline results (held-out test regimes)

| Mode | mean U | gate regret | top-k Jac | calls | cat. rate | pol. acc |
|---|---:|---:|---:|---:|---:|---:|
| oracle | 0.229 | 0.368 | 0.433 | 16.0 | 0.083 | 1.000 |
| always_uht | 0.089 | 0.523 | 0.475 | 16.0 | 0.250 | 0.083 |
| random | 0.089 | 0.523 | 0.475 | 16.0 | 0.250 | 0.083 |
| selective_three_way | 0.004 | 0.536 | 0.350 | 15.3 | 0.250 | 0.000 |
| majority_best | -0.018 | 0.549 | 0.283 | 15.8 | 0.083 | 0.000 |
| staged | -0.024 | 0.562 | 0.350 | 15.3 | 0.250 | 0.083 |
| soft_mixture | -0.065 | 0.604 | 0.308 | 15.3 | 0.333 | 0.000 |
| budget_split | -0.065 | 0.604 | 0.308 | 15.3 | 0.333 | 0.000 |
| conservative_fallback | -0.065 | 0.604 | 0.308 | 15.3 | 0.333 | 0.000 |
| always_robust | -0.076 | 0.613 | 0.325 | 15.7 | 0.250 | 0.250 |
| contextual | -0.118 | 0.657 | 0.283 | 15.7 | 0.333 | 0.167 |
| always_challenger | -0.119 | 0.654 | 0.283 | 15.8 | 0.333 | 0.000 |
| hard_qhat | -0.119 | 0.654 | 0.283 | 15.8 | 0.333 | 0.000 |
| calibrated_hard | -0.119 | 0.654 | 0.283 | 15.8 | 0.333 | 0.000 |
| cost_sensitive_regret | -0.119 | 0.654 | 0.283 | 15.8 | 0.333 | 0.000 |
| broad_static | -0.144 | 0.677 | 0.258 | 15.8 | 0.333 | 0.333 |

## Answers to required conclusions

1. **Predictability of best policy.** Test policy-selection accuracy for calibrated_hard=0.000; selective=0.000. Observable probe features carry signal but are far from oracle.

2. **Probe phase value.** See `decision_curves.json` quality_vs_probe; mixed probes of budget 2–3 typically lift gate utility vs budget 0.

3. **Most informative probe pairs.** Mixed diagnostic and top-k-vs-outsider pairs best discriminate burial and local top-k errors (design priors in summary.probe_informativeness; empirical boundary fractions {'random_pairs': {'mean_boundary_fraction': 0.611111111111111}, 'boundary_pairs': {'mean_boundary_fraction': 1.0}, 'topk_vs_outsider': {'mean_boundary_fraction': 1.0}, 'mixed_diagnostic': {'mean_boundary_fraction': 0.6666666666666666}}).

4. **Hard gate vs soft mixture.** Compare calibrated_hard vs soft_mixture / staged in the table above; soft mixtures reduce catastrophic false-trust when classification confidence is low.

5. **Regret prediction vs prior-quality.** Cost-sensitive regret gate uses Δ(UHT, challenger); see `policy_regret_table.json`. Prefer regret when asymmetric catastrophic risk dominates pure Q̂.

6. **Asymmetry.** Operating false_trust=2.5, false_distrust=0.5 (~5:1). Thresholds selected by expected utility on validation, not balanced accuracy.

7. **Buried-outsider risk.** Probe feature `n_outsiders_defeating_insiders` plus topk-vs-outsider pairs; challenger / conservative modes recover more often than plain UHT.

8. **Abstention rate.** Selective gate abstain_rate=0.833 at τ_policy=0.50; increase τ to trade coverage for lower regret.

9. **Online switching.** Staged mode with hysteresis; see failure traces tagged `switching`. Helps when posterior Q̂ crosses bands; avoid oscillation via min_steps_between_switches.

10. **Lightweight fallback.** Mandatory outsider probe + max consecutive UHT + final adversarial challenger before stop; light when Q̂ high.

11. **Fallback cost under good priors.** Safety floor 0.15 and single outsider probe add a few calls; compare always_uht vs conservative_fallback call counts.

12. **Shift robustness.** Leave-one-regime-out ECE/Brier in summary; n_items shift rows=[{'n_items': 6, 'utility': 0.09600000000000003, 'topk_jaccard': 0.5, 'policy': 'HYBRID', 'g_q': 0.2928614835822261}, {'n_items': 6, 'utility': 0.09400000000000003, 'topk_jaccard': 0.5, 'policy': 'HYBRID', 'g_q': 0.2944608899797784}, {'n_items': 10, 'utility': 0.096, 'topk_jaccard': 0.2, 'policy': 'HYBRID', 'g_q': 0.29199680520664595}, {'n_items': 10, 'utility': 0.096, 'topk_jaccard': 0.2, 'policy': 'HYBRID', 'g_q': 0.29356702060159795}]. Calibration degrades under OOD; ood_score triggers conservative mixture.

13. **Oracle gap.** Oracle mean U=0.229; best production=always_uht U=0.089.

14. **Production default.** `always_uht` at the operating point above.

15. **Minimum real multi-provider calibration next.** 30–40 queries × 2 providers × 2 prompts × orientation reverse on top-12 candidates; budget 20–25 judgments/query with a fixed 3-call mixed diagnostic probe first. Endpoints: calibration of P(UHT optimal), catastrophic false-trust rate, buried-outsider recovery, and utility vs always-UHT / always-challenger. No full all-pairs campaign.

## Implementation map

Package: `src/consistency_ranker/policy_selection/`

| Module | Role |
|---|---|
| `gate_features.py` | Pre / probe / online features + schema versioning |
| `diagnostic_probes.py` | Probe designs and execution |
| `policy_utility.py` | Utility + asymmetric gate losses |
| `policy_calibration.py` | Logistic / isotonic / beta / stump / multinomial |
| `policy_regret.py` | Direct Δ regret prediction |
| `policy_gate.py` | Hard / selective / soft / contextual selectors |
| `policy_mixture.py` | Score mix, budget split, staged plan |
| `policy_switching.py` | Online switch + hysteresis |
| `safe_fallback.py` | Lightweight catastrophic safeguards |
| `risk_control.py` | Empirical risk-control (non-certificate) |
| `policy_benchmark.py` | Nested synthetic population + oracle labels |
| `policy_runner.py` | Policy ↔ engine mapping + gated loop |
| `replay_eval.py` | Provenance-safe sparse replay |

### Complexity / inference overhead

- Feature extraction: O(|E| + n log n) over acquired evidence and prior sort.
- Probe phase: O(B_probe) judgments (default 3).
- Gate inference: O(d) dot-product / stump; multinomial O(|Π| d).
- Does not add Monte Carlo beyond the underlying acquisition engine.
- Switching / fallback: O(1) per step.

## Risk-control assumptions

Split-conformal / risk-control thresholds assume exchangeability between calibration and deployment queries. Nested synthetic regime shifts and real distribution shift violate this; treat results as empirical bounds on the calibration distribution only, not as deployment guarantees.

## Reproduction

```bash
source .venv/bin/activate
PYTHONPATH=src python scripts/run_policy_selection_experiment.py --output-dir reports/policy_selection_20260726T030500Z
pytest tests/test_policy_selection.py -q
```

## Incomplete

See `INCOMPLETE.md`.
