"""Terminal evaluation of collected judgments against qrels.

This collection gathers shared pairwise judgments, not full policy
trajectories. Terminal rankings here are derived from the collected
judgment graph (via the existing FAS/topological-ranking machinery), which is
an honest "judgment-collection-derived" diagnostic -- explicitly not the
output of an executed acquisition policy. ``TerminalOutcome.policy_replay_ready``
stays ``False`` and ``executed_policies`` stays empty until a later, separate
task actually replays policies over these judgments.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.counterfactual_benchmark.models import (
    CandidatePoolRecord,
    NormalizedJudgment,
    TerminalOutcome,
)
from consistency_ranker.multi_provider_eval.graph_eval import (
    evaluate_preference_graph,
    records_to_preferences,
)
from consistency_ranker.multifactor_acquisition.evaluation_contract import evaluate_ranking


def load_qrels(qrels_path: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(dict)
    with qrels_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            out[str(rec["query_id"])][str(rec["doc_id"])] = int(rec["relevance"])
    return dict(out)


def _judgment_to_graph_record(j: NormalizedJudgment) -> dict[str, Any]:
    valid = bool(j.success and j.normalized_document_preference in {j.doc_a_id, j.doc_b_id})
    return {
        "valid": valid,
        "normalized_winner_id": j.normalized_document_preference if valid else None,
        "query_id": j.query_id,
        "doc_a_id": j.doc_a_id,
        "doc_b_id": j.doc_b_id,
        "canonical_pair_id": j.pair_id,
        "displayed_orientation": j.presentation_order,
    }


def compute_terminal_outcomes(
    *,
    judgments: list[NormalizedJudgment],
    pools: dict[tuple[str, str], CandidatePoolRecord],
    qrels_by_dataset: dict[str, dict[str, dict[str, int]]],
    eval_k: int,
) -> list[TerminalOutcome]:
    """One terminal outcome per (dataset, query, provider) judgment cell."""
    by_cell: dict[tuple[str, str, str], list[NormalizedJudgment]] = defaultdict(list)
    for j in judgments:
        by_cell[(j.dataset, j.query_id, j.provider)].append(j)

    outcomes: list[TerminalOutcome] = []
    for (dataset, query_id, provider), judgs in sorted(by_cell.items()):
        pool = pools[(dataset, query_id)]
        records = [_judgment_to_graph_record(j) for j in judgs]
        prefs = records_to_preferences(records, query_id=query_id)
        graph_result = evaluate_preference_graph(prefs)
        ranking: list[str] = list(graph_result["ranking"])
        missing = [d for d in pool.candidate_ids if d not in ranking]
        # Deterministically append pool candidates untouched by any valid
        # edge, ranked by the qrels-blind primary prior, so every candidate
        # in the pool is represented in the terminal ranking.
        missing.sort(key=lambda d: (-pool.prior_scores_primary[d], d))
        ranking = ranking + missing

        prior_ranking = sorted(
            pool.candidate_ids, key=lambda d: (-pool.prior_scores_primary[d], d)
        )
        qrels_for_query = qrels_by_dataset.get(dataset, {}).get(query_id, {})
        result = evaluate_ranking(
            ranking,
            qrels_for_query,
            k=eval_k,
            n_calls=len(judgs),
            prior_ranking=prior_ranking,
            candidate_pool=list(pool.candidate_ids),
        )
        outcomes.append(
            TerminalOutcome(
                dataset=dataset,
                query_id=query_id,
                provider=provider,
                ranking=ranking,
                ndcg_at_5=result.ndcg_at_k,
                mrr=result.mrr_at_k,
                recall_at_5=result.recall_at_k,
                has_qrels=result.has_qrels,
                missing_qrels_reason=result.missing_qrels_reason,
                prior_agreement_diagnostic={
                    "prior_topk_jaccard": result.prior_topk_jaccard,
                    "prior_kendall_tau": result.prior_kendall_tau,
                    "prior_topk_jaccard_informative": result.prior_topk_jaccard_informative,
                    "agreement_metric_informative": result.agreement_metric_informative,
                },
                n_judgments_used=len(judgs),
            )
        )
    return outcomes
