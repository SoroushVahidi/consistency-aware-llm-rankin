"""
data_loader.py
==============
Utilities for loading ranking datasets from disk.

Supported formats
-----------------
- JSON lines: each line is a dict with at least an ``"id"`` key.
- CSV: first column is treated as item id, remaining columns as metadata.
- Plain text: one item id per line.

The module returns simple Python lists/dicts to keep the rest of the codebase
dependency-light; callers can convert to pandas DataFrames if desired.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON-lines file and return a list of record dicts.

    Parameters
    ----------
    path:
        Path to the ``.jsonl`` file.

    Returns
    -------
    list[dict]
        Each element corresponds to one line in the file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    json.JSONDecodeError
        If a line cannot be parsed as JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise json.JSONDecodeError(
                    f"Invalid JSON on line {lineno} of {path}: {exc.msg}",
                    exc.doc,
                    exc.pos,
                ) from exc
    return records


def load_csv(path: str | Path, id_col: str = "id") -> list[dict[str, Any]]:
    """Load a CSV file and return a list of record dicts.

    Parameters
    ----------
    path:
        Path to the ``.csv`` file.
    id_col:
        Name of the column to use as the item identifier.  If the column does
        not exist, a sequential integer ``id`` is assigned automatically.

    Returns
    -------
    list[dict]
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    records: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if id_col not in row:
                row[id_col] = i  # type: ignore[assignment]
            records.append(dict(row))
    return records


def load_txt(path: str | Path) -> list[str]:
    """Load a plain-text file where each non-empty line is an item id.

    Parameters
    ----------
    path:
        Path to the ``.txt`` file.

    Returns
    -------
    list[str]
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def save_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    """Serialise a list of dicts to a JSON-lines file.

    Parameters
    ----------
    records:
        Data to write.
    path:
        Destination file path (created or overwritten).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
