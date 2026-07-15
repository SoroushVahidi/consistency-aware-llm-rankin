#!/usr/bin/env python3
"""
exact_ilp_scip.py
==================
Backward-compatible shim for the exact open-source SCIP MWFAS solver used by
this investigation's scripts (e.g. ``run_exact_open_ilp_study.py``).

The linear-ordering MIP formulation this module used to implement directly
has been promoted to the canonical, reusable package location:
``consistency_ranker.mwfas_solver._solve_scip`` (exposed publicly via
``consistency_ranker.mwfas_solver.solve(..., method="scip")``). This file now
only re-exports that implementation under its original name
(``solve_ilp_scip``) so this investigation's scripts do not need to change,
and so results regenerated today are produced by the exact same code path
that is unit-tested in ``tests/test_exact_mwfas_scip.py`` and documented in
the manuscript.

Do not reintroduce a second copy of the MIP model here — import from
``consistency_ranker.mwfas_solver`` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from consistency_ranker.mwfas_solver import SolveStatus, _solve_scip  # noqa: E402

solve_ilp_scip = _solve_scip

__all__ = ["SolveStatus", "solve_ilp_scip"]
