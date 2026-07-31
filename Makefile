SHELL := /bin/bash

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
OUTPUTS := outputs

.PHONY: help setup check lint test test-full typecheck verify-env \
        check-architecture \
        validate-evidence reproduce-ir-audit reproduce-real-llm-reanalysis \
        validate-offline doc-links secret-scan repo-ready \
        synth-smoke q1-tables paper-tables \
        noise-sweep scale-sweep multiseed clean-outputs

help:
	@echo "Targets:"
	@echo "  setup                          Create venv and install dependencies (incl. [dev,exact])"
	@echo "  verify-env                     Confirm Python/solver versions match the canonical spec"
	@echo "  check                          Run repository readiness checks (includes check-architecture)"
	@echo "  check-architecture             Fail if any consistency_ranker subpackage has a circular import dependency"
	@echo "  lint                           Run Ruff lint checks"
	@echo "  test                           Run pytest (fast: whatever is installed; SCIP tests skip if absent)"
	@echo "  test-full                      Run pytest and fail if any test is skipped (requires [exact] extra)"
	@echo "  typecheck                      No mypy configured in this repo -- documented no-op, see canonical_environment_specification.md"
	@echo "  validate-evidence              Validate the canonical evidence inventory's paths all exist"
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
	"$(PIP)" install -r requirements.txt
	"$(PIP)" install -e ".[dev,exact]"

verify-env:
	"$(PYTHON)" -c "import sys; print('python', sys.version)"
	"$(PYTHON)" -c "from consistency_ranker.mwfas_solver import verify_canonical_solver_version as v; print('PySCIPOpt', v())"
	@"$(PYTHON)" -c "import pyscipopt; print('SCIP (underlying)', pyscipopt.Model().version())" 2>/dev/null || true
	@echo "verify-env: OK"

check:
	"$(PYTHON)" scripts/check_repo_ready.py

check-architecture:
	"$(PYTHON)" scripts/check_architecture_boundaries.py

lint:
	"$(RUFF)" check .

test:
	"$(PYTEST)"

test-full:
	@SKIPPED=$$("$(PYTEST)" -q 2>&1 | tail -1 | grep -o '[0-9]* skipped' | grep -o '[0-9]*'); \
	if [ -n "$$SKIPPED" ] && [ "$$SKIPPED" != "0" ]; then \
		echo "test-full FAILED: $$SKIPPED test(s) skipped -- install '.[exact]' (and any other optional extra) for a full run, or use 'make test' if skips are expected"; \
		exit 1; \
	fi
	@echo "test-full: OK (0 skipped)"

typecheck:
	@echo "typecheck: no [tool.mypy] configuration exists in this repository (documented, not an oversight -- see canonical_environment_specification.md); this target is a deliberate no-op, not a failure"

validate-evidence:
	"$(PYTHON)" scripts/validate_canonical_evidence_manifest.py

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

repo-ready: check lint test validate-evidence doc-links secret-scan
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
