"""Runtime qrels-leakage guard for policy/acquisition inputs.

Recursively scans arbitrary nested payloads (dicts/lists) for keys that would
indicate qrels, relevance labels, or oracle-derived fields leaking into
runtime policy inputs. Extends
``counterfactual_pilot.trajectory.FORBIDDEN_QRELS_KEYS`` (shallow, single
dict) with recursion so nested acquisition-state payloads are covered too.
"""

from __future__ import annotations

from typing import Any

from consistency_ranker.counterfactual_pilot.trajectory import FORBIDDEN_QRELS_KEYS


class QrelsLeakageError(ValueError):
    """Raised when qrels-like keys are found in a runtime policy input."""


def assert_no_qrels_anywhere(payload: Any, *, _path: str = "$") -> None:
    """Fail closed if any forbidden qrels-like key appears anywhere in *payload*."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_str = str(key)
            if key_str in FORBIDDEN_QRELS_KEYS or key_str.lower() in FORBIDDEN_QRELS_KEYS:
                raise QrelsLeakageError(
                    f"qrels leakage into policy execution inputs at {_path}.{key_str!r}. "
                    "Qrels may be used only after trajectories finish."
                )
            assert_no_qrels_anywhere(value, _path=f"{_path}.{key_str}")
    elif isinstance(payload, (list, tuple)):
        for i, item in enumerate(payload):
            assert_no_qrels_anywhere(item, _path=f"{_path}[{i}]")
