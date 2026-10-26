"""Offline safeguards and independent small-instance checks; no model inference."""

import itertools
import json
import sqlite3
import subprocess
from pathlib import Path

import networkx as nx
import pytest

from . import worker
from .analyze import classify, decomposition, evaluate_pool, make_graph, summarize
from .common import (
    EVALUATION_COUNTS,
    absolute_interpreter,
    atomic,
    database,
    paired_disposition,
    parse,
    requests_for,
)
from .gate import gate_report


def record(uid, pair, orientation, variant="primary", repeat=0, winner=None):
    winner = winner or pair[0]
    shown_first = pair[orientation]
    label = "A" if winner == shown_first else "B"
    return {
        "uid": uid,
        "pair": pair,
        "orientation": orientation,
        "variant": variant,
        "repeat": repeat,
        "status": "valid",
        "label": label,
        "winner": winner,
        "raw": label,
        "latency_s": 0.01,
    }


def perfect_development():
    rows = []
    for q in range(12):
        for variant in ("primary", "robustness"):
            for pair_id in range(4):
                pair = [f"p{pair_id}:a", f"p{pair_id}:b"]
                for orientation in (0, 1):
                    rows.append(record(f"q:{q}", pair, orientation, variant))
        for orientation in (0, 1):
            rows.append(record(f"q:{q}", ["p0:a", "p0:b"], orientation, repeat=1))
    for q in range(12):
        for orientation in (0, 1):
            rows.append(record(f"control:{q:02d}", ["relevant", "unrelated"], orientation))
    return rows


def report(rows):
    return gate_report(
        rows,
        {"main_responses": 67860, "analysis_reserve_s": 3600, "max_active_wall_s": 43200},
        {"gpu_peak_allocated_bytes": 15_000_000_000, "gpu_total_bytes": 17_000_000_000},
        100,
    )


@pytest.mark.parametrize("raw", ["A", "B", " A\n", "\nB "])
def test_strict_directional_parser(raw):
    assert parse(raw) == ("valid", raw.strip())


@pytest.mark.parametrize("raw", ["A because B is worse", "A.", '{"choice":"A"}', "", "AB"])
def test_no_default_or_format_repair(raw):
    assert parse(raw)[0] == "invalid"


@pytest.mark.parametrize("raw", ["TIE", "N", "ABSTAIN", "I cannot compare these"])
def test_abstentions_are_retained(raw):
    assert parse(raw) == ("abstention", None)


def test_capped_valid_looking_label_is_invalid():
    assert parse("A", capped=True) == ("invalid_capped", None)


def test_perfect_instrument_passes_gate():
    assert report(perfect_development())["gate_pass"]


def test_always_a_does_not_pass_despite_perfect_parseability():
    rows = perfect_development()
    for row in rows:
        row.update(label="A", raw="A", winner=row["pair"][row["orientation"]])
    result = report(rows)
    assert not result["gate_pass"]
    assert "primary_position" in result["failed_checks"]
    assert "primary_reversal" in result["failed_checks"]
    assert "semantic_control_1" in result["failed_checks"]


def test_abstaining_instrument_fails():
    rows = perfect_development()
    for row in rows[:40]:
        row.update(status="abstention", label=None, winner=None, raw="N")
    assert not report(rows)["gate_pass"]


def test_fresh_repetition_instability_fails():
    rows = perfect_development()
    for row in rows:
        if row["repeat"]:
            row["raw"] = "B" if row["raw"] == "A" else "A"
    assert "repeatability" in report(rows)["failed_checks"]


def test_prompt_semantic_instability_fails():
    rows = perfect_development()
    for row in rows:
        if row["variant"] == "robustness":
            row["winner"] = row["pair"][1]
    assert "prompt_robustness" in report(rows)["failed_checks"]


def test_missing_development_records_cannot_pass():
    assert not report(perfect_development()[:-3])["gate_pass"]


def test_roster_size_follows_precision_design():
    assert sum(EVALUATION_COUNTS) == 390
    assert 1.96 * (0.25 / 390) ** 0.5 < 0.05


def test_union_pairs_are_deduplicated_and_swapped():
    row = {
        "uid": "test",
        "pools": {
            "natural": list(map(str, range(12))),
            "enriched": list(map(str, range(10))) + ["12", "13"],
        },
    }
    requests = requests_for(row)
    assert len(requests) == 174
    assert len({r["id"] for r in requests}) == 174
    assert len(requests_for(row, development=True)) == 18


def test_missing_is_not_conflict_or_zero_vote():
    assert paired_disposition([record("q", ["a", "b"], 0)])[0] == "missing"
    graph, counts = make_graph(["a", "b", "isolate"], [])
    assert set(graph) == {"a", "b", "isolate"}
    assert graph.number_of_edges() == 0
    assert counts["missing"] == 3


def test_same_displayed_choice_is_actual_document_conflict():
    first = record("q", ["a", "b"], 0, winner="a")
    second = record("q", ["a", "b"], 1, winner="b")
    assert first["label"] == second["label"] == "A"
    assert paired_disposition([first, second]) == ("conflict", None)


