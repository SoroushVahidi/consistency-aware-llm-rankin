# SNCS 2026 Reproducibility Quickstart (Reviewer-Facing)

**Manuscript:** Structural Consistency Is Not Retrieval Utility…  
**Freeze ledger:** `SUBMISSION_FREEZE.md`  
**This guide does not claim one-command full-study reproduction.**

Use the labeled tracks below. Prefer verifying against committed canonical
CSVs and figures unless you intentionally regenerate expensive layers.

## Environment setup

```bash
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin
git checkout papers/sncs-2026-foundation   # or the freeze tag when authorized
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"          # fast local track
# for solver-enabled track:
python -m pip install -e ".[dev,exact]"    # installs PySCIPOpt (SCIP)
```

| Requirement | Value |
|---|---|
| Python | 3.11+ (verified here with 3.12.3) |
| Core deps | `requirements.txt` / `pyproject.toml` (install constraints, not a lockfile) |
| Exact solver | SCIP via `pyscipopt` (`[exact]` extra). **Gurobi is not required** for manuscript results |
| OS notes | Linux verified; no Docker image is required |

Pin the commit you reproduce:

```bash
git rev-parse HEAD
# compare to SUBMISSION_FREEZE.md
```

## Track A — Fast verification (no experiments)

**Goal:** confirm the package installs, imports, and core tests pass.

```bash
python -c "import consistency_ranker, numpy, pandas, scipy; print('imports OK')"
python scripts/run_synthetic.py --help
python scripts/check_repo_ready.py
pytest -q tests/test_graph_and_solver.py tests/test_baseline_ranking.py
```

**Expected:** imports OK; `check_repo_ready.py` reports 0 failures (warnings OK);
graph/baseline subset tests PASS.

**Runtime:** typically under 1–2 minutes after install.

## Track B — Small deterministic example (local, no API)

```bash
python scripts/run_synthetic.py --n-items 10 --noise 0.2 --seed 42 \
  --output-dir /tmp/sncs_synthetic_smoke --overwrite-existing
```

**Expected:** writes `/tmp/sncs_synthetic_smoke/synthetic_results.json`; prints
method comparison table. This is a pipeline smoke test, **not** a manuscript table.

**Runtime:** seconds.

## Track C — Table/figure verification from canonical stored results (local)

**Goal:** reproduce headline manuscript numbers from committed artifacts without
re-running the full calibration study.

```bash
python - <<'PY'
import pandas as pd
from pathlib import Path
root = Path('reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables')
struct = pd.read_csv(root / 'table_primary_graph_structure.csv')
boot = pd.read_csv(root / 'table_primary_bootstrap_permutation.csv')
exact = pd.read_csv('reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv')
assert len(struct) == 12
assert len(boot) == 60
assert len(exact) == 1025
print('canonical row counts OK', len(struct), len(boot), len(exact))
PY
```

Optional figure regeneration from stored exact-repair CSV (writes under
`papers/SNCS_2026/figures/`; prefer copying output elsewhere if you must not
dirty the tree):

```bash
python papers/SNCS_2026/figures/generate_f5_exact_vs_greedy_gap.py
```

**Expected outputs / paths:**

| Artifact | Path | Practical check |
|---|---|---|
| Structural table | `.../table_primary_graph_structure.csv` | 12 rows |
| Bootstrap/Holm table | `.../table_primary_bootstrap_permutation.csv` | 60 rows |
| Exact structural per-query | `.../structural_per_query.csv` | 1,025 rows |
| Manuscript figures | `papers/SNCS_2026/figures/f1_*.pdf` … `f5_*.pdf` | present vector PDFs |

**Runtime:** seconds to low minutes.

## Track D — Solver-enabled reproduction (local, no API)

```bash
python -m pip install -e ".[dev,exact]"
python -c "import pyscipopt; print(pyscipopt.__version__)"  # expect 6.2.x in this environment
pytest -q tests/test_exact_mwfas_scip.py
# optional broader mirror of CI solver job:
python scripts/run_cloud_validation.py --tier solver
```

