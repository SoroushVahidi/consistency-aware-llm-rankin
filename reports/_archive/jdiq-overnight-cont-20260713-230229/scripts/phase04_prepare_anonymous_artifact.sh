#!/usr/bin/env bash
# Rebuild scrubbed anonymous artifact; fail the scan if identity leaks remain.
set -euo pipefail
REPO="/home/soroush/consistency-aware-llm-rankin"
OUT="/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229"
ART="$OUT/artifact_prep/anonymous_review_bundle"
STAGE="$OUT/artifact_prep/stage"
rm -rf "$ART" "$STAGE"
mkdir -p "$ART" "$STAGE/manuscript" "$STAGE/inputs" "$STAGE/tables" "$STAGE/code_snapshot" "$STAGE/docs"

echo "Building staged artifact contents..."

# Compile should already have refreshed PDF; copy current sources.
cp "$REPO/papers/JDIQ_2026/manuscript/main.pdf" "$STAGE/manuscript/"
cp "$REPO/papers/JDIQ_2026/manuscript/main.tex" "$STAGE/manuscript/"
cp "$REPO/papers/JDIQ_2026/manuscript/references.bib" "$STAGE/manuscript/"
cp -a "$REPO/papers/JDIQ_2026/manuscript/figures_v2" "$STAGE/manuscript/" 2>/dev/null || true
find "$STAGE/manuscript" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

for ds in scidocs fiqa hotpotqa bright; do
  mkdir -p "$STAGE/inputs/$ds"
  src="$REPO/experiments/method_improvement_audit_20260711_205733/inputs/$ds"
  if [[ -d "$src" ]]; then
    cp -a "$src"/. "$STAGE/inputs/$ds/" || true
  fi
done

TAB="$REPO/reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables"
if [[ -d "$TAB" ]]; then
  cp -a "$TAB"/. "$STAGE/tables/" || true
fi

rsync -a --exclude '__pycache__' --exclude '*.pyc' \
  "$REPO/src/consistency_ranker" "$STAGE/code_snapshot/src/"
mkdir -p "$STAGE/code_snapshot/reports_scripts"
cp "$REPO/reports/full_calibrated_core/scripts/"*.py "$STAGE/code_snapshot/reports_scripts/" 2>/dev/null || true
cp "$REPO/requirements.txt" "$STAGE/code_snapshot/" 2>/dev/null || true
cp "$REPO/pyproject.toml" "$STAGE/code_snapshot/pyproject.toml.raw" 2>/dev/null || true

# Pin note for reproducibility reviewers
if [[ -f "$REPO/requirements.txt" ]]; then
  {
    echo "# Environment note"
    echo "Primary mechanical stack: Python 3.12.x; pinned-ish deps in requirements.txt."
    echo "networkx is used for graph construction/repair; SciPy/NumPy for metrics."
    echo "Exact ILP repair check used PySCIPOpt/SCIP (see manuscript §4 / Limitations)."
  } > "$STAGE/docs/ENVIRONMENT.md"
fi

cat > "$STAGE/README.md" <<'EOF'
# Anonymous review artifact — preference-graph repair measurement study

This bundle supports double-anonymous review of the accompanying manuscript.

## Contents
- `manuscript/` — TeX sources, PDF, figures
- `inputs/` — stored BM25 / TF-IDF / MiniLM scores and query-ID lists
- `tables/` — manuscript-ready calibrated tables
- `code_snapshot/` — ranking/repair/evaluation code needed to regenerate mechanical results
- `docs/ENVIRONMENT.md` — dependency notes

## Anonymity
Author identity, institutional affiliation, and public repository remotes are withheld.
Do not attempt to deanonymize during review.

## Reproduction (high level)
1. Install Python >=3.11 and dependencies from `code_snapshot/requirements.txt`.
2. Use stored inputs under `inputs/` (do not regenerate upstream retrieval).
3. Follow manifests in `tables/` / manuscript Data Availability section for seeds and protocols.

Bootstrap seed 13; permutation seed 17; 10,000 resamples each (manuscript Experimental Setup).
EOF

python3 - <<'PY'
from pathlib import Path
import re
raw = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/stage/code_snapshot/pyproject.toml.raw")
if raw.exists():
    t = raw.read_text()
    for pat in ["Soroush", "Vahidi", "soroush", "github.com/SoroushVahidi", "sv96@", "njit.edu"]:
        t = t.replace(pat, "REDACTED")
    t = re.sub(
        r'(authors?\s*=\s*\[[^\]]*\])',
        'authors = [{ name = "Anonymous", email = "anonymous@example.com" }]',
        t,
        flags=re.I,
    )
    raw.with_suffix('').write_text(t) if False else None
    Path(str(raw).replace('.raw', '')).write_text(t)
    raw.unlink(missing_ok=True)
    print("scrubbed pyproject")
