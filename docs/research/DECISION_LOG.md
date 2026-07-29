# Decision Log: Preserve vs. Repair Research Trajectory

*Companion to `docs/research/RESEARCH_TRAJECTORY.md`. Each entry: the
decision, the date, the reasoning, and what would change it. Append new
entries; do not edit past ones except to fix factual errors (note the
correction inline, don't silently rewrite history).*

---

### D1 — 2026-07-28: Why "always-repair" is no longer the default working assumption

**Decision:** Treat repair as a per-query decision to be predicted, not a
default action to apply universally or to reject universally.

**Reasoning:** The JDIQ manuscript establishes, robustly (0/60 canonical
Holm-significant cells, 0/36 exact-repair cells), that always-repair does
not reliably beat always-preserve in aggregate. It does not establish that
repair never helps any individual query — an aggregate null is consistent
with query-level heterogeneity that partially cancels in the mean. Three
independent prior informal attempts to detect that heterogeneity (see
trajectory doc §2) found weak-to-inconclusive signal, not zero signal.

**What would change this:** If Phase 1's widened oracle-headroom analysis
(roadmap doc) still finds no slice with real headroom after using
substantially more of the already-existing data, the working assumption
should revert to "repair effect is not predictable at query granularity
either, from the signals tried" and the project should write up the
stronger negative result described in trajectory doc §10.

---

### D2 — 2026-07-28: Why preserve-vs-repair comes before re-querying

**Decision:** Phase 4 (re-query design/implementation) is explicitly gated
behind Phase 3 (preserve-vs-repair prediction surviving negative controls).

**Reasoning:** Re-querying is more expensive (real acquisition cost) and
structurally more complex (it changes what evidence exists, which changes
the observability assumptions underlying the initial supervised-learning
framing — see D3). Building it before knowing whether even the simpler
2-action prediction problem has any signal risks repeating the pattern
already seen once in this repository: the already-audited active-
acquisition pivot (`PROJECT_STATUS.md`) built and ran a full active
pair-selection pipeline that turned out to lose to random selection. There
is no reason to assume a repair-domain re-query heuristic would fare
differently without first establishing that repair-effect prediction works
at all.

**What would change this:** Phase 3 passing its exit criterion (roadmap
doc) is both necessary and sufficient to unlock Phase 4 design work.

---

### D3 — 2026-07-28: Why the initial task is not automatically causal inference

**Decision:** Frame Phases 0–3 as supervised effect-prediction / algorithm
selection, not causal-effect estimation, and avoid causal-inference
vocabulary until the observability assumptions actually change.

**Reasoning:** For the {preserve, repair} action space with offline-
computable outcomes, both potential outcomes \(M_q(\mathrm{preserve})\)
and \(M_q(\mathrm{repair})\) are literally computed and observed for every
query considered. There is no missing counterfactual, no non-random
historical assignment, and no logged-production-data selection bias to
correct for at this stage. Reaching for causal-inference machinery
(propensity weighting, doubly-robust estimators, uplift modeling) would
be solving a harder, differently-assumption-laden problem than the one
actually present, and could quietly introduce unjustified assumptions
(e.g. an implicit "treatment assignment" model that doesn't exist here).

**What would change this:** The `requery` action (Phase 4) changes what
future evidence exists depending on which edge is queried — at that point,
the "what would have happened under a different acquisition choice" question
does become a genuine counterfactual, and revisiting causal framing for
that specific sub-problem (not the whole pipeline) is appropriate. Also:
if a future phase uses logged, non-randomly-assigned historical
preserve/repair decisions instead of offline replay, causal framing
becomes necessary immediately.

---

### D4 — 2026-07-28: Continuation and stopping criteria

**Decision:** Adopt the three-way gate machinery in
`oracle_headroom.evaluate_go_no_go` (`PROCEED_TO_LABELING` /
`NO_HEADROOM_DO_NOT_LEARN` / `AMBIGUOUS_NEED_MORE_DATA`) as the literal,
executable stopping rule for Gate 0, modeled on the Outcome F precedent
(`oracle_corr - always_uht_corr > 0.05` in
`reports/policy_selection_20260726T030500Z/`) but adapted to a 2-action
space with proper bootstrap CIs (which the Outcome F package itself
lacked — see the same-branch statistical-rigor fixes already made to the
active-acquisition pivot's severe-harm-rate reporting, `PROJECT_STATUS.md`).

**Reasoning:** A repository history of at least four prior attempts at
closely related questions (three informal, one this document's own formal
Phase-0 pass) with no clean positive result argues strongly against an
open-ended "keep trying different features/models until something works"
approach, which is how negative-control failures happen. A pre-registered,
numeric gate — chosen and written down before looking at Phase 1's widened
results — is the discipline this project's own history shows is needed.

**Concrete numbers as of this entry:** `headroom_threshold=0.01`
(matches the manuscript's own smallest equivalence margin),
`min_heterogeneity_fraction=0.05`. These are defaults in
`scripts/run_oracle_headroom_analysis.py` and
`configs/preserve_repair_experiment_spec_v1.json`, not immutable —  but
any change to them should be logged here with a reason, not made silently
inside a script re-run after seeing a disappointing result.

**What would change this:** Nothing has changed these thresholds yet; this
entry exists to make any future change visible and justified.

---

### D5 — 2026-07-28: Why the Gate-0 module reuses `policy_selection` and `repair_selector_mining` rather than building new infrastructure

**Decision:** `oracle_headroom.py` imports `regret_vs_oracle` directly from
`policy_selection.policy_utility`; `grouped_splits.py` wraps (does not
reimplement) `repair_selector_mining.splits.assign_splits`; CI computation
uses the existing `statistical_inference.bootstrap_mean_interval`.

**Reasoning:** Before writing any new code, this repository was searched
for equivalent implementations (see trajectory doc §2 and the roadmap
doc's per-feature-group status notes). Both packages found were built for
closely related problems (Outcome F's 8-policy selection; the never-run
repair-selector-mining pipeline) and are either directly reusable or
adaptable with a documented, tested wrapper. Duplicating them would
violate the explicit instruction not to duplicate existing functionality,
and would also mean re-deriving invariants (e.g. leakage-safe grouping)
that the existing code had already gotten right.

**What would change this:** If a future phase's needs genuinely diverge
from what these packages provide (e.g. a fundamentally different action
space or cost model), a new module is justified — but the divergence
should be stated explicitly in a new decision-log entry, not silently
assumed.
