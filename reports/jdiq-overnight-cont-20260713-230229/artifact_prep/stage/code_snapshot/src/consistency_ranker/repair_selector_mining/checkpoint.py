"""Incremental checkpoint writers for overnight repair mining."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class FlushWriter:
    """Append-only writer that flushes after each record."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def write(self, obj: dict | str) -> None:
        if isinstance(obj, dict):
            self._fh.write(json.dumps(obj, default=str) + "\n")
        else:
            self._fh.write(str(obj) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class CsvWriter:
    def __init__(self, path: Path, fieldnames: list[str]) -> None:
        self.path = path
        self.fieldnames = fieldnames
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._exists = path.exists()
        self._fh = path.open("a", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(self._fh, fieldnames=fieldnames, extrasaction="ignore")
        if not self._exists:
            self._writer.writeheader()
            self._fh.flush()

    def write(self, row: dict[str, Any]) -> None:
        self._writer.writerow(row)
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class CheckpointManager:
    """Manages all required output artifacts with incremental flushing."""

    REQUIRED_FILES = (
        "run_manifest.json",
        "run.log",
        "progress.json",
        "provider_usage.csv",
        "api_failures.csv",
        "query_candidates.csv",
        "split_assignments.csv",
        "pairwise_judgments.jsonl",
        "per_query_method_results.csv",
        "repair_pair_results.csv",
        "repair_selector_dataset.jsonl",
        "positive_case_inventory.csv",
        "checkpoint_state.json",
    )

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.writers = {
            "pairwise_judgments": FlushWriter(output_dir / "pairwise_judgments.jsonl"),
            "repair_selector_dataset": FlushWriter(output_dir / "repair_selector_dataset.jsonl"),
            "full_records": FlushWriter(output_dir / "query_level_full_records.jsonl"),
        }
        self.csv_writers = {
            "provider_usage": CsvWriter(
                output_dir / "provider_usage.csv",
                ["timestamp", "provider", "model", "query_id", "dataset", "status", "from_cache", "latency_s"],
            ),
            "api_failures": CsvWriter(
                output_dir / "api_failures.csv",
                [
                    "timestamp",
                    "provider",
                    "model",
                    "query_id",
                    "dataset",
                    "error",
                    "error_message",
                    "http_status",
                    "retry_count",
                ],
            ),
            "query_candidates": CsvWriter(
                output_dir / "query_candidates.csv",
                [
                    "dataset",
                    "query_id",
                    "vote_regime",
                    "mining_priority",
                    "split_assignment",
                    "is_cyclic",
                    "largest_scc_frac",
                    "ranker_disagreement",
                ],
            ),
            "split_assignments": CsvWriter(
                output_dir / "split_assignments.csv",
                ["dataset", "query_id", "split", "text_fingerprint"],
            ),
            "per_query_method_results": CsvWriter(
                output_dir / "per_query_method_results.csv",
                ["dataset", "query_id", "vote_regime", "method", "ndcg_at_k", "split"],
            ),
            "repair_pair_results": CsvWriter(
                output_dir / "repair_pair_results.csv",
                [
                    "dataset",
                    "query_id",
                    "vote_regime",
                    "repaired_method",
                    "unrepaired_method",
                    "repair_backend",
                    "repair_gain",
                    "split",
                ],
            ),
            "positive_case_inventory": CsvWriter(
                output_dir / "positive_case_inventory.csv",
                [
                    "dataset",
                    "query_id",
                    "vote_regime",
                    "threshold",
                    "repair_gain",
                    "repaired_method",
                    "primary_provider",
                    "split",
                ],
            ),
        }
        self._completed_keys: set[str] = set()
        ckpt = output_dir / "checkpoint_state.json"
        if ckpt.exists():
            state = json.loads(ckpt.read_text(encoding="utf-8"))
            self._completed_keys = set(state.get("completed_keys", []))

    def is_completed(self, key: str) -> bool:
        return key in self._completed_keys

    def mark_completed(self, key: str) -> None:
        self._completed_keys.add(key)

    def write_json(self, name: str, data: dict) -> None:
        path = self.output_dir / name
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def save_checkpoint(self, state: dict) -> None:
        state = {**state, "completed_keys": sorted(self._completed_keys)}
        self.write_json("checkpoint_state.json", state)

    def close(self) -> None:
        for w in self.writers.values():
            w.close()
        for w in self.csv_writers.values():
            w.close()
