"""
Stability-guided adaptive comparison acquisition.

Budget-aware selection of the next pairwise judgment to reduce uncertainty in the
final top-k ranking. Builds on the reliability-aware repair pipeline, the DAG
linear-extension / ambiguity modules, and the provenance-safe multi-provider
evaluation interface.

Pipeline of concerns (each independently testable / ablatable):
* ``acquisition_state`` — serializable, resumable per-query knowledge.
* ``acquisition_actions`` — action space + eligible-action generation (dedup).
* ``pair_uncertainty`` — vote/entropy/orientation/repetition/prompt/model/reliability.
* ``ranking_impact`` — prior/current-rank, top-k boundary, extension & membership
  sensitivity, rank-variance, reachability, repair impact.
* ``structural_signals`` — cycle / incomparability / frontier signals.
* ``acquisition_policies`` — scoring, baselines, exploration, batch selection.
* ``provider_escalation`` — cheap→expensive cascade + model-action reliability.
* ``adaptive_stopping`` — top-k-aware stopping with a reported reason.
* ``transitivity`` — skip reliably-implied pairs.
* ``counterfactual`` — expected stability gain (exact over discrete outcomes).
* ``interactive_judges`` — simulated judge that answers only on request.
* ``offline_replay`` — provenance-safe replay pool with policy isolation.
* ``anytime_metrics`` — budget-indexed trajectory recording.
* ``engine`` — the acquisition loop tying it all together.
"""

from consistency_ranker.adaptive_acquisition.acquisition_actions import (
    Action,
    JudgeProfile,
    generate_eligible_actions,
)
from consistency_ranker.adaptive_acquisition.acquisition_policies import (
    AcquisitionPolicy,
    make_policy,
    select_batch,
)
from consistency_ranker.adaptive_acquisition.acquisition_state import (
    AcquisitionState,
    initial_state,
)
from consistency_ranker.adaptive_acquisition.adaptive_stopping import StoppingPolicy
from consistency_ranker.adaptive_acquisition.engine import (
    AcquisitionResult,
    EngineConfig,
    run_acquisition,
)
from consistency_ranker.adaptive_acquisition.interactive_judges import (
    InteractiveJudge,
    InteractiveJudgeConfig,
    make_interactive_judge,
)
from consistency_ranker.adaptive_acquisition.offline_replay import (
    ReplayPool,
    load_replay_pools,
)
from consistency_ranker.adaptive_acquisition.provider_escalation import (
    ActionReliabilityModel,
    synthetic_roster,
)

__all__ = [
    "Action",
    "JudgeProfile",
    "generate_eligible_actions",
    "AcquisitionState",
    "initial_state",
    "AcquisitionPolicy",
    "make_policy",
    "select_batch",
    "StoppingPolicy",
    "AcquisitionResult",
    "EngineConfig",
    "run_acquisition",
    "InteractiveJudge",
    "InteractiveJudgeConfig",
    "make_interactive_judge",
    "ReplayPool",
    "load_replay_pools",
    "ActionReliabilityModel",
    "synthetic_roster",
]
