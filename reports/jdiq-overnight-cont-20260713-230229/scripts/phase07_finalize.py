#!/usr/bin/env python3
"""Write overnight continuation report; commit/push manuscript-scoped changes if clean."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
MS = REPO / "papers/JDIQ_2026/manuscript"

val = {}
vp = OUT / "tables" / "phase06_validation.json"
if vp.exists():
    val = json.loads(vp.read_text())
comb = {}
cp = OUT / "tables" / "phase03_combmnz.json"
if cp.exists():
    comb = json.loads(cp.read_text())
leak = (OUT / "artifact_prep" / "IDENTITY_LEAK_SCAN.txt").read_text() if (
    OUT / "artifact_prep" / "IDENTITY_LEAK_SCAN.txt"
).exists() else "(missing)"

head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
ok = not val.get("fail")

report = f"""# JDIQ Overnight Continuation Report

**Finished:** {datetime.now(timezone.utc).isoformat()}
**HEAD at report time:** `{head}`

## Why this continuation

The first overnight session finished in minutes and left three high-value gaps:
1. Methods still claimed retention sensitivity was \"not yet performed\" while Limitations said otherwise.
2. CombMNZ exploratory log was empty (wrong qrels paths).
3. Anonymous artifact still contained `/home/soroush/` identity leak.

## Priorities executed

1. **Methods/Limitations consistency** for retention-target sensitivity.
2. **Hardcoded home-path leak removed** from `src/.../processor.py`.
3. **CombMNZ exploratory recomputed** — decision: `{comb.get("decision", "n/a")}`.
4. **Anonymous artifact rebuilt** + identity scan.
5. **Validation / compile**.

## Validation

```json
{json.dumps(val, indent=2)}
```

## Identity leak scan (artifact)

```
{leak.strip()}
```

## CombMNZ (exploratory; not added as table)

```json
{json.dumps(comb.get("datasets", {}), indent=2)}
```

## Remaining human/submission steps

1. Upload scrubbed zip to anonymous.4open.science (or equivalent).
2. Insert verified anonymous URL into Data Availability only after URL exists.
3. Do not include author GitHub URL in the anonymous PDF.
"""
(OUT / "OVERNIGHT_REPORT.md").write_text(report)

# Copy report into manuscript folder for easy discovery
(MS / "OVERNIGHT_CONTINUATION_REPORT.md").write_text(report)

if not ok:
    print("Skipping commit/push due to validation failures:", val.get("fail"))
    print(report)
    raise SystemExit(0)

# Stage manuscript-scoped + overnight report paths only
paths = [
    "papers/JDIQ_2026/manuscript/main.tex",
    "papers/JDIQ_2026/manuscript/main.pdf",
    "papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md",
    "papers/JDIQ_2026/manuscript/PRE_SUBMISSION_REVIEW.md",
    "papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md",
    "src/consistency_ranker/repair_selector_mining/processor.py",
    "reports/jdiq-overnight-cont-20260713-230229",
]
subprocess.check_call(["git", "add", "--", *paths], cwd=REPO)
status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True)
if not status.strip():
    print("Nothing to commit")
else:
    msg = (
        "Close overnight JDIQ consistency gaps and scrub artifact leaks.\n\n"
        "Align Methods with retention-sensitivity evidence, remove a hardcoded home-path "
        "identity leak, recompute exploratory CombMNZ, and rebuild the anonymous review bundle."
    )
    subprocess.check_call(
        ["git", "commit", "-m", msg],
        cwd=REPO,
    )
    # push
    push = subprocess.run(["git", "push", "origin", "HEAD"], cwd=REPO, text=True, capture_output=True)
    print(push.stdout)
    print(push.stderr)
    if push.returncode != 0:
        print("PUSH_FAILED")
    else:
        print("Committed and pushed to origin/main")
        print(subprocess.check_output(["git", "log", "-1", "--oneline"], cwd=REPO, text=True))

print("Phase 7 complete.")
print(report)