def cyclic_records():
    edges = {("a", "b"): "a", ("b", "c"): "b", ("a", "c"): "c"}
    return [
        record("q", list(pair), orientation, winner=winner)
        for pair, winner in edges.items()
        for orientation in (0, 1)
    ]


def test_existing_exact_solver_matches_independent_enumeration():
    out = evaluate_pool(["a", "b", "c"], cyclic_records(), {"a": 1, "outside": 1})
    assert out["cyclic"]
    assert out["exact_status"]["proven_optimal"]
    edges = out["edges"]
    optimum = min(
        sum(order.index(a) > order.index(b) for a, b in edges)
        for order in itertools.permutations(["a", "b", "c"])
    )
    assert len(out["methods"]["exact"]["removed"]) == optimum == 1
    for name in ("greedy", "exact"):
        assert nx.is_directed_acyclic_graph(nx.DiGraph(out["methods"][name]["edges"]))


def test_grade_profile_zero_and_harm_are_distinct():
    args = {"removed": [("a", "b", 1)], "baseline": ["a", "b", "c"], "ranking": ["b", "a", "c"]}
    assert (
        classify(**args, qrels={"a": 1, "b": 1}, delta=0) == "changed_ranking_equal_grade_profile"
    )
    assert classify(**args, qrels={}, delta=0) == "changed_ranking_zero_positive_pool"
    assert classify(**args, qrels={"a": 1}, delta=-0.1) == "utility_harm"


def test_uncertainty_does_not_hide_empty_conditional_denominator():
    out = evaluate_pool(["a", "b", "c"], [], {"a": 1})
    rows = [{"dataset": "test", "conditions": {"natural": {"strict": out}}}]
    result = decomposition(rows, "natural", "greedy")
    assert result["conditional_on_ranking_change"]["gain"]["rate"] is None
    assert result["conditional_on_ranking_change"]["gain"]["empty_bootstrap_denominators"] == 10000
    assert result["classes"]["utility_gain"]["wilson95"][1] > 0


def test_sqlite_completed_records_cannot_be_replaced(tmp_path):
    connection = database(tmp_path / "test.sqlite3")
    connection.execute("INSERT INTO responses VALUES('same','evaluation','q','{}')")
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO responses VALUES('same','evaluation','q','{}')")
    connection.close()


def test_analysis_interpreter_keeps_virtual_environment_symlink(tmp_path):
    binary = tmp_path / "python-real"
    binary.touch()
    virtual_python = tmp_path / "venv" / "bin" / "python"
    virtual_python.parent.mkdir(parents=True)
    virtual_python.symlink_to(binary)
    assert absolute_interpreter(virtual_python) == str(virtual_python)
    assert absolute_interpreter(virtual_python) != str(virtual_python.resolve())


def test_actual_launcher_keeps_virtual_environment_executable(tmp_path):
    run = tmp_path / "private-run"
    (run / "logs").mkdir(parents=True)
    marker = tmp_path / "invoked-interpreter"
    target = tmp_path / "underlying-interpreter"
    target.write_text('#!/bin/sh\nprintf "%s\\n" "$0" > "' + str(marker) + '"\n')
    target.chmod(0o700)
    virtual_python = tmp_path / "venv" / "bin" / "python"
    virtual_python.parent.mkdir(parents=True)
    virtual_python.symlink_to(target)
    script = Path(__file__).parent / "launch.sh"
    subprocess.run(["bash", str(script), str(run), str(virtual_python)], check=True)
    assert marker.read_text().strip() == str(virtual_python)


def test_failed_gate_does_not_launch_main(monkeypatch, tmp_path):
    events = []

    class FailedInstrument:
        def __init__(self, *_args, **_kwargs):
            pass

        def load_model(self):
            events.append("load")

        def validate(self):
            return {"gate_pass": False}

        def heartbeat(self, state):
            events.append(state)

        def main_collection(self, _report):
            pytest.fail("Main launched after failed validation")

        def close(self):
            events.append("close")

    monkeypatch.setattr(worker, "Worker", FailedInstrument)
    monkeypatch.setattr("sys.argv", ["worker", "--run", str(tmp_path)])
    assert worker.main() == 2
    assert events == ["load", "FAILED", "close"]


def test_summary_uses_query_units_and_fixed_two_test_family(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "results").mkdir()
    rows, roster = [], []
    for index in range(3):
        uid = "q:" + str(index)
        out = evaluate_pool(["a", "b", "c"], cyclic_records(), {"a": 1})
        row = {
            "uid": uid,
            "dataset": "test",
            "stratum": "test",
            "conditions": {c: {"strict": out} for c in ("natural", "enriched")},
        }
        rows.append(row)
        roster.append({"uid": uid, "dataset": "test", "stratum": "test"})
        atomic(tmp_path / "results" / f"{index}.json", row)
    (tmp_path / "inputs/evaluation.jsonl").write_text("".join(json.dumps(r) + "\n" for r in roster))
    summarize(tmp_path)
    summary = json.loads((tmp_path / "ANALYSIS_SUMMARY.json").read_text())
    assert summary["planned_queries"] == summary["completed_queries"] == 3
    assert len(summary["natural_pool_secondary_effects"]) == 2
    assert all(r["n"] == 3 for r in summary["natural_pool_secondary_effects"])
