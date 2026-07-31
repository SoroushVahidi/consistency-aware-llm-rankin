# Branch Handoff: fix/outcome-f-production-operating-point

*Branch-specific companion to `PROJECT_STATUS.md`. Read that first for the
repository-wide picture; this document is scoped to this branch's history
and exact continuation point.*

## Branch purpose

Originally: enforce the Outcome F interim production operating point
(always-UHT + non-routing safety floor) and correct an invalid
`production_uht` evaluation. The branch then extended into building and
canary-testing a real, qrels-grounded, multi-provider counterfactual
LLM-judge benchmark. **As of `756495d` the branch pivoted** to a
consistency-aware active-acquisition / regularized-aggregation /
stopping-rule research line built on one real, pre-existing SciDocs
oracle — this is the branch's active focus as of this handoff; the
counterfactual-benchmark work is paused, not abandoned (see
`PROJECT_STATUS.md`'s "Consistency-aware pivot" section for the scientific
summary).

## Base and divergence

- Diverged from `origin/main` at `3e02b73666506f3eb894f5df2c531284ea31a60e`
  ("Update JDIQ title page with verified support and acknowledgments").
- `documented_code_head` (the code state this handoff describes, **not**
  a promise about the current branch tip — this documentation commit
  itself lands after it): `cd678f02cec725496c484757146d44649ac0d034`.
- 28 commits ahead of `origin/main`, 0 behind, as of `documented_code_head`.

## Commit-by-commit development timeline

In chronological order (`git log --reverse --format='%H%x09%s' origin/main..HEAD`):

1. **`3614333` — Enforce Outcome F production operating point.**
   Freezes `policy_selection/production_config.py`: the only policy
   production may execute is UHT, with a non-routing safety floor
   (mandatory outsider probe, prohibited weak-evidence stop, final
   adversarial challenger). Codifies the Outcome F decision.

2. **`51fec89` — Add Outcome F audit and reviewer concern gap reports.**
   Adds audit/gap-report documentation for the Outcome F synthetic package
   (`reports/policy_selection_20260726T030500Z/`).

3. **`19d8304` — Add offline real-query repair and policy-utility replay.**
   Adds cache-only, zero-new-paid-call offline replay infrastructure for
   real-query graph repair and policy-utility comparison.

4. **`65b1427` — Record scientific replay commit hash in FINAL_REPORT.**
   Provenance polish: records the commit hash a scientific replay was run
   against.

5. **`74a8f90` — Fix scientific replay commit hash in FINAL_REPORT provenance.**
   Corrective fix to (4) — the recorded hash was wrong; this is a genuine
   corrective commit, not filler.

6. **`89b9406` — Repair Azure multifactor acquisition path for safe resume.**
   Fixes an Azure-specific resume/safety defect in the multifactor
   acquisition path.

7. **`5465ea6` — Polish Outcome F provenance and track canonical evidence.**
   Finalizes tracking of the canonical Outcome F evidence package and
   provenance notes (`reports/policy_selection_20260726T030500Z/README.md`).

8. **`923ee35` — fix: evaluate multifactor production UHT against qrels.**
   **Major corrective commit.** The prior `production_uht` evaluation
   scored against its own prior ranking (Jaccard `≡ 1.0`, uninformative)
   instead of qrels-based retrieval metrics. This commit adds the corrected
   qrels-based evaluation path. See
   `docs/MULTIFACTOR_PRODUCTION_UHT_EVAL_INVALIDATION.md`.

9. **`d158a04` — chore: organize experimental drivers and offline execution.**
   Organizes the Outcome B-D driver scripts (adaptive acquisition,
   prior-robust, reliability-aware repair, linear-extension extraction,
   multi-provider LLM robustness) into canonical `scripts/` entry points.
   See `docs/experiments/OUTCOME_BCD_DRIVERS.md`.

10. **`07b4ba2` — feat: add bounded provider audit and counterfactual benchmark spec.**
    Adds `provider_capability/` (bounded, ledger-capped live audit engine)
    and `docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md` (design
    only, not executed at commit time).

11. **`32d39a9` — feat: freeze multi-provider counterfactual micro-pilot.**
    Freezes `counterfactual_micro_pilot_v1`: prompt, judgment schema,
    provider panel v1, `lexical_prior_pool_v1` pool protocol,
    `title_plus_prefix_truncate_v1` rendering policy. Adds
    `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md`. Status at this
    commit: frozen design, not executed.

