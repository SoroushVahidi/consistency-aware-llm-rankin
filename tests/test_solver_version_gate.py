"""
Tests for the canonical solver-version gate.

Repo Stage 4A (2026-07-30): `verify_canonical_solver_version()` and
`UnsupportedSolverVersionError` (added in `mwfas_solver.py` during Stage 4)
had zero test coverage anywhere in the repository until this file. These
tests exercise the gate's actual decision logic -- missing PySCIPOpt, missing
version metadata, an explicit version mismatch, the documented
`allow_mismatch` override, and (when the `[exact]` extra is actually
installed) the real installed environment -- rather than monkey-patching the
function itself away, which would test nothing.
"""

from __future__ import annotations

import sys
import types

import pytest

from consistency_ranker.mwfas_solver import (
    CANONICAL_PYSCIPOPT_VERSION,
    UnsupportedSolverVersionError,
    is_scip_available,
    verify_canonical_solver_version,
)


def _install_fake_pyscipopt(monkeypatch, *, version) -> None:
    """Inject a fake ``pyscipopt`` module into ``sys.modules``.

    ``version`` may be a string (sets ``__version__``) or ``None`` (omits
    ``__version__`` entirely, simulating a build that lacks version
    metadata). This patches only the import target the gate itself resolves
    at call time -- the gate function under test is never touched.
    """
    fake = types.ModuleType("pyscipopt")
    if version is not None:
        fake.__version__ = version
    monkeypatch.setitem(sys.modules, "pyscipopt", fake)


def _uninstall_pyscipopt(monkeypatch) -> None:
    """Force ``import pyscipopt`` to raise ImportError.

    Setting the ``sys.modules`` entry to ``None`` is the standard way to
    simulate "module not installed" for a module that may already be
    imported elsewhere in the process (e.g. by ``consistency_ranker``
    itself), without needing to actually uninstall the package.
    """
    monkeypatch.setitem(sys.modules, "pyscipopt", None)


class TestMissingPySCIPOpt:
    def test_raises_unsupported_solver_version_error_by_default(self, monkeypatch):
        _uninstall_pyscipopt(monkeypatch)
        with pytest.raises(UnsupportedSolverVersionError, match="not installed"):
            verify_canonical_solver_version()

    def test_error_message_names_the_required_version_and_install_hint(self, monkeypatch):
        _uninstall_pyscipopt(monkeypatch)
        with pytest.raises(UnsupportedSolverVersionError) as exc_info:
            verify_canonical_solver_version()
        message = str(exc_info.value)
        assert CANONICAL_PYSCIPOPT_VERSION in message
        assert "consistency-ranker[exact]" in message
        assert "allow_mismatch" in message

    def test_allow_mismatch_returns_sentinel_instead_of_raising(self, monkeypatch):
        _uninstall_pyscipopt(monkeypatch)
        result = verify_canonical_solver_version(allow_mismatch=True)
        assert result == "NOT_INSTALLED"


class TestMissingSolverVersionMetadata:
    def test_missing_dunder_version_treated_as_mismatch(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version=None)
        with pytest.raises(UnsupportedSolverVersionError, match="unknown"):
            verify_canonical_solver_version()

    def test_missing_dunder_version_with_allow_mismatch_returns_unknown(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version=None)
        result = verify_canonical_solver_version(allow_mismatch=True)
        assert result == "unknown"


class TestExplicitVersionMismatch:
    def test_wrong_version_raises_by_default(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version="5.0.0")
        with pytest.raises(UnsupportedSolverVersionError) as exc_info:
            verify_canonical_solver_version()
        message = str(exc_info.value)
        assert "5.0.0" in message
        assert CANONICAL_PYSCIPOPT_VERSION in message

    def test_wrong_version_diagnostic_explains_tie_breaking_risk(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version="5.0.0")
        with pytest.raises(UnsupportedSolverVersionError, match="not necessarily identical"):
            verify_canonical_solver_version()

    def test_wrong_version_with_allow_mismatch_returns_installed_version(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version="5.0.0")
        result = verify_canonical_solver_version(allow_mismatch=True)
        assert result == "5.0.0"


class TestSupportedVersion:
    def test_matching_version_returns_it_even_without_override(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version=CANONICAL_PYSCIPOPT_VERSION)
        result = verify_canonical_solver_version()
        assert result == CANONICAL_PYSCIPOPT_VERSION

    def test_matching_version_also_returns_it_with_allow_mismatch_true(self, monkeypatch):
        # allow_mismatch is only consulted when there IS a mismatch; a
        # matching version must not be rejected or altered by the flag.
        _install_fake_pyscipopt(monkeypatch, version=CANONICAL_PYSCIPOPT_VERSION)
        result = verify_canonical_solver_version(allow_mismatch=True)
        assert result == CANONICAL_PYSCIPOPT_VERSION


class TestCanonicalVsExploratoryModeDefaults:
    def test_default_call_is_canonical_mode_strict(self, monkeypatch):
        """``allow_mismatch`` defaults to False: canonical-reproduction calls
        that don't pass the flag explicitly must still fail loudly on a
        mismatch, not silently degrade to exploratory behavior."""
        _install_fake_pyscipopt(monkeypatch, version="999.0.0")
        with pytest.raises(UnsupportedSolverVersionError):
            verify_canonical_solver_version()

    def test_exploratory_mode_is_opt_in_only(self, monkeypatch):
        _install_fake_pyscipopt(monkeypatch, version="999.0.0")
        # Canonical (default) call still raises even after an exploratory
        # call succeeded, proving the two calls are independent and the
        # override is never "sticky" across call sites.
        assert verify_canonical_solver_version(allow_mismatch=True) == "999.0.0"
        with pytest.raises(UnsupportedSolverVersionError):
            verify_canonical_solver_version()


@pytest.mark.skipif(
    not is_scip_available(),
    reason="PySCIPOpt not installed (install the '[exact]' extra: "
    'pip install "consistency-ranker[exact]")',
)
class TestRealInstalledEnvironment:
    """Exercises the real installed PySCIPOpt/SCIP environment directly, with
    no mocking, whenever the '[exact]' extra is actually available (e.g. in
    the repository's own .venv or the CI solver-enabled job)."""

    def test_real_environment_matches_canonical_version(self):
        installed = verify_canonical_solver_version()
        assert installed == CANONICAL_PYSCIPOPT_VERSION

    def test_real_environment_reports_underlying_scip_version(self):
        import pyscipopt

        scip_version = pyscipopt.Model().version()
        assert scip_version
