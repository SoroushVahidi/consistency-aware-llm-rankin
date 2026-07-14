#!/usr/bin/env bash
# Remaining overnight value: numeric audit + REVISION_SUMMARY sync + final compile check.
set -euo pipefail
REPO=/home/soroush/consistency-aware-llm-rankin
OUT=$REPO/reports/jdiq-overnight-cont-20260713-230229
PY=$REPO/.venv/bin/python
MS=$REPO/papers/JDIQ_2026/manuscript
cd "$REPO"
echo STARTED: "$(date -Is)"

"$PY" "$OUT/scripts/phase08_numeric_audit.py" | tee "$OUT/logs/phase08.log"

# Sync REVISION_SUMMARY CombMNZ overnight section with actual deltas
"$PY" - <<'PY'
from pathlib import Path
import json
rev = Path('/home/soroush/consistency-aware-llm-rankin/papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md')
comb = json.loads(Path('/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/tables/phase03_combmnz.json').read_text())
t = rev.read_text()
block = [
    '',
    '## Overnight CombMNZ computation (verified)',
    '',
    f"**Decision:** {comb['decision']}",
    '',
]
for ds, row in comb['datasets'].items():
    block.append(
        f"- {ds}: CombSUM={row['combsum_mean_ndcg']:.4f}, CombMNZ={row['combmnz_mean_ndcg']:.4f}, "
        f"Δ={row['delta_mnz_minus_sum']:+.4f} (n={row['n']})"
    )
block.append('')
block.append('Numbers stay out of main PDF tables; scoping sentence only.')
block.append('')
if '## Overnight CombMNZ computation (verified)' in t:
    pre = t.split('## Overnight CombMNZ computation (verified)')[0].rstrip()
    # drop trailing overnight auto block duplication carefully
    t = pre + '\n'
# Append before end
t = t.rstrip() + '\n' + '\n'.join(block)
rev.write_text(t)
print('REVISION_SUMMARY synced')
PY

# Append numeric audit summary into overnight report
{
  echo
  echo '## Numeric audit'
  cat "$OUT/NUMERIC_AUDIT.md"
} >> "$OUT/OVERNIGHT_REPORT.md"
cp "$OUT/OVERNIGHT_REPORT.md" "$MS/OVERNIGHT_CONTINUATION_REPORT.md"

# Final compile + identity/forbidden checks
cd "$MS"
tectonic -X compile main.tex --keep-logs
pdfinfo main.pdf | tee "$OUT/logs/pdfinfo_final.txt"
pdftotext main.pdf "$OUT/logs/main_pdftotext_final.txt"
"$PY" - <<'PY'
from pathlib import Path
import re
tex=Path('main.tex').read_text()
txt=Path('/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/logs/main_pdftotext_final.txt').read_text(errors='ignore')
fail=[]
for ph in ['original study','blocking audit','not yet performed','github.com/SoroushVahidi','/home/soroush/']:
    if ph.lower() in tex.lower() or ph.lower() in txt.lower():
        fail.append(ph)
assert not fail, fail
assert 'seed 13' in txt.lower() or 'seed~13' in tex
assert 'seed 17' in txt.lower() or 'seed~17' in tex
print('final_checks_ok pages=', re.search(r'Pages:\s+(\d+)', Path('/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/logs/pdfinfo_final.txt').read_text()).group(1))
PY

cd "$REPO"
# Rebuild artifact one last time so it matches final PDF (optional but high value)
bash "$OUT/scripts/phase04_prepare_anonymous_artifact.sh" | tee "$OUT/logs/phase04_final.log"
grep -q 'NO IDENTITY LEAKS' "$OUT/artifact_prep/IDENTITY_LEAK_SCAN.txt"
test ! -f "$OUT/artifact_prep/LEAK_FAIL"

git add -- \
  papers/JDIQ_2026/manuscript/main.tex \
  papers/JDIQ_2026/manuscript/main.pdf \
  papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md \
  papers/JDIQ_2026/manuscript/OVERNIGHT_CONTINUATION_REPORT.md \
  reports/jdiq-overnight-cont-20260713-230229
if git diff --cached --quiet; then
  echo 'Nothing to commit'
else
  git commit -m "$(cat <<'EOF'
Add overnight numeric audit and finalize JDIQ continuity docs.

Record verified CombMNZ deltas, confirm seed/Holm narrative consistency against package tables, and refresh the scrubbed anonymous review artifact.
EOF
)"
  git push origin HEAD
  echo PUSHED: "$(git rev-parse --short HEAD)"
fi
echo FINISHED: "$(date -Is)"
