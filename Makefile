SHELL := /bin/bash

VENV ?= .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python)
PIP ?= $(if $(wildcard $(VENV)/bin/pip),$(VENV)/bin/pip,python -m pip)
PYTEST ?= $(if $(wildcard $(VENV)/bin/pytest),$(VENV)/bin/pytest,pytest)
RUFF ?= $(if $(wildcard $(VENV)/bin/ruff),$(VENV)/bin/ruff,ruff)
OUTPUTS := outputs

.PHONY: help setup check lint lint-full test test-full test-real-data typecheck verify-env \
        check-architecture check-portability \
        validate-evidence validate-claims cloud-validate cloud-validate-solver cloud-validate-all reproduce-ir-audit reproduce-real-llm-reanalysis \
        validate-offline doc-links secret-scan repo-ready \
        synth-smoke q1-tables paper-tables \
        noise-sweep scale-sweep multiseed clean-outputs

MAINTAINED_LINT_PATHS := \
	scripts/check_active_portability.py \
	scripts/check_architecture_boundaries.py \
	scripts/check_repo_ready.py \
	scripts/run_real_llm_clustered_reanalysis.py \
	scripts/run_secret_scan.py \
	scripts/run_cloud_validation.py \
	scripts/validate_canonical_evidence_manifest.py \
	scripts/validate_claim_evidence_registry.py \
	scripts/validate_report_links.py \
	src/consistency_ranker/experiment_cli.py \
	src/consistency_ranker/provenance.py \
	src/consistency_ranker/real_llm_reanalysis/population.py \
	tests/test_active_portability.py \
	tests/test_check_architecture_boundaries.py \
	tests/test_check_repo_ready.py \
	tests/test_cli_validation.py \
	tests/test_experiment_cli.py \
	tests/test_offline_validation_scripts.py \
	tests/test_provenance.py \
	tests/test_real_llm_clustered_reanalysis.py \
	tests/test_secret_scan.py \
	tests/test_cloud_validation.py

help:
	@echo "Targets:"
	@echo "  setup                          Create venv and install dependencies (incl. [dev,exact,llm])"
	@echo "  verify-env                     Confirm Python/solver versions match the canonical spec"
	@echo "  check                          Run repository readiness checks (includes check-architecture)"
	@echo "  check-architecture             Fail if any consistency_ranker subpackage has a circular import dependency"
	@echo "  check-portability              Fail if active code/docs contain machine-specific paths"
	@echo "  lint                           Run Ruff on maintained readiness/provenance/reanalysis paths"
	@echo "  lint-full                      Run Ruff on the whole repository (known historical debt)"
	@echo "  test                           Run pytest (fast: whatever is installed; SCIP tests skip if absent)"
	@echo "  test-full                      Run pytest and fail if any test is skipped (requires [exact] extra)"
	@echo "  test-real-data                 Run the 'real_data' tier (needs 'python scripts/prepare_datasets.py --dataset all' first)"
	@echo "  cloud-validate                 Canonical release validation, core tier (mirrors ci.yml 'tests' job)"
	@echo "  cloud-validate-solver          Canonical release validation, solver tier (mirrors ci.yml 'tests-solver-enabled' job)"
	@echo "  cloud-validate-all             Canonical release validation, all local tiers (core+solver+real-data if already prepared)"
	@echo "  typecheck                      No mypy configured in this repo -- documented no-op, see canonical_environment_specification.md"
	@echo "  validate-evidence              Validate the canonical evidence inventory's paths all exist"
	@echo "  validate-claims                Validate docs/claim_evidence_registry.yaml paths and internal consistency"
	@echo "  reproduce-ir-audit             Re-run the classical IR evidence audit and diff against committed output"
	@echo "  reproduce-real-llm-reanalysis  Re-run the real-LLM clustered re-analysis and diff against committed output"
	@echo "  validate-offline               Run the full offline validation workflow (env + both reproductions + tests + link/manifest checks)"
	@echo "  doc-links                      Validate every markdown link in reports/README.md resolves"
	@echo "  secret-scan                    Grep tracked+staged files for secret-shaped patterns"
	@echo "  repo-ready                     check + lint + test + validate-evidence + doc-links + secret-scan"
	@echo "  synth-smoke                    Run a deterministic synthetic smoke experiment"
	@echo "  q1-tables                      Regenerate outputs/q1_journal_package tables (historical pipeline)"
	@echo "  paper-tables                   Generate reports/paper_tables manuscript CSVs"
	@echo "  noise-sweep                    Run noise sweep across 6 noise levels"
	@echo "  scale-sweep                    Run scale sweep at n=10/20/50/100"
	@echo "  multiseed                      Run margin + uniform multi-seed replication"
	@echo "  clean-outputs                  Remove generated experiment outputs"

setup:
	python3 -m venv "$(VENV)"
	"$(VENV)/bin/pip" install -r requirements.txt
	"$(VENV)/bin/pip" install -e ".[dev,exact,llm]"
	"$(VENV)/bin/pip" install gurobipy

verify-env:
	"$(PYTHON)" -c "import sys; print('python', sys.version)"
	"$(PYTHON)" -c "from consistency_ranker.mwfas_solver import verify_canonical_solver_version as v; print('PySCIPOpt', v())"
	@"$(PYTHON)" -c "import pyscipopt; print('SCIP (underlying)', pyscipopt.Model().version())" 2>/dev/null || true
	@echo "verify-env: OK"

check:
	"$(PYTHON)" scripts/check_repo_ready.py

check-architecture:
	"$(PYTHON)" scripts/check_architecture_boundaries.py

