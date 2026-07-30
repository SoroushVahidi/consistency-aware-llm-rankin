"""
timing.py
=========
Lightweight timing utilities for profiling pipeline stages.

Public API
----------
- :class:`Timer`               — context-manager that measures a single code block.
- :func:`timed`                — decorator that measures every call to a function.
- :class:`TimingAccumulator`   — collect named timings across many stages / queries,
                                  then print or export them.

Usage example
-------------
::

    from consistency_ranker.utils.timing import Timer, TimingAccumulator, timed

    acc = TimingAccumulator()

    with Timer("graph_build", accumulator=acc):
        graph = build_graph(prefs)

    @timed("greedy_fas", accumulator=acc)
    def run_fas(g):
        return greedy_fas(g)

    acc.print_summary()
    acc.save_csv("outputs/timings/stages.csv")
    acc.save_json("outputs/timings/stages.json")
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from functools import wraps
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Timer — single-block context manager
# ---------------------------------------------------------------------------

class Timer:
    """Context manager that measures elapsed wall-clock time.

    Parameters
    ----------
    name:
        Label for this timing measurement.
    accumulator:
        Optional :class:`TimingAccumulator` to record the result into.
    verbose:
        If ``True`` (default), print the elapsed time when the block exits.

    Attributes
    ----------
    elapsed:
        Elapsed time in seconds after the block exits.  ``None`` while inside
        the block.

    Examples
    --------
    ::

        with Timer("graph_build") as t:
            graph = build_graph(prefs)
        print(t.elapsed)   # seconds
    """

    def __init__(
        self,
        name: str = "unnamed",
        accumulator: "TimingAccumulator | None" = None,
        verbose: bool = False,
    ) -> None:
        self.name = name
        self._accumulator = accumulator
        self._verbose = verbose
        self.elapsed: float | None = None
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed = time.perf_counter() - self._start
        if self._accumulator is not None:
            self._accumulator.record(self.name, self.elapsed)
        if self._verbose:
            print(f"  [{self.name}] {self.elapsed:.4f}s")


# ---------------------------------------------------------------------------
# timed — function decorator
# ---------------------------------------------------------------------------

def timed(
    name: str | None = None,
    accumulator: "TimingAccumulator | None" = None,
    verbose: bool = False,
) -> Callable:
    """Decorator that records elapsed time of every function call.

    Parameters
    ----------
    name:
        Stage name.  Defaults to the function's ``__name__``.
    accumulator:
        Optional :class:`TimingAccumulator` to record timings into.
    verbose:
        If ``True``, print elapsed time after each call.

    Examples
    --------
    ::

        acc = TimingAccumulator()

        @timed("build_graph", accumulator=acc)
        def build(prefs):
            return build_graph(prefs)
    """
    def decorator(fn: Callable) -> Callable:
        stage = name if name is not None else fn.__name__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - start
            if accumulator is not None:
                accumulator.record(stage, elapsed)
            if verbose:
                print(f"  [{stage}] {elapsed:.4f}s")
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# TimingAccumulator — collect & aggregate named timings
# ---------------------------------------------------------------------------

class TimingAccumulator:
    """Collect named timing measurements and produce summary statistics.

    Each :meth:`record` call appends a measurement (in seconds) for a named
    stage.  Call :meth:`print_summary` for a console table, or
    :meth:`save_csv` / :meth:`save_json` to export.

    Attributes
    ----------
    _timings : dict[str, list[float]]
        Raw timing records keyed by stage name.
    _metadata : dict[str, Any]
        Arbitrary metadata stored alongside timings (e.g. dataset name).
    """

    def __init__(self) -> None:
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._metadata: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, stage: str, elapsed: float) -> None:
        """Append *elapsed* seconds to the *stage* bucket.

        Parameters
        ----------
        stage:
            Human-readable name of the pipeline stage.
        elapsed:
            Wall-clock seconds taken.
        """
        self._timings[stage].append(elapsed)

    def set_metadata(self, **kwargs: Any) -> None:
        """Store arbitrary key-value metadata (e.g. dataset name, n_items).

        Parameters
        ----------
        **kwargs:
            Arbitrary key-value pairs to attach to this accumulator.
        """
        self._metadata.update(kwargs)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def stages(self) -> list[str]:
        """Return all recorded stage names in insertion order."""
        return list(self._timings.keys())

    def all_timings(self, stage: str) -> list[float]:
        """Return all raw timing values for *stage*."""
        return list(self._timings.get(stage, []))

    def total(self, stage: str) -> float:
        """Return sum of all timings for *stage* (seconds)."""
        return sum(self._timings.get(stage, []))

    def mean_time(self, stage: str) -> float:
        """Return mean timing for *stage* (seconds). Returns 0.0 if no data."""
        values = self._timings.get(stage, [])
        return mean(values) if values else 0.0

    def median_time(self, stage: str) -> float:
        """Return median timing for *stage* (seconds). Returns 0.0 if no data."""
        values = self._timings.get(stage, [])
        return median(values) if values else 0.0

    def max_time(self, stage: str) -> float:
        """Return maximum timing for *stage* (seconds). Returns 0.0 if no data."""
        values = self._timings.get(stage, [])
        return max(values) if values else 0.0

    def grand_total(self) -> float:
        """Return sum of **all** recorded timings across every stage."""
        return sum(v for vals in self._timings.values() for v in vals)

    def summary_rows(self) -> list[dict[str, Any]]:
        """Return a list of summary dicts, one per stage.

        Each dict has keys: ``stage``, ``n_calls``, ``total_s``, ``mean_s``,
        ``median_s``, ``max_s``.
        """
        rows = []
        for stage in self.stages():
            values = self._timings[stage]
            rows.append(
                {
                    "stage": stage,
                    "n_calls": len(values),
                    "total_s": round(sum(values), 6),
                    "mean_s": round(mean(values), 6),
                    "median_s": round(median(values), 6),
                    "max_s": round(max(values), 6),
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_summary(self) -> None:
        """Print a formatted summary table to stdout."""
        rows = self.summary_rows()
        if not rows:
            print("  (no timings recorded)")
            return
        col_widths = {"stage": 28, "n_calls": 8, "total_s": 10, "mean_s": 10, "median_s": 10, "max_s": 10}
        header = (
            f"  {'Stage':<{col_widths['stage']}} "
            f"{'n_calls':>{col_widths['n_calls']}} "
            f"{'total(s)':>{col_widths['total_s']}} "
            f"{'mean(s)':>{col_widths['mean_s']}} "
            f"{'median(s)':>{col_widths['median_s']}} "
            f"{'max(s)':>{col_widths['max_s']}}"
        )
        sep = "  " + "-" * (sum(col_widths.values()) + len(col_widths) - 1)
        print("\n  Timing Summary")
        print(sep)
        print(header)
        print(sep)
        for row in rows:
            print(
                f"  {row['stage']:<{col_widths['stage']}} "
                f"{row['n_calls']:>{col_widths['n_calls']}} "
                f"{row['total_s']:>{col_widths['total_s']}.4f} "
                f"{row['mean_s']:>{col_widths['mean_s']}.4f} "
                f"{row['median_s']:>{col_widths['median_s']}.4f} "
                f"{row['max_s']:>{col_widths['max_s']}.4f}"
            )
        print(sep)
        print(f"  Grand total: {self.grand_total():.4f}s\n")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    _CSV_COLUMNS = ["stage", "n_calls", "total_s", "mean_s", "median_s", "max_s"]

    def save_csv(self, path: str | Path) -> Path:
        """Write summary statistics to a CSV file.

        Parameters
        ----------
        path:
            File path for the CSV output.  Parent directories are created
            automatically.

        Returns
        -------
        Path
            The resolved output path.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = self.summary_rows()
        with out.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return out

    def save_json(self, path: str | Path) -> Path:
        """Write full timing data (summary + raw values + metadata) to JSON.

        Parameters
        ----------
        path:
            File path for the JSON output.  Parent directories are created
            automatically.

        Returns
        -------
        Path
            The resolved output path.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": self._metadata,
            "summary": self.summary_rows(),
            "raw": {stage: vals for stage, vals in self._timings.items()},
        }
        with out.open("w") as fh:
            json.dump(payload, fh, indent=2)
        return out

    def to_flat_rows(self) -> list[dict[str, Any]]:
        """Return one row per individual timing observation (flat format).

        Each row: ``{"stage": ..., "elapsed_s": ..., **metadata}``.
        Useful for per-query timing export where each call is one query.
        """
        rows = []
        for stage, values in self._timings.items():
            for i, v in enumerate(values):
                row: dict[str, Any] = {"stage": stage, "call_index": i, "elapsed_s": round(v, 6)}
                row.update(self._metadata)
                rows.append(row)
        return rows

    def save_flat_csv(self, path: str | Path) -> Path:
        """Write one CSV row per individual timing observation.

        Parameters
        ----------
        path:
            Output file path.

        Returns
        -------
        Path
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = self.to_flat_rows()
        if not rows:
            out.write_text("stage,call_index,elapsed_s\n")
            return out
        fieldnames = list(rows[0].keys())
        with out.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return out
