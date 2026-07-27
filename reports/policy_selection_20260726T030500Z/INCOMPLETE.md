# INCOMPLETE

- No large multi-provider billed API calibration was executed (by design).
- Offline real-data replay is sparse / simulated from synthetic cache stubs; treat as observational only.
- Contextual-bandit results are simulated via synthetic utilities, not online bandit learning on real queries.
- Conformal / risk-control bounds assume exchangeability; regime-shift evaluations violate that — reported as empirical diagnostics only.
- Generalized additive models were not fitted (optional dependency); logistic / isotonic / beta / stump cover the interpretable primary set.
- Full provider-escalation cost accounting uses synthetic est_cost, not production tariffs.
- Hyperparameters selected on nested validation regimes; a larger seed grid would tighten intervals.