PY

# Scrub any residual home/author strings inside staged text sources (not binary scores).
python3 - <<'PY'
from pathlib import Path
root = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/stage")
replacements = {
    "/home/soroush/consistency-aware-llm-rankin-caar": "<REDACTED_SIBLING_REPO>",
    "/home/soroush/": "<REDACTED_HOME>/",
    "SoroushVahidi": "REDACTED",
    "Soroush Vahidi": "Anonymous Author",
    "Soroush": "Anonymous",
    "Vahidi": "Author",
    "sv96@njit.edu": "anonymous@example.com",
    "njit.edu": "example.com",
    "NJIT": "REDACTED_ORG",
}
text_ext = {".py", ".tex", ".md", ".txt", ".toml", ".cfg", ".yml", ".yaml", ".json", ".bib", ".csv"}
for p in root.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix.lower() not in text_ext and p.name not in {"REQUIREMENTS", "LICENSE"}:
        continue
    try:
        t = p.read_text(errors="ignore")
    except Exception:
        continue
    orig = t
    for a, b in replacements.items():
        t = t.replace(a, b)
    if t != orig:
        p.write_text(t)
        print("scrubbed", p.relative_to(root))
PY

python3 - <<'PY'
from pathlib import Path
root = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/stage")
needles = [
    "Soroush", "Vahidi", "soroush@", "github.com/SoroushVahidi",
    "/home/soroush/", "njit", "NJIT", "sv96@",
]
hits = []
for p in root.rglob("*"):
    if p.is_dir():
        continue
    if p.suffix.lower() in {".png", ".pkl", ".npy", ".npz", ".jpg", ".jpeg"}:
        continue
    try:
        data = p.read_bytes()
    except Exception:
        continue
    for n in needles:
        if n.encode() in data:
            # pdf may contain producer strings; allow only TeX producer without author
            hits.append((str(p.relative_to(root)), n))
out = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/IDENTITY_LEAK_SCAN.txt")
if hits:
    # Filter known-benign PDF metadata producer if any (XeTeX/acm) — keep listed.
    out.write_text("LEAKS FOUND:\n" + "\n".join(f"{a}\t{b}" for a, b in hits) + "\n")
    print("WARNING: identity leak hits; see IDENTITY_LEAK_SCAN.txt")
    # Do not abort packaging, but write fail flag for validator.
    Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/LEAK_FAIL").write_text("1\n")
else:
    out.write_text("NO IDENTITY LEAKS FOUND\n")
    print("NO IDENTITY LEAKS FOUND")
    Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/LEAK_FAIL").unlink(missing_ok=True)
PY

# PDF metadata note
echo "exiftool may be unavailable; PDF Creator is TeX toolchain (non-identifying)." \
  > "$OUT/artifact_prep/PDF_METADATA_NOTE.txt"
if command -v exiftool >/dev/null 2>&1; then
  exiftool -overwrite_original -Author= -Creator= -Producer="TeX" \
    "$STAGE/manuscript/main.pdf" || true
fi

(
  cd "$STAGE"
  tar -czf "$ART/anonymous_review_artifact.tar.gz" .
  zip -qr "$ART/anonymous_review_artifact.zip" .
)

python3 - <<'PY'
import hashlib, json
from pathlib import Path
art = Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/anonymous_review_bundle")
manifest = {}
for p in sorted(art.glob("*")):
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest[p.name] = {"bytes": p.stat().st_size, "sha256": h}
Path("/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/artifact_prep/ARTIFACT_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
print(manifest)
PY

cat > "$OUT/artifact_prep/UPLOAD_INSTRUCTIONS.md" <<'EOF'
# Upload instructions (human / submission step)

1. Prefer `anonymous.4open.science` (or equivalent anonymity-preserving host).
2. Upload `anonymous_review_bundle/anonymous_review_artifact.zip`.
3. After hosting, verify:
   - clone/download URL does not redirect to `github.com/SoroushVahidi/...`
   - README and HTML title remain anonymous
   - re-run a string scan for author name / institution / home paths
4. Only then paste the verified anonymous URL into manuscript Data Availability.
5. Do **not** invent or guess a URL in the PDF before the hosted mirror exists.
EOF

ls -lh "$ART"
echo "Phase 4 artifact complete."
