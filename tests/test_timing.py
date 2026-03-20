"""
Tests for timing utilities.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from consistency_ranker.utils.timing import Timer, TimingAccumulator, timed


# ---------------------------------------------------------------------------
# Timer context manager
# ---------------------------------------------------------------------------


class TestTimer:
    def test_elapsed_is_none_before_exit(self):
        t = Timer("test")
        t.__enter__()
        assert t.elapsed is None
        t.__exit__(None, None, None)

    def test_elapsed_is_nonnegative_after_exit(self):
        with Timer("test") as t:
            pass
        assert t.elapsed is not None
        assert t.elapsed >= 0.0

    def test_elapsed_is_float(self):
        with Timer("test") as t:
            pass
        assert isinstance(t.elapsed, float)

    def test_measures_sleep_approximately(self):
        with Timer("sleep") as t:
            time.sleep(0.05)
        assert t.elapsed >= 0.04  # allow some tolerance

    def test_records_into_accumulator(self):
        acc = TimingAccumulator()
        with Timer("stage", accumulator=acc):
            pass
        assert len(acc.all_timings("stage")) == 1
        assert acc.all_timings("stage")[0] >= 0.0

    def test_name_attribute(self):
        t = Timer("my_stage")
        assert t.name == "my_stage"

    def test_multiple_uses_independent(self):
        """Each `with Timer(...)` block should produce an independent elapsed."""
        with Timer("a") as t1:
            pass
        with Timer("b") as t2:
            pass
        assert t1.elapsed is not None
        assert t2.elapsed is not None


# ---------------------------------------------------------------------------
# timed decorator
# ---------------------------------------------------------------------------


class TestTimedDecorator:
    def test_return_value_preserved(self):
        @timed("add")
        def add(x, y):
            return x + y

        assert add(1, 2) == 3

    def test_records_into_accumulator(self):
        acc = TimingAccumulator()

        @timed("fn", accumulator=acc)
        def fn():
            return 42

        fn()
        assert len(acc.all_timings("fn")) == 1

    def test_multiple_calls_accumulate(self):
        acc = TimingAccumulator()

        @timed("counter", accumulator=acc)
        def inc():
            return 1

        inc()
        inc()
        inc()
        assert len(acc.all_timings("counter")) == 3

    def test_uses_function_name_by_default(self):
        acc = TimingAccumulator()

        @timed(accumulator=acc)
        def my_func():
            pass

        my_func()
        assert "my_func" in acc.stages()

    def test_wraps_preserves_function_name(self):
        @timed("stage")
        def original():
            pass

        assert original.__name__ == "original"


# ---------------------------------------------------------------------------
# TimingAccumulator
# ---------------------------------------------------------------------------


class TestTimingAccumulator:
    def test_empty_stages(self):
        acc = TimingAccumulator()
        assert acc.stages() == []

    def test_record_and_retrieve(self):
        acc = TimingAccumulator()
        acc.record("build", 1.5)
        acc.record("build", 0.5)
        assert acc.all_timings("build") == [1.5, 0.5]

    def test_total(self):
        acc = TimingAccumulator()
        acc.record("s1", 1.0)
        acc.record("s1", 2.0)
        assert acc.total("s1") == pytest.approx(3.0)

    def test_mean_time(self):
        acc = TimingAccumulator()
        acc.record("s", 1.0)
        acc.record("s", 3.0)
        assert acc.mean_time("s") == pytest.approx(2.0)

    def test_median_time(self):
        acc = TimingAccumulator()
        acc.record("s", 1.0)
        acc.record("s", 2.0)
        acc.record("s", 3.0)
        assert acc.median_time("s") == pytest.approx(2.0)

    def test_max_time(self):
        acc = TimingAccumulator()
        acc.record("s", 1.0)
        acc.record("s", 5.0)
        acc.record("s", 3.0)
        assert acc.max_time("s") == pytest.approx(5.0)

    def test_grand_total(self):
        acc = TimingAccumulator()
        acc.record("a", 1.0)
        acc.record("b", 2.0)
        acc.record("a", 0.5)
        assert acc.grand_total() == pytest.approx(3.5)

    def test_mean_time_no_data_returns_zero(self):
        acc = TimingAccumulator()
        assert acc.mean_time("nonexistent") == 0.0

    def test_max_time_no_data_returns_zero(self):
        acc = TimingAccumulator()
        assert acc.max_time("nonexistent") == 0.0

    def test_metadata(self):
        acc = TimingAccumulator()
        acc.set_metadata(dataset="scidocs", n_items=20)
        assert acc._metadata["dataset"] == "scidocs"
        assert acc._metadata["n_items"] == 20

    def test_summary_rows_columns(self):
        acc = TimingAccumulator()
        acc.record("build", 1.0)
        acc.record("build", 2.0)
        rows = acc.summary_rows()
        assert len(rows) == 1
        row = rows[0]
        expected_keys = {"stage", "n_calls", "total_s", "mean_s", "median_s", "max_s"}
        assert expected_keys == set(row.keys())

    def test_summary_rows_values(self):
        acc = TimingAccumulator()
        acc.record("s", 1.0)
        acc.record("s", 3.0)
        rows = acc.summary_rows()
        assert rows[0]["stage"] == "s"
        assert rows[0]["n_calls"] == 2
        assert rows[0]["total_s"] == pytest.approx(4.0)
        assert rows[0]["mean_s"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestSaveCSV:
    def test_csv_written(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("load", 0.1)
        acc.record("build", 0.2)
        out = acc.save_csv(tmp_path / "timings.csv")
        assert out.exists()

    def test_csv_contains_expected_columns(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("eval", 0.5)
        out = acc.save_csv(tmp_path / "timings.csv")
        content = out.read_text()
        for col in ["stage", "n_calls", "total_s", "mean_s", "median_s", "max_s"]:
            assert col in content

    def test_csv_stage_appears_in_rows(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("my_stage", 1.23)
        out = acc.save_csv(tmp_path / "t.csv")
        assert "my_stage" in out.read_text()

    def test_csv_creates_parent_dirs(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("s", 0.1)
        out = acc.save_csv(tmp_path / "a" / "b" / "t.csv")
        assert out.exists()


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


class TestSaveJSON:
    def test_json_written(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("load", 0.1)
        out = acc.save_json(tmp_path / "t.json")
        assert out.exists()

    def test_json_contains_summary_key(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("s", 0.1)
        out = acc.save_json(tmp_path / "t.json")
        data = json.loads(out.read_text())
        assert "summary" in data
        assert "raw" in data
        assert "metadata" in data

    def test_json_summary_has_expected_columns(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.record("stage_a", 0.5)
        out = acc.save_json(tmp_path / "t.json")
        data = json.loads(out.read_text())
        row = data["summary"][0]
        for col in ["stage", "n_calls", "total_s", "mean_s", "median_s", "max_s"]:
            assert col in row

    def test_json_metadata_saved(self, tmp_path: Path):
        acc = TimingAccumulator()
        acc.set_metadata(dataset="hotpotqa")
        acc.record("s", 0.1)
        out = acc.save_json(tmp_path / "t.json")
        data = json.loads(out.read_text())
        assert data["metadata"]["dataset"] == "hotpotqa"
