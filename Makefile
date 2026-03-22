SHELL := /bin/bash

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

.PHONY: help setup check lint test synth-smoke q1-tables paper-tables

help:
	@echo "Targets:"
	@echo "  setup        Create venv and install dependencies"
	@echo "  check        Run repository readiness checks"
	@echo "  lint         Run Ruff lint checks"
	@echo "  test         Run pytest"
	@echo "  synth-smoke  Run a deterministic synthetic smoke experiment"
	@echo "  q1-tables    Regenerate outputs/q1_journal_package tables"
	@echo "  paper-tables Generate reports/paper_tables manuscript CSVs"

setup:
	python3 -m venv "$(VENV)"
	"$(PIP)" install -r requirements.txt
	"$(PIP)" install -e ".[dev]"

check:
	"$(PYTHON)" scripts/check_repo_ready.py

lint:
	"$(RUFF)" check .

test:
	"$(PYTEST)"

synth-smoke:
	"$(PYTHON)" scripts/run_synthetic.py \
		--n-items 20 \
		--noise 0.2 \
		--seed 42 \
		--output-dir outputs/synthetic_smoke \
		--overwrite-existing

q1-tables:
	"$(PYTHON)" scripts/generate_q1_tables.py \
		--pub-root outputs/pub_vote_cmp_v2 \
		--out-dir outputs/q1_journal_package

paper-tables:
	"$(PYTHON)" scripts/generate_paper_tables.py \
		--out-dir reports/paper_tables
