# Makefile — consistency-aware-llm-ranking
# Targets for common development and experiment workflows.
# Run `make help` to see available targets.

.PHONY: help install test lint check smoke-test noise-sweep scale-sweep \
        multiseed q1-tables clean-outputs

# ─── Configuration ────────────────────────────────────────────────────────────
PYTHON     := python
PYTEST     := pytest
OUTPUTS    := outputs

# ─── Help ─────────────────────────────────────────────────────────────────────
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Environment ──────────────────────────────────────────────────────────────
install:  ## Install package and dev dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

# ─── Quality ──────────────────────────────────────────────────────────────────
test:  ## Run all unit tests
	$(PYTEST)

lint:  ## Run ruff linter
	ruff check .

check: lint test  ## Run lint + tests

# ─── Repository verification ─────────────────────────────────────────────────
check-repo:  ## Verify repository setup (imports, key files, directories)
	$(PYTHON) scripts/check_repo_ready.py

# ─── Synthetic experiments (no network needed) ────────────────────────────────
smoke-test:  ## Run a single quick synthetic experiment (n=20, noise=0.2, seed=42)
	$(PYTHON) scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42

noise-sweep:  ## Run noise sweep (n=20, margin, seed=42) across 6 noise levels
	for NOISE in 0.05 0.10 0.15 0.20 0.25 0.30; do \
	  $(PYTHON) scripts/run_synthetic.py \
	    --n-items 20 --noise $$NOISE --seed 42 --weight-scheme margin \
	    --output-dir $(OUTPUTS)/noise_sweep_n$$NOISE; \
	done

scale-sweep:  ## Run scale sweep (noise=0.10, margin, seed=42) at n=10/20/50/100
	for N in 10 20 50 100; do \
	  $(PYTHON) scripts/run_synthetic.py \
	    --n-items $$N --noise 0.10 --seed 42 --weight-scheme margin \
	    --save-timings \
	    --output-dir $(OUTPUTS)/scale_sweep_n$$N; \
	done

multiseed:  ## Run margin + uniform multi-seed replication (n=20, noise=0.20)
	for SEED in 42 123 456 789 1234; do \
	  $(PYTHON) scripts/run_synthetic.py \
	    --n-items 20 --noise 0.20 --seed $$SEED --weight-scheme margin \
	    --output-dir $(OUTPUTS)/margin_multiseed_n20_noise0.20/seed_$$SEED; \
	  $(PYTHON) scripts/run_synthetic.py \
	    --n-items 20 --noise 0.20 --seed $$SEED --weight-scheme uniform \
	    --output-dir $(OUTPUTS)/uniform_multiseed_n20_noise0.20/seed_$$SEED; \
	done

# ─── Evidence package ─────────────────────────────────────────────────────────
q1-tables:  ## Regenerate Q1 journal tables from pre-committed outputs (offline)
	$(PYTHON) scripts/generate_q1_tables.py

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean-outputs:  ## Remove all generated experiment outputs (keeps paper_package)
	@echo "Removing generated outputs (noise_sweep, scale_sweep, multiseed)..."
	rm -rf $(OUTPUTS)/noise_sweep_n* $(OUTPUTS)/scale_sweep_n* \
	       $(OUTPUTS)/margin_multiseed_n20_noise0.20 \
	       $(OUTPUTS)/uniform_multiseed_n20_noise0.20 \
	       $(OUTPUTS)/q1_journal_package
	@echo "Done. Canonical evidence package (pub_vote_cmp_v2) preserved."
