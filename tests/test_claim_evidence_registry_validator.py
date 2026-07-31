"""Tests for scripts/validate_claim_evidence_registry.py's consistency
checks -- specifically the guard-rails that prevent a future edit from
mislabeling internal-only validation (e.g. the Gurobi solver checks) or a
superseded/historical result as canonical or manuscript-applicable.

Uses a temporary registry file (not the real docs/claim_evidence_registry.yaml)
so these tests exercise the validator's *logic* against deliberately-bad
input, independent of the real registry's current contents.
"""

from __future__ import annotations

import yaml

import scripts.validate_claim_evidence_registry as validator

_BASE_CLAIM = {
    "id": "TEST-01",
    "claim": "A test claim.",
    "status": "canonical",
    "canonical": True,
    "manuscript_applicable": True,
    "implementation_paths": [],
    "generating_scripts": [],
    "evidence_paths": [],
    "statistical_unit": "n/a",
    "correction_method": "n/a",
    "sample_size": "n/a",
    "limitations": [],
    "superseded_by": [],
}


def _write_registry(tmp_path, claims):
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump({"claims": claims}))
    return path


def test_valid_minimal_registry_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [dict(_BASE_CLAIM)]))
    assert validator.main() == 0


def test_duplicate_ids_rejected(tmp_path, monkeypatch):
    claims = [dict(_BASE_CLAIM), dict(_BASE_CLAIM)]
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, claims))
    assert validator.main() == 1


def test_canonical_internal_validation_rejected(tmp_path, monkeypatch):
    """Guards against ever mislabeling something like the Gurobi solver
    cross-validation as canonical evidence."""
    claim = dict(_BASE_CLAIM)
    claim["status"] = "internal_validation"
    claim["canonical"] = True
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_canonical_superseded_rejected(tmp_path, monkeypatch):
    """Guards against using a superseded row-level/historical result as
    canonical evidence."""
    claim = dict(_BASE_CLAIM)
    claim["status"] = "superseded"
    claim["canonical"] = True
    claim["manuscript_applicable"] = False
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_manuscript_applicable_internal_validation_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["status"] = "internal_validation"
    claim["canonical"] = False
    claim["manuscript_applicable"] = True
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_manuscript_applicable_superseded_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["status"] = "superseded"
    claim["canonical"] = False
    claim["manuscript_applicable"] = True
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_missing_evidence_path_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["canonical"] = False
    claim["manuscript_applicable"] = False
    claim["evidence_paths"] = ["definitely/not/a/real/path.csv"]
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_unknown_superseded_by_reference_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["canonical"] = False
    claim["manuscript_applicable"] = False
    claim["superseded_by"] = ["NONEXISTENT-99"]
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_invalid_status_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["canonical"] = False
    claim["manuscript_applicable"] = False
    claim["status"] = "made_up_status"
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1


def test_missing_required_field_rejected(tmp_path, monkeypatch):
    claim = dict(_BASE_CLAIM)
    claim["canonical"] = False
    claim["manuscript_applicable"] = False
    del claim["limitations"]
    monkeypatch.setattr(validator, "_REGISTRY_PATH", _write_registry(tmp_path, [claim]))
    assert validator.main() == 1
