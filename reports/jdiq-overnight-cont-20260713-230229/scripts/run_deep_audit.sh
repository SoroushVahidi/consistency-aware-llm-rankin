#!/usr/bin/env bash
set -euo pipefail
REPO=/home/soroush/consistency-aware-llm-rankin
OUT=$REPO/reports/jdiq-overnight-cont-20260713-230229
cd "$REPO"
echo STARTED: "$(date -Is)"
# deep audit already produced outputs; re-run for certainty
.venv/bin/python "$OUT/scripts/phase09_deep_table_audit.py" | tee "$OUT/logs/phase09.log"
{
  echo
  echo "## Deep table reconciliation"
  cat "$OUT/deep_audit/DEEP_AUDIT.md"
} >> "$OUT/OVERNIGHT_REPORT.md"
cp "$OUT/OVERNIGHT_REPORT.md" papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md
git add -- \
  papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md \
  reports/jdiq-overnight-cont-20260713-230229/deep_audit \
  reports/jdiq-overnight-cont-20260713-230229/OVERNIGHT_REPORT.md \
  reports/jdiq-overnight-cont-20260713-230229/scripts/phase09_deep_table_audit.py \
  reports/jdiq-overnight-cont-20260713-230229/scripts/run_deep_audit.sh
if ! git diff --cached --quiet; then
  git commit -m "$(cat <<'EOM'
Add deep overnight table reconciliation for JDIQ manuscript.

Cross-check highlight bootstrap and graph-structure displays against paper_package CSVs and record unpublished nonzero cells for transparency.
EOM
)"
  git push origin HEAD
  echo PUSHED: "$(git rev-parse --short HEAD)"
else
  echo Nothing to commit
fi
echo FINISHED: "$(date -Is)"
