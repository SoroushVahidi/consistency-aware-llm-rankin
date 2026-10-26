# Resource amendment v2 — before any prospective response

This document supersedes only the local resource/launch provisions of
PROTOCOL.md. Its scientific design, model revision, prompts/parser, acceptance
thresholds, query membership, pools, seeds, endpoints, analysis and missingness
rules are unchanged. Original local manifests and failure receipts remain
preserved. Neither local attempt generated a model comparison or utility
outcome. No development result was available for protocol tuning.

The 16-GB local GPU could not load the complete BF16 checkpoint: the loader
needed a further 2.03 GiB after 14.19 GiB had been allocated. Keep BF16 and the
same checkpoint; do not quantize or substitute a different judge to evade the
failure. The local process has exited and its GPU allocation is released.

Use Wulver account ikoutis, partition debug_gpu, QOS debug, one A100 **40-GB
MIG** device. Its larger slice supplies loading/inference headroom and better
prospects of fitting the existing bounded campaign within the QOS wall limit.
Allocate at most **four CPUs and 14 GiB host RAM**, keeping inference/BLAS at
two threads. This respects the inspected debug QOS ceiling (four CPUs, 16 GiB,
eight hours), including memory-driven CPU allocation. No other job or model
cache may be changed. No simultaneous local campaign, paid API, cloud credit,
new model-weight download or automatic requeue.

New ceiling: **eight scheduler wall-hours**, at most 27,600 cumulative active
worker seconds (7h40m), with the unchanged 3,600-second analysis reserve included
in the gate's runtime projection. This reduces GPU wall allowance from the
original 12 hours. Retain the 30-GiB new-disk cap and frozen response/attempt
ceilings. A validation-only allocation may precede the main job; its charged
seconds stay in the same ledger. Use the remaining ledger budget on explicit
resume, never reset it. Stop if the measured gate estimate cannot fit.

Use the existing Wulver CUDA environment read-only and the existing preserved
PySCIPOpt 6.2.1 dependency directory read-only. Actual package versions are
recorded before development. Clone only necessary source into a separate
private run/worktree. All current tokenizer/config files come from the pinned
local snapshot; remote cached weight shards may be symlinked only when their
saved identities match current official hashes. Rehash every shard inside the
allocation before model loading. No mutation of the historical cached model.

Stage a **new** immutable resource-bound manifest, citing its parent frozen
preparation and amendment hash. Retain identical development/evaluation input
bytes and qrels. Verify destination copies, code/core/model identities, actual
Slurm allocation, visible-device count, and GPU memory before acquisition.
Do not claim a new historical model execution or a different scientific sample.

Slurm owns device-conflict isolation, including MIG. Require exactly one
allocated visible device; do not reject or terminate legitimate processes on
other MIG instances based on a global nvidia-smi process list. Local execution
retains its unrelated-process refusal. A scheduler-pending job is reported as
pending, not a passed gate or running main experiment.

Run the same 240-response gate first. Main acquisition is allowed only after
its identity-bound pass. If it fails, preserve diagnostics and stop; no prompt,
threshold or model switch is authorized within this version. Perform a short
health check after the main launch and leave healthy work running.