12. **`fb74974` — feat: add fail-closed counterfactual micro-pilot collector.**
    Adds the actual collector implementation
    (`counterfactual_benchmark/{collector,dispatch,request_plan,reserve,
    cache_store,evaluation}.py`) and the canary-v1 config. **Canary-v1 was
    then run against this commit** (locally; the report directory is
    untracked evidence, not a separate commit) — it surfaced two defects:
    a content-poor (title-only) candidate pool for one frozen SciDocs
    query, and a Vertex AI/Gemini fenced-JSON parse failure.

13. **`3a47e90` — fix: harden counterfactual pool quality and provider
    normalization.** Diagnoses and fixes both canary-v1
    defects: adds `lexical_prior_pool_v2` (bounded-denominator prior) +
    `document_validity_v2` (pre-scoring eligibility gate), eliminating the
    measured title-only bias (17/80 → 0/80 candidates, 16/64 → 0/64 pairs
    across the 8 frozen queries); adds `extract_json_payload` to correctly
    unwrap Vertex AI's fenced-JSON wrapper without weakening strict
    validation; adds cross-version guards (`config.verify_frozen_contract`
    refuses any config that combines a `benchmark_version` with the wrong
    `pool_protocol_version`); adds `counterfactual_micro_pilot_v2` /
    `counterfactual_collector_canary_v2` configs. **Canary-v2 was then run
    against this commit** (local evidence) — 3/4 providers (Azure,
    Fireworks, Vertex AI/Gemini) normalized correctly; Cohere returned
    syntactically valid JSON with `evidence_strength: "unsupported"`
    (a `reason_code` value leaked into the wrong field), correctly rejected
    by strict local validation.
14. **`ab4e064` — docs: add repository status and branch handoff.** Adds
    `PROJECT_STATUS.md`, this handoff document, and
    `docs/handoff/state_snapshot.json`; documentation only, no
    source/config/test changes.

15. **`b22bd55` — feat: add native Cohere transport and schema projection.**
    Adds `cohere_native.py` (Chat API v2 `ClientV2` transport) and
    `cohere_schema_projection.py` (schema-projection versions v1-v3), a
    genuinely different wire protocol from the archived compatibility-API
    shim. Offline-tested (28 tests); one live confirmation call at this
    commit was rejected 400 (root cause unestablished at the time).

16. **`aff9025` — docs: reconcile repository status and evidence authority.**
    Reconciles `PROJECT_STATUS.md` and several `docs/*` files after the
    native-Cohere work; renames the stale JDIQ-paper status doc to
    `PROJECT_STATUS_SUPERSEDED_20260712.md` to remove an authority
    ambiguity.

17. **`e8f6006` — chore: classify provider diagnostic and canary artifacts.**
    Tracks 8 previously-untracked, individually-inspected (no secrets, no
    raw provider transcripts) diagnostic/canary report directories from the
    Cohere investigation and the two counterfactual-collector canaries, per
    `docs/ARTIFACT_POLICY.md`'s classification criteria.

18. **`8e70029` — chore: polish branch-local code and tests.** Ruff-only
    cleanup scoped to branch-changed files only (not a repo-wide fix of
    pre-existing, unrelated Ruff debt elsewhere).

19. **`756495d` — feat: add offline active-acquisition pilot
    (consistency-aware pivot).** **Branch pivot point.** Adds
    `active_acquisition/{oracle,scoring,strategies,simulate,evaluate,
    stats}.py` and the pilot CLI, evaluating an active pair-selection
    proposal against a real, pre-existing SciDocs q50/k15 oracle
    (`outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl`, no
    live calls). **Result: negative** — the proposed strategy loses to
    random unrevealed-pair selection at 10%/20% budget, Holm-corrected.
    24 tests.

20. **`e4566aa` — docs: freeze offline active-acquisition pilot v1 config.**
    Freezes `configs/offline_active_acquisition_pilot_v1.json`.

