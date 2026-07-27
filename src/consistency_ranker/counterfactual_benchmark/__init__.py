"""Fail-closed collector for the frozen counterfactual micro-pilot (v1).

Reuses the frozen contracts in ``consistency_ranker.counterfactual_pilot``
(panel, prompt, schema, presentation, trajectory, query selection) plus
existing provider/ledger/evaluation infrastructure elsewhere in this repo.
This package never executes provider collection on import; execution is
gated behind the CLI's explicit ``--dry-run`` / ``--cache-only`` /
``--allow-provider-calls`` modes.
"""

from __future__ import annotations

COLLECTOR_VERSION = "counterfactual_benchmark_collector_v1"
