#!/usr/bin/env python3
"""Phase 6: overnight report; commit+push manuscript-only changes if validation passed."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-20260713-225928"
MS = REPO / "papers/JDIQ_2026/manuscript"

val = json.loads((OUT / "tables" / "phase05_validation.json").read_text())
comb = {}
if (OUT / "tables" / "phase02_combmnz.json").exists():
    comb = json.loads((OUT / "tables" / "phase02_combmnz.json").read_text())
ret = {}
if (OUT / "tables" / "phase01_retention_evidence.json").exists():
    ret = json.loads((OUT / "tables" / "phase01_retention_evidence.json").read_text())

artifact_ready = (OUT / "artifact_prep/anonymous_review_bundle/anonymous_review_artifact.zip").exists()
leak = (OUT / "artifact_prep/IDENTITY_LEAK_SCAN.txt").read_text() if (OUT / "artifact_prep/IDENTITY_LEAK_SCAN.txt").exists() else ""

report = f"""# JDIQ Overnight Report

**Finished:** {datetime.now(timezone.utc).isoformat()}
**Start HEAD expected:** `db6edb61b601ca9c5035fd17fcf53c4dd14d0acc`
**Actual HEAD at report time:** `{subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip()}`

## Priorities executed

1. **Retention-target sensitivity** — integrated verified existing investigation into manuscript Limitations/Discussion (was incorrectly labeled \"untested\").
2. **CombMNZ exploratory** — computed from stored scores; decision: `{comb.get('decision','n/a')}`.
3. **Anonymous artifact package** — local scrubbed zip/tar prepared: `{artifact_ready}`. Upload URL still requires manual anonymous.4open.science step.
4. **Presentation/validation** — compile + forbidden-phrase / cite / ref checks.

## Validation

```json
{json.dumps(val, indent=2)}
```

## Identity leak scan (artifact)

```
{leak[:2000]}
```

## Remaining human/submission steps

1. Upload scrubbed zip to anonymous.4open.science (or equivalent), verify no identity leaks on the hosted copy.
2. Insert the verified anonymous URL into Data Availability only after the URL exists.
3. Do not include author GitHub URL in the anonymous PDF.
"""

(OUT / "OVERNIGHT_REPORT.md").write_text(report)
# Append brief note to REVISION_SUMMARY
rev = MS / "REVISION_SUMMARY.md"
if rev.exists():
    note = (
        "\n\n---\n\n## Overnight integration (auto)\n\n"
        f"- Retention-sensitivity Limitations claim corrected using `reports/retention_matching_investigation/`.\n"
        f"- CombMNZ exploratory: {comb.get('decision','n/a')}\n"
        f"- Local anonymous artifact package prepared under `{OUT}/artifact_prep/` "
        "(hosted anonymous URL still unresolved).\n"
        f"- Validation pages={val.get('pages')}; fail={val.get('fail')}\n"
    )
    txt = rev.read_text()
    if "Overnight integration (auto)" not in txt:
        rev.write_text(txt + note)

# Commit only if validation passed and manuscript changed
if val.get("fail"):
    print("Skipping commit due to validation failures.")
else:
    # stage manuscript-related deltas only
    to_add = [
        "papers/JDIQ_2026/manuscript/main.tex",
        "papers/JDIQ_2026/manuscript/main.pdf",
        "papers/JDIQ_2026/manuscript/references.bib",
        "papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md",
        "papers/JDIQ_2026/manuscript/COLD_REVIEW_FIXES.md",
        "papers/JDIQ_2026/manuscript/SECONDARY_METRIC_ASSESSMENT.md",
        f"reports/jdiq-overnight-20260713-225928/OVERNIGHT_REPORT.md",
        f"reports/jdiq-overnight-20260713-225928/COMBMNZ_ASSESSMENT.md",
        f"reports/jdiq-overnight-20260713-225928/artifact_prep/UPLOAD_INSTRUCTIONS.md",
        f"reports/jdiq-overnight-20260713-225928/artifact_prep/ARTIFACT_MANIFEST.json",
        f"reports/jdiq-overnight-20260713-225928/artifact_prep/IDENTITY_LEAK_SCAN.txt",
        f"reports/jdiq-overnight-20260713-225928/tables",
    ]
    # Also add artifact zip if not huge? Skip binary zip from git if very large — check size
    zip_path = OUT / "artifact_prep/anonymous_review_bundle/anonymous_review_artifact.zip"
    if zip_path.exists() and zip_path.stat().st_size < 80_000_000:
        to_add.append(str(zip_path.relative_to(REPO)))
        to_add.append(str((OUT / "artifact_prep/anonymous_review_bundle/anonymous_review_artifact.tar.gz").relative_to(REPO)))

    existing = [p for p in to_add if (REPO / p).exists()]
    subprocess.run(["git", "add", "--", *existing], cwd=REPO, check=True)
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=REPO, text=True).strip()
    if not staged:
        print("No staged manuscript changes to commit.")
    else:
        msg = (
            "Integrate overnight JDIQ retention sensitivity and artifact prep.\n\n"
            "Correct the untested retention-sensitivity limitation using verified "
            "existing sweeps, document CombMNZ exploration, and add a scrubbed "
            "anonymous review bundle for submission packaging."
        )
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO, check=True)
        print("Committed and pushed to origin/main")
        print(subprocess.check_output(["git", "log", "-1", "--oneline"], cwd=REPO, text=True))

print("Phase 6 complete.")
print(report[:1500])
