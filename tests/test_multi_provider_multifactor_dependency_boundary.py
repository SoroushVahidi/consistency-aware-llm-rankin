"""Regression tests for the circular package dependency fix (repo hygiene
Stage 5, 2026-07-30) between ``consistency_ranker.multi_provider_eval`` and
``consistency_ranker.multifactor_acquisition``.

Before this fix, ``multi_provider_eval/providers.py`` imported three Azure
request-shaping constants from
``consistency_ranker.multifactor_acquisition.azure_request`` at module top
level, while ``multifactor_acquisition/live_judge.py`` imports
``multi_provider_eval.providers``/``multi_provider_eval.spending`` at module
top level -- a genuine circular package dependency (neither package could be
understood, tested, or extracted independently of the other), even though no
single file pair triggered a Python ``ImportError``.

The fix moved the three constants to their actual responsibility owner,
``consistency_ranker.multi_provider_eval.azure_request`` (the package that
actually shapes and issues the Azure request), and left
``consistency_ranker.multifactor_acquisition.azure_request`` as a
compatibility shim re-exporting the same names.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_in_fresh_process(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Each package must import independently in a fresh Python process
# ---------------------------------------------------------------------------


def test_multi_provider_eval_imports_independently_in_fresh_process():
    result = _run_in_fresh_process("import consistency_ranker.multi_provider_eval")
    assert result.returncode == 0, result.stderr


def test_multi_provider_eval_providers_imports_independently_in_fresh_process():
    """The specific module that used to cause the cycle."""
    result = _run_in_fresh_process("import consistency_ranker.multi_provider_eval.providers")
    assert result.returncode == 0, result.stderr


def test_multifactor_acquisition_imports_independently_in_fresh_process():
    result = _run_in_fresh_process("import consistency_ranker.multifactor_acquisition")
    assert result.returncode == 0, result.stderr


def test_multifactor_acquisition_live_judge_imports_independently_in_fresh_process():
    """The specific module on the other side of the former cycle."""
    result = _run_in_fresh_process(
        "import consistency_ranker.multifactor_acquisition.live_judge"
    )
    assert result.returncode == 0, result.stderr


def test_multi_provider_eval_imports_before_multifactor_acquisition_ever_loads():
    """Import order independence: multi_provider_eval must not require
    multifactor_acquisition to already be imported (or importable) first --
    this is exactly what the former circular dependency would have made
    fragile under a different import order."""
    result = _run_in_fresh_process(
        "import sys\n"
        "import consistency_ranker.multi_provider_eval.providers\n"
        "assert 'consistency_ranker.multifactor_acquisition' not in sys.modules, "
        "'multi_provider_eval.providers must not transitively import multifactor_acquisition'\n"
        "print('OK')\n"
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# The previous cycle is absent: no import edge remains from multi_provider_eval
# to multifactor_acquisition anywhere in the package.
# ---------------------------------------------------------------------------


def test_no_multi_provider_eval_module_imports_multifactor_acquisition():
    """Static check across every file in the package, not just providers.py --
    guards against the cycle being reintroduced anywhere else in the future."""
    package_dir = REPO_ROOT / "src" / "consistency_ranker" / "multi_provider_eval"
    offending = []
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "multifactor_acquisition" in stripped:
                offending.append(f"{path.name}: {stripped}")
    assert offending == [], (
        f"multi_provider_eval must not import multifactor_acquisition: {offending}"
    )


# ---------------------------------------------------------------------------
# Compatibility: the old import path still works and yields identical values
# ---------------------------------------------------------------------------


def test_compatibility_shim_reexports_identical_constant_values():
    from consistency_ranker.multi_provider_eval.azure_request import (
        AZURE_MAX_TOKENS_V1 as canonical_tokens,
    )
    from consistency_ranker.multi_provider_eval.azure_request import (
        AZURE_REQUEST_PROFILE as canonical_profile,
    )
    from consistency_ranker.multi_provider_eval.azure_request import (
        AZURE_SYSTEM_MESSAGE_V1 as canonical_message,
    )
    from consistency_ranker.multifactor_acquisition.azure_request import (
        AZURE_MAX_TOKENS_V1 as shim_tokens,
    )
    from consistency_ranker.multifactor_acquisition.azure_request import (
        AZURE_REQUEST_PROFILE as shim_profile,
    )
    from consistency_ranker.multifactor_acquisition.azure_request import (
        AZURE_SYSTEM_MESSAGE_V1 as shim_message,
    )

    assert shim_tokens == canonical_tokens == 16
    assert shim_profile == canonical_profile == "azure_compact_ab_v1"
    assert shim_message == canonical_message
    assert "A or B" in shim_message


def test_providers_module_uses_the_canonical_azure_request_location():
    """providers.py must source these constants from its own package
    (multi_provider_eval), not re-introduce a dependency on
    multifactor_acquisition, even indirectly through re-export chasing."""
    from consistency_ranker.multi_provider_eval import providers
    from consistency_ranker.multi_provider_eval.azure_request import (
        AZURE_MAX_TOKENS_V1,
    )

    assert providers.AZURE_MAX_TOKENS_V1 == AZURE_MAX_TOKENS_V1


# ---------------------------------------------------------------------------
# Behavior preservation: provider request shaping, spending/cost accounting
# ---------------------------------------------------------------------------


def test_azure_compact_profile_request_shaping_unchanged():
    """providers._build_pairwise_config(), fed the (moved) Azure compact-A/B
    constants, must still produce the exact same PairwiseConfig values as
    before the constants moved -- proving the import-path change did not
    alter request shaping."""
    from consistency_ranker.multi_provider_eval.providers import (
        AZURE_MAX_TOKENS_V1,
        AZURE_SYSTEM_MESSAGE_V1,
        _build_pairwise_config,
    )

    cfg, _call_cfg = _build_pairwise_config(
        "azure",
        max_tokens=AZURE_MAX_TOKENS_V1,
        system_message=AZURE_SYSTEM_MESSAGE_V1,
        dry_run=True,
    )
    assert cfg.max_tokens == 16
    assert cfg.system_message == AZURE_SYSTEM_MESSAGE_V1
    assert "A or B" in cfg.system_message


def test_spending_ceiling_accounting_unchanged():
    """Spending/cost accounting logic lives entirely in multi_provider_eval
    and was not touched by the constant move -- verify allow()/record()
    still behave as documented."""
    from consistency_ranker.multi_provider_eval.spending import SpendingCeiling

    ceiling = SpendingCeiling(
        max_new_calls_global=2,
        max_new_calls_per_provider={"azure": 1},
        max_prompt_tokens_global=1000,
    )
    assert ceiling.allow("azure") is True
    ceiling.record("azure", prompt_tokens=10, completion_tokens=5)
    assert ceiling.new_calls_global == 1
    assert ceiling.new_calls_by_provider["azure"] == 1
    # Second azure call should be refused: per-provider ceiling of 1 reached.
    assert ceiling.allow("azure") is False
