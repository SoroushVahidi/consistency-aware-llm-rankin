# Reviewer-Concerns Program Artifacts

Status: exploratory support for the real-LLM pilot interpretation.

Tracked files preserve compact branch/stage summaries, final reports, feature
rows, checkpoints, and provider usage/failure ledgers. Raw provider
request/response transcripts under `raw_calls/`, parsed cache trees under
`cache/`, smoke raw calls/caches, and transient logs are intentionally excluded
from Git by narrow `.gitignore` rules.

This program used the same provider model families recorded by
`reports/multi_provider_repair_pilot_20260729T032348Z/PROVIDER_MODELS.json`.
Regeneration from scratch requires paid/provider API calls and explicit user
authorization with a scoped call ceiling.
