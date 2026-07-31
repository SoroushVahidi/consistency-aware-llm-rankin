"""Leakage-safe train/validation/test split assignment at query level."""

from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np

TRAIN_FRAC = 0.6
VAL_FRAC = 0.2
TEST_FRAC = 0.2
MIN_TEST_FRAC = 0.2


def _text_fingerprint(text: str | None) -> str:
    normalized = (text or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def assign_splits(
    candidates: list[dict],
    *,
    seed: int = 42,
    train_frac: float = TRAIN_FRAC,
    val_frac: float = VAL_FRAC,
) -> dict[tuple[str, str], str]:
    """Assign each (dataset, query_id) to train, validation, or test.

  Near-duplicate queries (same normalized text fingerprint) are forced into the
  same split. Stratification is by dataset.
  """
    rng = np.random.default_rng(seed)

    # Group by fingerprint first to keep near-duplicates together.
    fp_to_keys: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for cand in candidates:
        key = (str(cand["dataset"]), str(cand["query_id"]))
        fp = _text_fingerprint(cand.get("query_text"))
        fp_to_keys[fp].append(key)

    # One representative per fingerprint group, tagged with dataset.
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fp, keys in fp_to_keys.items():
        dataset = keys[0][0]
        groups[dataset].append(keys[0])

    assignments: dict[tuple[str, str], str] = {}
    for dataset, rep_keys in groups.items():
        shuffled = list(rep_keys)
        rng.shuffle(shuffled)
        n = len(shuffled)
        if n == 1:
            split_map = {shuffled[0]: "train"}
        elif n == 2:
            split_map = {shuffled[0]: "train", shuffled[1]: "test"}
        else:
            n_test = max(1, int(round(n * max(TEST_FRAC, 1.0 - train_frac - val_frac))))
            n_val = max(1, int(round(n * val_frac)))
            n_train = n - n_test - n_val
            if n_train < 1:
                n_train = 1
                n_val = max(0, min(n_val, n - n_train - 1))
                n_test = n - n_train - n_val
            split_map = {}
            for i, key in enumerate(shuffled):
                if i < n_train:
                    split_map[key] = "train"
                elif i < n_train + n_val:
                    split_map[key] = "validation"
                else:
                    split_map[key] = "test"

        for fp, keys in fp_to_keys.items():
            if keys[0][0] != dataset:
                continue
            if keys[0] not in split_map:
                continue
            split = split_map[keys[0]]
            for key in keys:
                assignments[key] = split

    return assignments


def split_rows(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    train, val, test = [], [], []
    for row in rows:
        split = row.get("split_assignment") or row.get("query_metadata", {}).get("split")
        if split == "train":
            train.append(row)
        elif split == "validation":
            val.append(row)
        elif split == "test":
            test.append(row)
    return train, val, test
