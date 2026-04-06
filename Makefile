SHELL := /bin/bash

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
OUTPUTS := outputs

.PHONY: help setup check lint test synth-smoke q1-tables paper-tables \
        noise-sweep scale-sweep multiseed clean-outputs

help:
@echo "Targets:"
@echo "  setup        Create venv and install dependencies"
@echo "  check        Run repository readiness checks"
@echo "  lint         Run Ruff lint checks"
@echo "  test         Run pytest"
@echo "  synth-smoke  Run a deterministic synthetic smoke experiment"
@echo "  q1-tables    Regenerate outputs/q1_journal_package tables"
@echo "  paper-tables Generate reports/paper_tables manuscript CSVs"
@echo "  noise-sweep  Run noise sweep across 6 noise levels"
@echo "  scale-sweep  Run scale sweep at n=10/20/50/100"
@echo "  multiseed    Run margin + uniform multi-seed replication"
@echo "  clean-outputs Remove generated experiment outputs"

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
