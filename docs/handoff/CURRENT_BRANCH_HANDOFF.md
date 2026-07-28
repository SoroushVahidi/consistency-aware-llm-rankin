# Branch Handoff: fix/outcome-f-production-operating-point

*Branch-specific companion to `PROJECT_STATUS.md`. Read that first for the
repository-wide picture; this document is scoped to this branch's history
and exact continuation point.*

## Branch purpose

Originally: enforce the Outcome F interim production operating point
(always-UHT + non-routing safety floor) and correct an invalid
`production_uht` evaluation. The branch then extended into building and
canary-testing a real, qrels-grounded, multi-provider counterfactual
LLM-judge benchmark — the active work as of this handoff.

## Base and divergence

- Diverged from `origin/main` at `3e02b73666506f3eb894f5df2c531284ea31a60e`
  ("Update JDIQ title page with verified support and acknowledgments").
- `documented_code_head` (the code state this handoff describes, **not**
  a promise about the current branch tip — this documentation commit
  itself lands after it): `ab4e06475ed47ed2ae59300cd5e1e796a18378ae`.
- 14 commits ahead of `origin/main`, 0 behind, as of `documented_code_head`.

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
14. **`ab4e064` — docs: add repository status and branch handoff.** (Current
    HEAD.) Adds `PROJECT_STATUS.md`, this handoff document, and
    `docs/handoff/state_snapshot.json`; documentation only, no
    source/config/test changes.

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

Expected `documented_code_head`: `3a47e9001ccc2ef14ae85e72a15f623cdcff19ad`,
13 ahead / 0 behind, branch `fix/outcome-f-production-operating-point`. The
actual HEAD after this documentation lands will be one commit ahead of
that — re-run the commands above rather than trusting this number.

## Staged or uncommitted work

**None, as of this document landing.** Two things were staged on top of
`ab4e064` and are committed together with this documentation update:

1. The native Cohere `ClientV2` transport and schema-projection modules
   (`cohere_native.py`, `cohere_schema_projection.py`) plus their offline
   tests — see "Cohere structured-output enforcement" above for the full
   evidence trail (schema/transport confirmed working; collector wiring
   deliberately deferred).
2. This documentation pass itself (`PROJECT_STATUS.md`,
   `CURRENT_BRANCH_HANDOFF.md`, `state_snapshot.json`,
   `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md`), reconciling stale
   test-count claims and other drift found during a branch cleanup pass.

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

**Unstaged:** none (other than this documentation commit itself).

**Untracked (local-only, not to be added per `docs/ARTIFACT_POLICY.md`):**
- `reports/counterfactual_collector_canary_v1_20260727T145126Z/`
- `reports/counterfactual_collector_canary_v2_20260727T161921Z/`
- `reports/cohere_normalization_diagnostic_20260727T183000Z/`
- `reports/cohere_json_schema_confirmation_20260727T200000Z/`

## Safety branches

Local-only (not pushed), one per major checkpoint on this branch:

```
backup/pre-cohere-schema-enforcement-20260727      (points at 3a47e90)
backup/pre-cohere-normalization-diagnostic-20260727 (points at 3a47e90)
backup/pre-counterfactual-canary-v2-20260727        (points at fb74974)
backup/pre-counterfactual-canary-20260727           (points at fb74974)
backup/pre-counterfactual-collector-20260727        (points at 32d39a9)
backup/pre-counterfactual-pilot-freeze-20260727     (points at 07b4ba2)
backup/pre-provider-capability-audit-20260727       (points at d158a04)
backup/pre-driver-organization-20260727             (points at 923ee35)
backup/pre-multifactor-eval-fix-20260726            (points at 5465ea6)
backup/pre-polish-outcome-f-20260726                (points at 89b9406)
```

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

## Current scientific interpretation

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

See `PROJECT_STATUS.md`'s "Evidence and artifact registry" for the full
classification. All counterfactual/Cohere report directories in this
branch's working tree are local-only, untracked, and explicitly labeled
canary/diagnostic-only in their own status fields — none constitute
benchmark data. This includes `reports/cohere_native_v2_confirmation_20260727T210000Z/`,
`reports/cohere_native_v2_schema_projection_confirmation_20260728T000000Z/`
(v1-projection),
`reports/cohere_native_v2_schema_projection_v2_confirmation_20260728T010224Z/`
(v2-projection, rejected), and
`reports/cohere_native_v2_schema_projection_v3_confirmation_20260728T011703Z/`
(v3-projection, **succeeded**) — the native transport's four confirmation
attempts.

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

The native Cohere transport (schema projection v3) is live-confirmed
working. The next task is implementing its wiring into
`dispatch.call_provider`/the frozen collector, per the plan in
`docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` ("Native Cohere
collector-wiring plan") — not yet started. Only after that is implemented
and offline-tested should a clean four-provider canary be attempted. Do
not run the micro-pilot yet. See "Exact next action" at the end of this
document.

## Tasks that must not be started yet

- The 256-384 call bounded micro-pilot (`counterfactual_micro_pilot_v2`).
- Any real oracle-opportunity audit (design-only so far).
- Any provider call without an explicit, scoped, up-front authorization
  (query, pair, provider, and a stated call ceiling).
- Any change to `production_config.py` / the always-UHT default.
- Any edit to a frozen protocol artifact (prompt, schema, v1 pool protocol)
  in place — add a new version instead.

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
ruff check <changed files>
mypy <changed files, together with at least one src module in the same invocation>
python -m compileall -q src scripts
git diff --check
git diff --cached --check
```

Note: `tests/test_counterfactual_cohere_json_schema.py` (the
compatibility-path attempt's test file) does **not** exist on this
branch — it lives only on the archived
`archive/cohere-compat-schema-failed-20260727` branch. Do not add it back
here.

Last verified 2026-07-28T03:14:55Z, with `dev`+`llm`+`exact` optional
extras installed (`pip install -e ".[dev,llm,exact]"`): full suite 1038
passed / 0 skipped / 0 failed; all lint/type/compile checks clean. Skip
counts are environment-dependent (see `PROJECT_STATUS.md`'s "Current
validation status") — re-run rather than trusting a cached number.

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

## Exact next action

The native Cohere transport is live-confirmed working (schema projection
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