21. **`91b8973` — feat: add prior-regularized pairwise rank aggregation
    (safe anytime reranking).** Adds `regularized_aggregation.py` (a
    regularized Bradley-Terry aggregator that reduces exactly to the BM25
    prior at zero pairwise evidence) plus a 1-line determinism fix in
    `oracle.py`'s `bm25_scores` (`set()` iteration order was hash-seed-
    dependent; changed to `sorted(set())` — floating-point summation order
    only, no semantic change). **Result: safety-dominant** — significantly
    reduces severe-harm rate vs. naive sparse Copeland aggregation at
    5%/10% budget and beats BM25 significantly at 10%/20%, but does not
    establish raw mean-nDCG/AUC superiority over the strongest non-oracle
    baseline (disclosed, not overstated). 21 tests.

22. **`c568b87` — docs: freeze regularized aggregation pilot v1 config.**
    Freezes `configs/regularized_aggregation_pilot_v1.json`.

23. **`fc866d7` — feat: add risk-controlled qrel-free stopping rule for
    regularized aggregation.** Adds `stopping.py` (counterfactual
    worst-case top-k-change statistic, both-outcome evaluated, never reads
    qrels/oracle/exhaustive ranking — enforced by a signature test and a
    behavioral flipped-oracle test) and the `simulate`/`analyze`/
    `mechanism` pilot CLI. Calibrated (`tau=0.20, m=3`) on a 15-query dev
    split, evaluated on the 35-query held-out test split shared with the
    prior pilot. 21 tests.

24. **`b007a13` — docs: freeze stopping rule pilot v1 config.** Freezes
    `configs/stopping_rule_pilot_v1.json`. This was the branch tip audited
    by an independent branch audit; commits 25-28 below are the resulting
    post-audit polish pass.

25. **`a3bc58c` — fix(stats): add centralized Wilson/Clopper-Pearson
    proportion interval.** Adds `proportion_interval()` to
    `statistical_inference.py` (Wilson by default) as a reusable
    replacement for using a nonparametric bootstrap on a 0/1 indicator to
    estimate a rate -- a bootstrap of an all-zero/all-one sample is
    degenerate and collapses to a zero-width interval. 12 new tests.

26. **`7c7bbfd` — fix(stopping): use valid severe-harm CI; expose
    stopped/capped/failed run counts.** Wires `proportion_interval` into
    the stopping pilot's `severe_harm`/`premature_stop` rates (was
    `bootstrap_mean_interval`, which had reported the observed 0/35
    severe-harm rate as a degenerate `[0.0%, 0.0%]`, corrected to
    `[0.0%, 9.9%]`); adds an explicit `run_status`
    (stopped/capped/failed) section to `statistical_analysis.json`
    (`schema_version: 2`); adds a completeness assertion to `analyze`
    mode. `analyze`/`mechanism` outputs regenerated offline from the
    unchanged cached simulation data (byte-identical `stopping_results.csv`
    /mechanism outputs; `primary_comparisons` unchanged). Tracks this
    pilot's report directory in Git (minus one regenerable raw log). 7 new
    tests.

27. **`9dcc80e` — fix(regularized-aggregation): add Wilson CI to
    per-method severe-harm rates.** Adds a CI to a rate that previously
    had none (not a correction of a prior bug). `evaluation/` outputs
    regenerated offline; `primary_comparisons` byte-identical. Tracks this
    pilot's report directory in Git in full. 4 new tests.

28. **`cd678f0` — chore: track offline active-acquisition report; update
    artifact policy.** (Current `documented_code_head`.) Completes
    tracking the third pilot's report directory (no code/numbers changed
    in it); updates `docs/ARTIFACT_POLICY.md`'s per-path table for all
    three pilots.

None of these commits change the mature preference-graph program's
algorithms, and none change production defaults except the intentional,
documented Outcome F fail-closed change in commit 1.

## Current Git state

Reconfirm before trusting this section — it is a point-in-time snapshot:

```bash
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count origin/main...HEAD
```

Expected `documented_code_head`: `cd678f02cec725496c484757146d44649ac0d034`,
28 ahead / 0 behind, branch `fix/outcome-f-production-operating-point`. This
number will move again once the in-progress post-pivot polish pass (Wilson
proportion intervals, explicit capped-run counts, this documentation update)
lands as new commits — re-run the commands above rather than trusting this
number; see "Last verified state" in `PROJECT_STATUS.md` for the most
recent re-verification.

## Staged or uncommitted work

