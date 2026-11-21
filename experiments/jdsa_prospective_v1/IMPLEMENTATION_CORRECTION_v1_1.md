# Implementation correction v1.1 — interpreter identity, no scientific change

The first validation-only launch failed before model loading or any inference:
the shell launcher used `realpath` on a virtual-environment Python executable,
resolving its symlink to system Python. Preparation likewise used
`Path.resolve()` for the analysis interpreter. Both lost the virtual environment.

The correction preserves the absolute executable's symlink identity. One
regression checks analysis-interpreter handling; another executes the actual
launcher against a temporary symlinked test interpreter. No model is invoked
by those tests. Original run/launch/failure receipts and the empty checkpoint
are preserved. Its frozen manifest cannot be reused after the code correction;
prepare a new run and bind it to the corrected implementation commit.

PROTOCOL.md, prompt strings, parser, model revision, sampling seed/membership,
candidate rules, metrics, gate thresholds, and budgets are unchanged. Verify
identical development/evaluation pool bytes between the failed preparation
and corrected preparation. No response or retrieval outcome was available to
tune the correction. The first runtime failure is not an instrument gate
failure or an observed scientific result.