check-portability:
	"$(PYTHON)" scripts/check_active_portability.py

lint:
	"$(RUFF)" check $(MAINTAINED_LINT_PATHS)

lint-full:
	"$(RUFF)" check .

test:
	"$(PYTEST)"

test-full:
	@TMP_OUT=$$(mktemp); \
	"$(PYTEST)" -q 2>&1 | tee "$$TMP_OUT"; \
	PYTEST_STATUS=$${PIPESTATUS[0]}; \
	SKIPPED=$$(tail -20 "$$TMP_OUT" | grep -o '[0-9][0-9]* skipped' | tail -1 | grep -o '[0-9][0-9]*' || true); \
	rm -f "$$TMP_OUT"; \
	if [ "$$PYTEST_STATUS" -ne 0 ]; then \
		exit "$$PYTEST_STATUS"; \
	fi; \
	if [ -n "$$SKIPPED" ] && [ "$$SKIPPED" != "0" ]; then \
		echo "test-full FAILED: $$SKIPPED test(s) skipped -- install '.[exact]' (and any other optional extra) for a full run, or use 'make test' if skips are expected"; \
		exit 1; \
	fi
	@echo "test-full: OK (0 skipped)"

test-real-data:
	@if [ ! -f data/processed/beir/scidocs/queries.jsonl ] || \
	   [ ! -f data/processed/beir/fiqa/queries.jsonl ] || \
	   [ ! -f data/processed/hotpotqa/queries.jsonl ] || \
	   [ ! -f data/processed/bright/queries.jsonl ]; then \
		echo "test-real-data: prepared datasets not found under data/processed/."; \
		echo "  Run: python scripts/download_datasets.py   (network access required)"; \
		echo "  Then: python scripts/prepare_datasets.py --dataset all"; \
		exit 1; \
	fi
	"$(PYTEST)" -m real_data

cloud-validate:
	python3 scripts/run_cloud_validation.py --tier core

cloud-validate-solver:
	python3 scripts/run_cloud_validation.py --tier solver

cloud-validate-all:
	python3 scripts/run_cloud_validation.py --tier all

typecheck:
	@echo "typecheck: no [tool.mypy] configuration exists in this repository (documented, not an oversight -- see canonical_environment_specification.md); this target is a deliberate no-op, not a failure"

validate-evidence:
	"$(PYTHON)" scripts/validate_canonical_evidence_manifest.py

validate-claims:
	"$(PYTHON)" scripts/validate_claim_evidence_registry.py

reproduce-ir-audit:
	"$(PYTHON)" scripts/run_offline_validation_workflow.py --only ir-audit

reproduce-real-llm-reanalysis:
	"$(PYTHON)" scripts/run_offline_validation_workflow.py --only real-llm

validate-offline:
	"$(PYTHON)" scripts/run_offline_validation_workflow.py

doc-links:
	"$(PYTHON)" scripts/validate_report_links.py

secret-scan:
	"$(PYTHON)" scripts/run_secret_scan.py

repo-ready: check check-portability lint test validate-evidence validate-claims doc-links secret-scan
	@echo "repo-ready: all checks passed"

synth-smoke:
	"$(PYTHON)" scripts/run_synthetic.py \
	--n-items 20 \
	--noise 0.2 \
	--seed 42 \
	--output-dir $(OUTPUTS)/synthetic_smoke \
	--overwrite-existing

q1-tables:
	"$(PYTHON)" scripts/generate_q1_tables.py \
	--pub-root outputs/pub_vote_cmp_v2 \
	--out-dir outputs/q1_journal_package

paper-tables:
	"$(PYTHON)" scripts/generate_paper_tables.py \
	--out-dir reports/paper_tables

noise-sweep:
	for NOISE in 0.05 0.10 0.15 0.20 0.25 0.30; do \
	  "$(PYTHON)" scripts/run_synthetic.py \
	    --n-items 20 --noise $$NOISE --seed 42 --weight-scheme margin \
	    --output-dir $(OUTPUTS)/noise_sweep_n$$NOISE; \
	done

scale-sweep:
	for N in 10 20 50 100; do \
	  "$(PYTHON)" scripts/run_synthetic.py \
	    --n-items $$N --noise 0.10 --seed 42 --weight-scheme margin \
	    --save-timings \
	    --output-dir $(OUTPUTS)/scale_sweep_n$$N; \
	done

multiseed:
	for SEED in 42 123 456 789 1234; do \
	  "$(PYTHON)" scripts/run_synthetic.py \
	    --n-items 20 --noise 0.20 --seed $$SEED --weight-scheme margin \
	    --output-dir $(OUTPUTS)/margin_multiseed_n20_noise0.20/seed_$$SEED; \
	  "$(PYTHON)" scripts/run_synthetic.py \
	    --n-items 20 --noise 0.20 --seed $$SEED --weight-scheme uniform \
	    --output-dir $(OUTPUTS)/uniform_multiseed_n20_noise0.20/seed_$$SEED; \
	done

clean-outputs:
	@echo "Removing generated outputs (noise_sweep, scale_sweep, multiseed)..."
	rm -rf $(OUTPUTS)/noise_sweep_n* $(OUTPUTS)/scale_sweep_n* \
	       $(OUTPUTS)/margin_multiseed_n20_noise0.20 \
	       $(OUTPUTS)/uniform_multiseed_n20_noise0.20 \
	       $(OUTPUTS)/q1_journal_package \
	       $(OUTPUTS)/synthetic_smoke
	@echo "Done. Canonical evidence packages (pub_vote_cmp_all4/paper_package and historical pub_vote_cmp_v2) preserved."
