#!/usr/bin/env bash
# Hard-fail CombMNZ completion + artifact rebuild + commit/push.
set -euo pipefail

REPO="/home/soroush/consistency-aware-llm-rankin"
OUT="$REPO/reports/jdiq-overnight-cont-20260713-230229"
MS="$REPO/papers/JDIQ_2026/manuscript"
PY="$REPO/.venv/bin/python"

cd "$REPO"
echo "STARTED: $(date -Is)"

"$PY" "$OUT/scripts/phase03_combmnz_explore.py" | tee "$OUT/logs/phase03_fixed.log"
test -f "$OUT/tables/phase03_combmnz.json"
test -f "$OUT/COMBMNZ_ASSESSMENT.md"

"$PY" - <<'PY'
import json
from pathlib import Path
OUT = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229")
r = json.loads((OUT / "tables/phase03_combmnz.json").read_text())
assert r.get("results"), r
assert not str(r.get("decision", "")).startswith("FAILED"), r
print("COMBMNZ_OK", r["decision"][:200])
print(json.dumps(r.get("datasets", {}), indent=2))

ms_report = Path("/home/soroush/consistency-aware-llm-rankin/papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md")
text = ms_report.read_text() if ms_report.exists() else "# JDIQ Overnight Continuation Report\n"
add = [
    "",
    "## CombMNZ addendum (hard-fail rerun)",
    "",
    f"**Decision:** {r['decision']}",
    "",
]
for ds, row in r.get("datasets", {}).items():
    add.append(
        f"- {ds}: CombSUM={row['combsum_mean_ndcg']:.4f}, "
        f"CombMNZ={row['combmnz_mean_ndcg']:.4f}, "
        f"Δ={row['delta_mnz_minus_sum']:+.4f} (n={row['n']})"
    )
add.append("")
add.append("Numbers exploratory only; no baseline table added.")
add.append("")
if "## CombMNZ addendum" in text:
    text = text.split("## CombMNZ addendum")[0].rstrip() + "\n"
ms_report.write_text(text.rstrip() + "\n" + "\n".join(add))
(OUT / "OVERNIGHT_REPORT.md").write_text(ms_report.read_text())
print("reports updated")
PY

# Ensure CombMNZ scoping sentence is present
"$PY" - <<'PY'
from pathlib import Path
tex_path = Path("/home/soroush/consistency-aware-llm-rankin/papers/JDIQ_2026/manuscript/main.tex")
t = tex_path.read_text()
old = "primary baseline family with CombMNZ; the study's comparative focus is"
new = (
    "primary baseline family with CombMNZ (an exploratory stored-score CombMNZ "
    "check did not overturn CombSUM's role enough to justify expanding the baseline "
    "table); the study's comparative focus is"
)
if old in t:
    tex_path.write_text(t.replace(old, new, 1))
    print("inserted CombMNZ scoping clause")
elif "exploratory stored-score CombMNZ" in t:
    print("CombMNZ scoping clause already present")
else:
    raise SystemExit("CombMNZ baseline sentence not found for update")
PY

cd "$MS"
tectonic -X compile main.tex --keep-logs
pdfinfo main.pdf | tee "$OUT/logs/pdfinfo_after_combmnz.txt"
pdftotext main.pdf "$OUT/logs/main_pdftotext_after_combmnz.txt"

"$PY" - <<'PY'
from pathlib import Path
tex = Path("/home/soroush/consistency-aware-llm-rankin/papers/JDIQ_2026/manuscript/main.tex").read_text()
assert "not yet performed" not in tex
assert "exploratory stored-score CombMNZ" in tex
assert "github.com/SoroushVahidi" not in tex
print("tex_ok")
PY

cd "$REPO"
bash "$OUT/scripts/phase04_prepare_anonymous_artifact.sh" | tee "$OUT/logs/phase04_after_combmnz.log"
test ! -f "$OUT/artifact_prep/LEAK_FAIL"
grep -q "NO IDENTITY LEAKS" "$OUT/artifact_prep/IDENTITY_LEAK_SCAN.txt"

git add -- \
  papers/JDIQ_2026/manuscript/main.tex \
  papers/JDIQ_2026/manuscript/main.pdf \
  papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md \
  papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md \
  reports/jdiq-overnight-cont-20260713-230229

if git diff --cached --quiet; then
  echo "Nothing staged to commit"
else
  git commit -m "$(cat <<'EOF'
Complete exploratory CombMNZ assessment for JDIQ baselines.

Fix CombSUM API usage, record per-dataset stored-score CombMNZ vs CombSUM deltas, and keep CombMNZ out of the primary baseline table while updating the anonymous artifact.
EOF
)"
  git push origin HEAD
  echo "PUSHED: $(git rev-parse --short HEAD)"
fi

echo "FINISHED: $(date -Is)"
