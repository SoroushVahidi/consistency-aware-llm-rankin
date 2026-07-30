"""Matched repaired/unrepaired method pairs for repair-gain labeling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairPair:
    repaired: str
    unrepaired: str
    repair_backend: str
    extraction: str
    description: str


# Only pairs that differ in repair application, not unrelated components.
REPAIR_PAIRS: tuple[RepairPair, ...] = (
    RepairPair(
        repaired="markov_graph_repaired",
        unrepaired="markov_graph",
        repair_backend="greedy_fas",
        extraction="markov_graph",
        description="Greedy MWFAS + Markov graph ranking",
    ),
    RepairPair(
        repaired="copeland_repaired",
        unrepaired="copeland",
        repair_backend="greedy_fas",
        extraction="copeland",
        description="Greedy MWFAS + Copeland on repaired DAG",
    ),
    RepairPair(
        repaired="balance_repaired",
        unrepaired="balance",
        repair_backend="greedy_fas",
        extraction="balance",
        description="Greedy MWFAS + weighted balance on repaired DAG",
    ),
    RepairPair(
        repaired="greedy_fas_topological",
        unrepaired="topological_unrepaired",
        repair_backend="greedy_fas",
        extraction="topological",
        description="Greedy MWFAS + topological sort vs unrepaired topological",
    ),
    RepairPair(
        repaired="markov_graph_ilp_repaired",
        unrepaired="markov_graph",
        repair_backend="ilp",
        extraction="markov_graph",
        description="Exact Gurobi MWFAS + Markov graph (small graphs only)",
    ),
    RepairPair(
        repaired="markov_graph_exact_dp_repaired",
        unrepaired="markov_graph",
        repair_backend="exact_dp",
        extraction="markov_graph",
        description="Exact DP MWFAS + Markov graph (small graphs only)",
    ),
)

PRIMARY_REPAIR_PAIR = REPAIR_PAIRS[0]