As of `documented_code_head` (`cd678f0`), the working tree is clean on all
tracked files, and this documentation commit is the only pending change.
The post-audit polish pass (commits 25-28, §"Commit-by-commit development
timeline") tracked all three consistency-aware-pivot report directories
per `docs/ARTIFACT_POLICY.md`'s updated classification (each in full
except one deterministically-regenerable raw per-step log, kept local via
a narrow `.gitignore` rule):
- `reports/offline_active_acquisition_pilot_20260728T142414Z/` (tracked
  minus `raw_trajectories.jsonl`)
- `reports/regularized_aggregation_pilot_20260728T164943Z/` (tracked in
  full)
- `reports/stopping_rule_pilot_20260728T190000Z/` (tracked minus
  `simulate/raw_stopping_histories.jsonl`)

These were untracked, local-only as of the earlier `documented_code_head`
(`b007a13`, the state audited before this polish pass) — see
`PROJECT_STATUS.md`'s "Evidence and artifact registry" for the current
disposition.

Separately, and unrelated to the above: the earlier Cohere
schema-constrained structured-output *compatibility-path* attempt (7
files; implemented and tested offline, but whose live confirmation call
failed) remains moved off this branch entirely, on the local archive
branch `archive/cohere-compat-schema-failed-20260727` at commit
`0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2`
(`chore: archive unsuccessful Cohere schema enforcement attempt`) — it is
not part of this branch's history and must not be presented as a working
fix.

**Do not merge or cherry-pick that archive commit onto this branch as a
"fix"** — it did not resolve the Cohere blocker; it is retained for
diagnosis and comparison only.

