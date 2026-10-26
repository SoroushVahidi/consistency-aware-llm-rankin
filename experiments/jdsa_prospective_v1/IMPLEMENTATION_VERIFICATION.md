# Implementation verification before prospective inference

Classification: engineering verification, not prospective outcome evidence.
Base manuscript commit: `2c69f331fa4add10ce577c17516afb997b630dfe`.
The manuscript and all historical scientific outputs are unchanged.

Verified before any new model responses:

- Default repository suite: **1362 passed, 64 deselected**, 37.59 seconds.
- New offline prospective tests: **30 passed**, including parser boundaries,
  always-A rejection, abstention/repeat/paraphrase failure, gate-before-main,
  missing-versus-zero semantics, unique swapped requests, immutable SQLite
  records, independent tiny exact enumeration, and fixed two-test inference.
- Combined relevant suite: **152 passed** (baseline rankings, SCIP, statistics,
  graph/solver and new prospective tests).
- Ruff on the experiment package: passed after formatting.
- Shell syntax: passed.
- Active portability: passed.
- Secret scan: **2956 files scanned, zero findings**.
- Claim/evidence registry: **12 claims validated, zero problems**. No new
  scientific claim is inserted merely because an experiment is prepared.

Commands from the isolated worktree (use the configured analysis interpreter):

```bash
PYTHONPATH=src "$ANALYSIS_PYTHON" -m pytest -q
PYTHONPATH=src "$ANALYSIS_PYTHON" -m pytest -q \
  experiments/jdsa_prospective_v1/test_prospective.py
PYTHONPATH=src "$ANALYSIS_PYTHON" -m pytest -q \
  tests/test_baseline_ranking.py tests/test_exact_mwfas_scip.py \
  tests/test_statistical_inference.py tests/test_graph_and_solver.py \
  experiments/jdsa_prospective_v1/test_prospective.py
ruff check experiments/jdsa_prospective_v1
bash -n experiments/jdsa_prospective_v1/launch.sh
PYTHONPATH=src "$ANALYSIS_PYTHON" scripts/check_active_portability.py
PYTHONPATH=src "$ANALYSIS_PYTHON" scripts/run_secret_scan.py
PYTHONPATH=src "$ANALYSIS_PYTHON" scripts/validate_claim_evidence_registry.py
```

These offline checks do not establish the LLM instrument's validity. Only the
separately recorded, predeclared development gate can permit main collection.
Actual gate, runtime, manifest, checkpoint, launch and health receipts live in
the private run directory and are not published with this implementation.

Identity extraction uses the preserved historical exclusion manifest plus
dataset/query projections of the offline campaign's metrics CSV; that CSV
contains the original identities for the selected-cache numeric projection.
Its outcome columns are not used for sampling. Frozen previous prospective and
candidate-intervention rosters are excluded as well. The anonymized numeric
projection alone cannot supply original query IDs.

Both queried candidate conditions share exact pair responses only for matching
query/document/prompt/model inputs. This reduces calls without turning pools
or branches into independent units. Official BRIGHT excluded documents are
masked before candidate selection. The source Arrow cache revisions, split
identities, source bytes, and every selected query/pool are verified and frozen
privately by preparation; this file is not a claim that preparation has run.