**Expected:** SCIP import works; exact MWFAS tests PASS. Manuscript claim
“1,025/1,025 proven optimal” is evidenced by the stored exact-repair report,
not by re-solving all queries in this quickstart.

**Runtime:** subset tests: minutes; full solver cloud-validation tier: longer
(use tmux for multi-hour jobs — see `docs/AGENT_GUIDE.md`).

## Track E — Full classical regeneration (expensive; optional)

Only if you intend to regenerate Layer-1/2/3 evidence. These commands can
overwrite report outputs and, for Layer 1, regenerate figures.

```bash
# Layer 1 — WARNING: regenerates figures_v2 and large report outputs
cd reports/full_calibrated_core/scripts && python3 run_full_calibrated_core.py

# Layer 2
cd reports/normalization_protocol_audit_20260714/scripts
python3 run_independent_protocols.py
python3 analyze_protocol_robustness.py

# Layer 3
cd reports/candidate_pool_conditional_audit_20260714/scripts
python3 run_pool_robustness.py
python3 run_conditional_and_failure_analysis.py
python3 run_baseline_comparison.py
```

See `docs/REPRODUCTION_CANONICAL.md` for the full table-to-command map.
**Approximate runtime:** Layers 2–3 are relatively short on stored inputs;
Layer 1 is the expensive primary study regeneration.

## Track F — API-dependent pilot reproduction (restricted)

The six-query real-LLM pilot is **not** the primary study. Public verification
should use:

- `reports/real_llm_clustered_reanalysis_20260730T023745Z/`
- compact summaries under `reports/multi_provider_repair_pilot_20260729T032348Z/`

Do **not** expect raw provider transcripts in Git. Re-calling providers:

- requires explicit scoped authorization and credentials;
- will not byte-reproduce historical judgments;
- is outside this quickstart.

## Manuscript compilation (source ZIP)

```bash
mkdir -p /tmp/sncs_src && cd /tmp/sncs_src
unzip /path/to/repo/papers/SNCS_2026/submission/SNCS_2026_latex_source.zip
mkdir build && cp manuscript/* figures/*.pdf template/sn-jnl.cls template/bst/sn-basic.bst build/
# adjust \graphicspath to {./} if compiling from the flat build/ directory
# then: tectonic -X compile main.tex   OR   pdflatex/bibtex cycle
```

**Expected:** 39-page PDF. Hash may differ from the committed `main.pdf` due to
engine timestamps; page count and content should match.

## Primary vs pilot (do not conflate)

| Study | Role | Independent unit | API? |
|---|---|---|---|
| Classical multi-ranker fusion on four benchmarks | **Primary** manuscript evidence | Queries under fixed lists / protocols | No |
| Exact SCIP vs greedy repair | Methodological control on same classical graphs | Queries in exact-repair report | No |
| Six-query multi-provider LLM pilot | Directional addendum only | **n = 6** query clusters | Yes (historical); raw payloads excluded |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pyscipopt` import fails | `[exact]` not installed or SCIP build issue | `pip install -e ".[dev,exact]"`; see PySCIPOpt docs |
| `check_repo_ready.py` warns on `ir-datasets` | Optional IR export extra missing | Install `consistency-ranker[ir]` only if needed |
| Synthetic script refuses to write | Output dir exists | Pass `--overwrite-existing` or a fresh `--output-dir` |
| Cannot find manuscript numbers in `outputs/pub_vote_cmp_*` | Historical package | Use `reports/full_calibrated_core/.../paper_package/tables/` |
| Provider re-run diverges | Non-determinism / model drift | Use stored compact pilot artifacts; do not treat re-query as audit truth |
| GitHub Actions red | Account billing block, not code | Use `scripts/run_cloud_validation.py` |

## Related documents

- `SUBMISSION_FREEZE.md` — exact hashes and commit
- `RELEASE_CANDIDATE_SMOKE_TEST.md` — what was actually run in this environment
- `docs/CONTRIBUTIONS.md` — canonical vs non-canonical classification
- `docs/REPRODUCTION_CANONICAL.md` — detailed classical command map
