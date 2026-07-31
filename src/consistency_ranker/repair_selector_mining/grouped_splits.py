"""Grouped, leakage-safe train/validation/test splitting for preserve-vs-repair records.

Thin wrapper around the EXISTING ``repair_selector_mining.splits.assign_splits``
/ ``split_rows`` (built for the JDIQ-era repair-mining pipeline; not
duplicated here, only adapted) so ``PreserveRepairRecord`` objects can be
split without hand-rolling a new grouped-CV utility -- per the roadmap
doc's explicit instruction not to duplicate existing functionality, and
its explicit prohibition on a random per-row split that could leak the
same query across train and test.

**Important gotcha, documented rather than silently worked around
upstream:** ``assign_splits`` groups queries by a SHA-256 fingerprint of
``candidate.get("query_text")``, so that near-duplicate query TEXT lands in
the same split. ``PreserveRepairRecord`` has no query text (it is built
from an already-aggregated outcome CSV, not raw queries). Passing
``query_text=None`` for every record would fingerprint every record to the
SAME hash (``_text_fingerprint(None) == _text_fingerprint("")``), collapsing
the entire population into one fingerprint group and defeating the split
entirely. This module avoids that by using ``query_id`` itself as the
fingerprint text -- unique per real query (assuming query IDs are not
reused for materially different queries within a dataset, which holds for
every source CSV currently in this repository). The tradeoff: two
different query IDs with genuinely duplicate query text will NOT be forced
into the same split by this wrapper, unlike the original near-duplicate-
text use case. Acceptable here because the source CSVs' query IDs are
already deduplicated upstream by the pipelines that produced them.
"""

from __future__ import annotations

from consistency_ranker.repair_selector_mining.oracle_headroom import PreserveRepairRecord
from consistency_ranker.repair_selector_mining.splits import assign_splits


def split_records(
    records: list[PreserveRepairRecord],
    *,
    seed: int = 42,
    train_frac: float = 0.6,
    val_frac: float = 0.2,
) -> tuple[list[PreserveRepairRecord], list[PreserveRepairRecord], list[PreserveRepairRecord]]:
    """Split records into (train, validation, test), grouped by (dataset, query_id).

    No ``(dataset, query_id)`` pair appears in more than one output list --
    verified by a test, not just asserted here.
    """
    candidates = [
        {"dataset": r.dataset, "query_id": r.query_id, "query_text": r.query_id} for r in records
    ]
    assignments = assign_splits(candidates, seed=seed, train_frac=train_frac, val_frac=val_frac)

    train: list[PreserveRepairRecord] = []
    val: list[PreserveRepairRecord] = []
    test: list[PreserveRepairRecord] = []
    for record in records:
        split = assignments.get(record.key())
        if split == "train":
            train.append(record)
        elif split == "validation":
            val.append(record)
        elif split == "test":
            test.append(record)
    return train, val, test


__all__ = ["split_records"]