**Note on the 8 Cohere/canary diagnostic directories** listed as
"untracked" in an earlier version of this document: they were tracked in
commit `e8f6006` ("chore: classify provider diagnostic and canary
artifacts") and are committed evidence as of `documented_code_head` — see
"Local-only reports and diagnostics" below, which has been corrected to
match.

## Safety branches

Local-only (not pushed), one per major checkpoint on this branch:

```
backup/pre-final-branch-polish-20260728-174708            (points at b007a13, this polish pass)
backup/pre-risk-controlled-stopping-pilot-20260728-182920 (points at c568b87)
backup/pre-regularized-aggregation-pilot-20260728-163011  (points at e4566aa)
backup/pre-active-acquisition-pilot-20260728-141641       (points at 8e70029)
backup/pre-cleanup-polish-20260728-030421                 (points at ab4e064)
backup/pre-native-cohere-clientv2-20260727                (points at ab4e064)
backup/pre-cohere-schema-projection-20260727              (points at ab4e064)
backup/pre-cohere-schema-enforcement-20260727             (points at 3a47e90)
backup/pre-cohere-normalization-diagnostic-20260727       (points at 3a47e90)
backup/pre-counterfactual-canary-v2-20260727              (points at fb74974)
backup/pre-counterfactual-canary-20260727                 (points at fb74974)
backup/pre-counterfactual-collector-20260727              (points at 32d39a9)
backup/pre-counterfactual-pilot-freeze-20260727           (points at 07b4ba2)
backup/pre-provider-capability-audit-20260727             (points at d158a04)
backup/pre-driver-organization-20260727                   (points at 923ee35)
backup/pre-multifactor-eval-fix-20260726                  (points at 5465ea6)
backup/pre-polish-outcome-f-20260726                      (points at 89b9406)
```

None of these are pushed to `origin`; they exist only on this local
machine, same as the branch itself.

Plus one local-only **archive** branch (distinct in purpose from the
`backup/*` checkpoints above — this one holds a real, extra commit, not
just a pointer):

```
archive/cohere-compat-schema-failed-20260727  (0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2,
                                                one commit ahead of 3a47e90)
```

## Major completed milestones

1. Outcome F synthetic evidence frozen and canonicalized; production
   defaults locked to always-UHT.
2. Multifactor `production_uht` evaluation corrected from an invalid
   prior-based metric to qrels-based retrieval metrics.
3. Provider capability audit: 4/4 providers live-authenticated.
4. Counterfactual benchmark v1 frozen (prompt/schema/panel/pool/rendering)
   and collector implemented, fail-closed.
5. Canary-v1 run, diagnosed (content-poor pool + Vertex parse failure), and
   fixed via v2 pool protocol + fenced-JSON extraction — independently
   re-verified in a separate review pass this session.
6. Canary-v2 run: 3/4 providers pass; Cohere failure discovered and
   documented (not yet resolved).
7. Two bounded, evidence-gathering live Cohere calls made this session
   (json_object-only, then full-schema); both reproduced byte-identical
   malformed output. Cohere marked unsupported for the frozen panel under
   its current access path.
8. The failed schema-enforcement attempt was archived to
   `archive/cohere-compat-schema-failed-20260727` (`0646fde8...`) and
   cleanly removed from this branch, so this branch's working tree carries
   no unresolved, half-working provider code.
9. **Branch pivot** (`756495d` onward): offline active-acquisition pilot
   run against a real, pre-existing SciDocs q50/k15 oracle — negative
   result (proposed strategy loses to random at 10%/20% budget).
10. Prior-regularized Bradley-Terry aggregation (`91b8973`) — safety-
    dominant result (significant severe-harm reduction vs. sparse
    Copeland, significant nDCG win over BM25; not established as beating
    the strongest baseline on raw mean nDCG/AUC, disclosed as such).
11. Risk-controlled qrel-free stopping rule (`fc866d7`) built on the
    regularized aggregator — qrel-freedom verified both structurally and
    behaviorally; capped-vs-stopped bookkeeping verified; does not meet
    its own near-exhaustive quality-recovery bar (aggregator property, not
    a stopping-rule defect).
12. Post-pivot polish pass (this handoff update): corrected a degenerate
    bootstrap confidence interval for a 0/35 severe-harm rate to a valid
    Wilson interval, and added explicit machine-readable stopped/capped/
    failed run counts to the stopping pilot's `statistical_analysis.json`
    — both point estimates and all prior scientific conclusions are
    unchanged; only the interval validity and the granularity of reporting
    improved. See `PROJECT_STATUS.md`'s "Consistency-aware pivot" section.

## Current scientific interpretation

**Note: the interpretation below describes the paused counterfactual-
benchmark thread, not the branch's current active focus.** See
`PROJECT_STATUS.md`'s "Consistency-aware pivot" section for the current
focus's own scientific interpretation.

The counterfactual-benchmark engineering is solid and independently
verified (pool audit statistics reproduced exactly from raw data; hash
determinism confirmed; resume-without-live-calls confirmed byte-identical
except cache flags; Gemini/Vertex fix narrowly scoped and regression-tested).
The **open scientific/engineering question** is not about this repository's
code — it is about Cohere's compatibility-layer behavior for
`command-r-plus-08-2024`, which appears not to honor `response_format` at
all for this model on this endpoint. This is now well-evidenced (2
independent live calls, byte-identical output regardless of the
`response_format` value sent) but not yet root-caused beyond that.

## Current benchmark state

- Frozen panel `counterfactual_provider_panel_v1` cannot currently pass a
  clean 4-provider canary.
- No benchmark-scale run (the 256-384 call micro-pilot) has ever executed.
- `configs/counterfactual_micro_pilot_v2.json` has `execute_in_this_task:
  false` — this must remain false until the panel question above is
  resolved and a fresh, clean canary passes under whatever panel is frozen
  next.

## Provider-specific status

| Provider | Status | Evidence |
|---|---|---|
| Azure (`gpt-4.1-mini`) | Reliable, normalizes correctly | Canary v1 + v2 |
| Fireworks (`gpt-oss-120b`) | Reliable, normalizes correctly | Canary v1 + v2 |
| Vertex AI (`gemini-2.5-flash`) | Reliable after fenced-JSON fix | Canary v1 (failed) → v2 (fixed, confirmed) |
| Cohere (`command-r-plus-08-2024`) | **Schema/transport confirmed working**, not yet wired into the collector — compat path: schema not honored (archived); native `ClientV2` path (protocol v3): **4th confirmation SUCCEEDED** after 3 rejections (400), each on a different field | Canary v1/v2, 2 compat-path diagnostic/confirmation calls (archived, `0646fde8...`), 4 native-path confirmation calls (`d6ba44eb...` unprojected, `41f1de66...` v1-projection, `be312ecf...` v2-projection — all rejected; `f062ea28...` v3-projection — **succeeded**) |

## Local-only reports and diagnostics

See `PROJECT_STATUS.md`'s "Evidence and artifact registry" for the full,
current classification. **Correction to an earlier version of this
document:** the 8 counterfactual/Cohere canary and diagnostic report
directories (both canaries plus 6 Cohere confirmation/diagnostic
directories, including `reports/cohere_native_v2_confirmation_20260727T210000Z/`,
the three `cohere_native_v2_schema_projection*_confirmation_*` directories,
and `reports/cohere_normalization_diagnostic_20260727T183000Z/` /
`reports/cohere_json_schema_confirmation_20260727T200000Z/`) are **tracked
in Git as of commit `e8f6006`**, not local-only/untracked — each was
individually inspected for secrets and raw provider transcripts (none
found) before being committed; see that commit's message and
`docs/ARTIFACT_POLICY.md` for the per-directory classification. They
remain explicitly labeled canary/diagnostic-only in their own status
fields regardless of being tracked — none constitute benchmark data, and
none should be merged into `counterfactual_micro_pilot_v2` benchmark data.

Separately, and genuinely local-only as of `documented_code_head`: the
three consistency-aware-pivot pilot report directories (see "Staged or
uncommitted work" above), whose tracking disposition is being finalized in
the polish pass this document is part of.

## Known defects and limitations

- Cohere's OpenAI-compatibility endpoint does not appear to honor
  `response_format` for `command-r-plus-08-2024` — root cause beyond "the
  compat layer likely ignores or mistranslates the parameter" is not
  established (would require Cohere-side investigation or their support).
  This is now moot: the native `ClientV2` path works and is the intended
  access path going forward.
- The native `ClientV2` transport is confirmed to work for a single
  request (schema accepted, valid judgment generated and locally
  validated), but it is **not yet wired into `dispatch.call_provider`/the
  frozen collector** — a deliberate, reviewed implementation task with
  several open design questions (see "Native Cohere collector-wiring
  plan" in the freeze doc), not yet started.
- The frozen `counterfactual_provider_panel_v1` panel cannot currently be
  satisfied end-to-end by all four members (blocked on the wiring above,
  not on Cohere's schema/transport anymore).
- No leave-one-dataset-out / leave-one-provider-out validation has been
  designed or run for the counterfactual benchmark.
- A single successful ABSTAIN judgment is a connectivity/schema signal
  only, not a quality signal — no claim about Cohere's judgment quality
  should be made from this one call.

## Exact next task

**For the active consistency-aware pivot:** refine the stopping rule's
worst-case statistic or the aggregator's regularization schedule to narrow
the gap to exhaustive quality at moderate budgets (the pivot's own
disclosed shortfall) — a small, separate follow-up, not a broader
acquisition-policy search (closed out as unsupported by the offline
active-acquisition pilot). See `PROJECT_STATUS.md`'s "Exact next action"
for the full framing.

**For the paused counterfactual-benchmark thread:** the native Cohere
transport (schema projection v3) is live-confirmed working. The next task
there is implementing its wiring into `dispatch.call_provider`/the frozen
collector, per the plan in `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md`
("Native Cohere collector-wiring plan") — not yet started. Only after that
is implemented and offline-tested should a clean four-provider canary be
attempted. Do not run the micro-pilot yet. See "Exact next action" at the
end of this document.

## Tasks that must not be started yet

- The 256-384 call bounded micro-pilot (`counterfactual_micro_pilot_v2`).
- Any real oracle-opportunity audit (design-only so far).
- Any provider call without an explicit, scoped, up-front authorization
  (query, pair, provider, and a stated call ceiling).
- Any change to `production_config.py` / the always-UHT default.
- Any edit to a frozen protocol artifact (prompt, schema, v1 pool protocol,
  `regularized_aggregation_pilot_v1`/`stopping_rule_pilot_v1`/
  `offline_active_acquisition_pilot_v1` configs) in place — add a new
  version instead.
- Resuming the active-acquisition proposal as-is — it is evidenced-worse
  than random on the one oracle tested; new evidence would be needed
  first.

## Validation commands

```bash
python -m pip check
python scripts/check_repo_ready.py
pytest -q
pytest -q tests/test_counterfactual_benchmark_collector.py \
          tests/test_counterfactual_benchmark_integration.py \
          tests/test_counterfactual_pilot_freeze.py \
          tests/test_provider_capability_audit.py \
          tests/test_counterfactual_cohere_native_v2.py \
          tests/test_counterfactual_cohere_schema_projection.py \
          tests/test_counterfactual_pool_v2.py \
          tests/test_counterfactual_versioning.py \
          tests/test_counterfactual_gemini_normalization.py
pytest -q tests/test_offline_active_acquisition.py \
          tests/test_regularized_aggregation.py \
          tests/test_regularized_aggregation_pilot_analysis.py \
          tests/test_stopping.py \
          tests/test_stopping_rule_pilot_analysis.py \
          tests/test_statistical_inference.py
ruff check <changed files>
python -m compileall -q src scripts
git diff --check
git diff --cached --check
```

Note: `tests/test_counterfactual_cohere_json_schema.py` (the
compatibility-path attempt's test file) does **not** exist on this
branch — it lives only on the archived
`archive/cohere-compat-schema-failed-20260727` branch. Do not add it back
here.

**No type checker (mypy or otherwise) is configured in this repository** —
no `[tool.mypy]` section in `pyproject.toml`, not a dev dependency. Any
earlier version of this document (or of a pilot's own `REPORT.md`) that
claimed a clean `mypy` run described a different environment/session's ad
hoc use of the tool, not a repository convention; do not add a `mypy`
invocation to a validation checklist without first installing and
configuring it.

Last verified during the post-pivot polish pass (see `PROJECT_STATUS.md`'s
"Current validation status" for the exact command, exit code, and
pass/fail/skip counts) — re-run rather than trusting a cached number; skip
counts are environment-dependent (exact-repair tests skip without
PySCIPOpt).

## Recovery and rollback points

- To inspect the archived (failed) Cohere schema-enforcement attempt:
  `archive/cohere-compat-schema-failed-20260727` at commit
  `0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2` — one commit ahead of
  `3a47e90`, containing exactly the 7 files listed above, unmixed with any
  documentation change.
- To inspect state before that attempt existed at all:
  `backup/pre-cohere-schema-enforcement-20260727` /
  `backup/pre-cohere-normalization-diagnostic-20260727` (both == `3a47e90`,
  i.e. this branch's current tip).
- To inspect state before the v2 pool/Gemini work: `fb74974` (tag
  `backup/pre-counterfactual-canary-v2-20260727`).
- To inspect state before the collector existed at all: `32d39a9`.
- To inspect state before the consistency-aware pivot began:
  `backup/pre-active-acquisition-pilot-20260728-141641` (== `8e70029`,
  i.e. the tip of the pre-pivot counterfactual-benchmark work).
- To inspect state before each pivot pilot:
  `backup/pre-regularized-aggregation-pilot-20260728-163011` (== `e4566aa`),
  `backup/pre-risk-controlled-stopping-pilot-20260728-182920` (== `c568b87`).
- To inspect state before this post-pivot polish pass:
  `backup/pre-final-branch-polish-20260728-174708` (== `b007a13`).
- None of these branches (including the archive branch) have been pushed;
  all rollback is local-only.

## File map for the next agent

| Concern | Path |
|---|---|
| Frozen v1 design doc | `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` |
| Benchmark spec (design only) | `docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md` |
| Artifact tracking policy | `docs/ARTIFACT_POLICY.md` |
| Collector implementation | `src/consistency_ranker/counterfactual_benchmark/` |
| Frozen prompt/schema/panel | `src/consistency_ranker/counterfactual_pilot/` |
| Frozen prompt text | `prompts/counterfactual_pairwise_judge_v1.txt` |
| Frozen judgment schema | `schemas/counterfactual_pairwise_judgment_v1.json` |
| v1/v2 configs | `configs/counterfactual_micro_pilot_v{1,2}.json`, `configs/counterfactual_collector_canary_v{1,2}.json` |
| Runner CLI | `scripts/run_counterfactual_micro_pilot.py` |
| Outcome F production default | `src/consistency_ranker/policy_selection/production_config.py` |
| Multifactor invalidation record | `docs/MULTIFACTOR_PRODUCTION_UHT_EVAL_INVALIDATION.md` |
| Outcome B-D drivers | `docs/experiments/OUTCOME_BCD_DRIVERS.md` |
| Archived Cohere schema-enforcement attempt + tests (not on this branch) | `archive/cohere-compat-schema-failed-20260727` (`0646fde8...`) |
| **Consistency-aware pivot (current focus):** oracle, scoring, strategies, aggregation, stopping | `src/consistency_ranker/active_acquisition/` |
| Shared proportion/paired-statistics helpers | `src/consistency_ranker/statistical_inference.py` |
| Pivot frozen configs | `configs/{offline_active_acquisition_pilot,regularized_aggregation_pilot,stopping_rule_pilot}_v1.json` |
| Pivot pilot CLIs | `scripts/run_{offline_active_acquisition,regularized_aggregation,stopping_rule}_pilot.py` |
| Pivot reports (headlines + provenance) | `reports/{offline_active_acquisition_pilot_20260728T142414Z,regularized_aggregation_pilot_20260728T164943Z,stopping_rule_pilot_20260728T190000Z}/` |
| Real oracle (shared, pre-existing, frozen) | `outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl` |

## Exact next action

**Consistency-aware pivot (current branch focus):** per the stopping-rule
pilot's own stop/go recommendation, the next useful increment is a
better-calibrated worst-case statistic or regularization schedule that
narrows the aggregator's gap to exhaustive quality at moderate budgets
(e.g. investigating whether the cycle/upset-fraction association found in
the stopping pilot's mechanism analysis could inform a
coverage-and-consistency-aware schedule) — a small, separate follow-up,
not a broader acquisition-policy search (closed out as unsupported). Do
not present the pivot as a complete, deployment-ready contribution yet.
See `PROJECT_STATUS.md`'s "Exact next action" for the full framing.

**Paused counterfactual-benchmark thread (not current focus, not
abandoned):** the native Cohere transport is live-confirmed working (schema projection
v3, request_hash `f062ea286398b73316c1dcbbc6a9868ab698491d47a6cd0d8041a43718d1e829`).
The next task is a deliberate, reviewed implementation to wire it into
`dispatch.call_provider`/the frozen collector — see "Native Cohere
collector-wiring plan" in the freeze doc for the open design questions
(adapter shape, request-hash/cache-identity extension, readiness-check
routing, collector-test updates). **Do not run the micro-pilot before
this wiring is implemented, offline-tested, and a clean canary passes.**
Status:

1. ✅ Compatibility-shim failure kept archived and off the active branch
   (`archive/cohere-compat-schema-failed-20260727`, `0646fde8...`).
2. ✅ Native Cohere `ClientV2` adapter implemented as a separate provider
   transport (`cohere_native.py`).
3. ✅ Offline request-capture and strict-schema tests run (59 tests).
4. ✅ First live confirmation (unprojected schema) — rejected (400),
   original error capture lost the reason (fixed afterward).
5. ✅ Schema projection v1 implemented (removes `minimum`/`maximum`).
   Second live confirmation — **rejected again (400), but this time the
   exact cause was recovered: `$id` is an unsupported field.**
6. ✅ Schema projection v2 implemented (additionally removes `$id`, new
   category `UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS`; `$schema`
   deliberately untouched — unevidenced). Third live confirmation
   (request_hash `be312ecf...`) — **rejected a third time (400), but the
   error moved to a new field: `schema_version` missing required `type`.**
7. ✅ Schema projection v3 implemented (additionally adds `type: "string"`
   to `schema_version` — new category, an *addition* not a removal,
   mechanically inferred from the `const` value's Python type); protocol
   bumped so this request cannot collide with any prior one; full suite
   passed (1016/22/0).
8. ✅ Fourth live confirmation (request_hash `f062ea28...`) — **SUCCESS.**
   `finish_reason: COMPLETE`, valid judgment generated
   (`preference: "ABSTAIN"`, `confidence: 0.0`), passed full canonical
   local validation unchanged. First successful native Cohere
   structured-output judgment in this investigation.
9. **Next:** wire the native transport into `dispatch.call_provider`/the
   frozen collector (plan documented, not started).
10. Once wired and offline-tested, run a clean four-provider canary.
11. If native Cohere is somehow still unworkable end-to-end after wiring,
    freeze a new three-provider or replacement-provider panel version
    instead.
12. Only then consider the bounded micro-pilot.

Steps 1-8 are done; steps 9-12 are planned, not completed.
