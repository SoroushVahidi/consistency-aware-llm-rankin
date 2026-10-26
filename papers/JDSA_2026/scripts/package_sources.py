"""Package manuscript files only; never include editor-only or experiment artifacts."""
from pathlib import Path
import zipfile,hashlib,json
root=Path(__file__).resolve().parents[1]
src=root/'manuscript';dest=root/'packages';dest.mkdir(exist_ok=True)
files=[f for f in src.iterdir() if f.is_file() and f.suffix in {'.tex','.cls','.bst','.bib','.sh'}]
files += [src/'main.pdf',src/'ESM_1.pdf']
for n in ['main.bbl','supplement.bbl']:
 f=src/'build'/n
 if f.exists():files.append(f)
with zipfile.ZipFile(dest/'JDSA_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,f.name)
 # Include exactly the five used vector figure assets.
 for f in src.glob('*Fig*.pdf'):
  if f not in files:z.write(f,f.name)
manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
for f in src.glob('*Fig*.pdf'):manifest[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
(root/'audit/PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
# This archive remains ignored and local; no other historical files are included.
with zipfile.ZipFile(dest/'editorial_private.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['cover_letter','overlap_disclosure','title_page']:
  for suffix in ['.tex','.pdf']:z.write(root/'editorial'/(name+suffix),name+suffix)
 for name in ['authors.tex','sn-jnl.cls']:z.write(src/name,name)
print('Source package files',len(manifest),'source bytes',(dest/'JDSA_sources.zip').stat().st_size)
