# Reproducibility Status (as of this stage)

Precise, per-category statement of what is and is not reproducible from a fresh clone, per `docs/ARTIFACT_POLICY.md`'s own framing. No claim below is made without having been checked this session.

## Fully reproducible from a fresh clone (code + tracked data only)

| Study | Verified how |
|---|---|
| Classical backbone (CB-01 through CB-05: construction, structure, repair effects, macro comparison, normalization taxonomy, candidate-pool/conditional robustness) | All source tables are already tracked in Git; not independently re-run this stage (out of scope), but no untracked dependency was found for these. |
| Larger-pool study (CB-06) and exact-baseline-fairness study (CB-08) | **Fixed this stage.** Previously blocked by a blanket `.gitignore` rule. Re-ran `scripts/run_ir_evidence_audit.py` after adding the surgical carve-out and diffed all four output CSVs against the already-committed report: byte-identical, twice (once right after `git add`, once again in final validation). |
| Exact repair vs. greedy (CB-07) | Source tables already tracked (4.2MB). Requires SCIP/PySCIPOpt installed to regenerate from raw score files, but the tracked per-query tables themselves need no external dependency to read. |
| Final IR evidence audit (AUD-01) | Directly re-run twice this session end-to-end; produces byte-identical output to the committed report both times. |
| Meta-audit (AUD-02) | Narrative document; every numeric claim it makes was independently re-derived from tracked source files this session and matched. |

## NOT reproducible from a fresh clone, and why (documented, not silently claimed otherwise)

| What | Why not | Is this a defect or intentional? |
|---|---|---|
| Real-LLM raw provider transcripts (`reports/multi_provider_repair_pilot_20260729T032348Z/raw_calls/*.jsonl`, `reports/reviewer_concerns_program_20260729T035320Z/raw_calls/*.jsonl`) | Require live Azure/Gemini/Cohere/Fireworks API credentials and cost real money per call; correctly excluded from Git per `docs/ARTIFACT_POLICY.md`'s explicit "do not track... raw API transcripts" rule | **Intentional**, not a defect. These are external, private-credential-gated data sources, exactly the kind of limit the brief asked to be documented precisely rather than glossed over. |
| Repair-frontier / extraction / repair-diagnostic studies' *original data collection* step (LLM-03/04/05) | Same as above — the analysis scripts (`run_repair_frontier_pilot.py` etc.) are deterministic and reproducible **given** the already-collected upstream JSONLs, but those JSONLs cannot be regenerated without live API access | **Intentional** for the raw calls; the analysis layer on top of them IS reproducible (verified: the already-collected `extraction_results.jsonl`/`diagnostic_results.jsonl`/`frontier_results.jsonl` are present and were read directly by the audit script this session) |
| Raw BEIR/BRIGHT/HotpotQA datasets under `data/raw/`, `data/processed/` | Mostly gitignored per policy; require `scripts/download_beir_via_irds.py` / `scripts/prepare_hotpotqa.py` and network access to HuggingFace Hub | **Intentional**, standard practice for large third-party datasets; `docs/DATASET_ACCESS_DIAGNOSIS.md` documents known access issues (some sandboxes block `huggingface.co`) |
| `docs/REPRODUCTION_CANONICAL.md`'s own pipeline map | Only documents Layers 1-3 (the pre-2026-07-15 evidence); does not yet mention the larger-pool, exact-baseline-fairness, exact-ILP, or repository-scale-headroom families that `scripts/run_ir_evidence_audit.py` also depends on | **Defect (documentation gap)**, not a data-reproducibility defect — the underlying tables ARE reproducible/tracked, the guide just doesn't mention them yet. Listed in `deferred_cleanup_items.csv`. |
| SCIP/PySCIPOpt solver version | Not pinned in `requirements.txt`; `docs/REPRODUCTION_CANONICAL.md` narratively lists `pyscipopt 6.2.1` as "the reference version used" but this isn't machine-enforced | **Defect (minor)** — listed in `deferred_cleanup_items.csv` |

## Explicit "do not claim more than this" statement

This stage does **not** claim full fresh-clone reproducibility of the repository as a whole. It claims, specifically and only: (1) `scripts/run_ir_evidence_audit.py` and every table it reads are now reproducible from a fresh clone, verified by direct re-run; (2) the real-LLM raw data collection step is not reproducible without external API credentials, by design, and this is now stated explicitly in `README.md`/`docs/READ_ME_FIRST_FOR_AI.md` rather than left implicit; (3) raw third-party benchmark datasets require external network access, as is standard and already partially documented in `docs/DATASET_ACCESS_DIAGNOSIS.md`.

## What was NOT attempted (explicitly out of scope for this stage)

- The pending query-clustered re-analysis (see `canonical_evidence_inventory.csv` row `IR-PENDING-01`) — a statistics task.
- A real LaTeX compile of `main.tex` — no manuscript content was touched this stage at all (see the main report's confirmation), so this is doubly out of scope here.
- Extending `docs/REPRODUCTION_CANONICAL.md` to cover the 2026-07-15 evidence families — listed as deferred, not done.
