"""Package editable manuscript and data-free verifiers; exclude private inputs."""

import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "manuscript"
destination = root / "packages"
destination.mkdir(exist_ok=True)
files = [
    f
    for f in source.iterdir()
    if f.is_file() and f.suffix in {".tex", ".cls", ".bst", ".bib", ".sh"}
]
files += [source / "main.pdf", source / "ESM_1.pdf"]
files += [
    source / n for n in ("Fig2.pdf", "Fig3.pdf", "ESM_Fig1.pdf", "ESM_Fig2.pdf", "ESM_Fig3.pdf")
]
files += [
    root / "scripts" / n
    for n in (
        "verify_relevance_profiles.py",
        "verify_optimum_envelope.py",
        "stratify_selected_cache.py",
        "test_selected_composition.py",
    )
]
files += [root / n for n in ("OFFLINE_VERIFICATION.md", "STRATIFIED_ATTRIBUTION.md")]
files += [source / "build" / n for n in ("main.bbl", "supplement.bbl")]
manifest = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
license_path = root.parents[1] / "LICENSE"
manifest["LICENSE_VERIFICATION_CODE.txt"] = hashlib.sha256(license_path.read_bytes()).hexdigest()
if len(manifest) != len(files) + 1:
    raise ValueError("Duplicate flat archive filename")
with zipfile.ZipFile(destination / "JDSA_sources.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for f in sorted(files):
        archive.write(f, f.name)
    archive.write(license_path, "LICENSE_VERIFICATION_CODE.txt")
(root / "audit" / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
archive_size = (destination / "JDSA_sources.zip").stat().st_size
print(f"Source package: {len(manifest)} files, {archive_size} bytes")
