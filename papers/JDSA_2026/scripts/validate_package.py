"""Document and preservation checks only; executes no scientific workflow."""
from pathlib import Path
import re,json,zipfile,hashlib,subprocess
root=Path(__file__).resolve().parents[1];src=root/'manuscript';audit=root/'audit';checks=[]
def check(name,ok,detail=None):checks.append({'check':name,'pass':bool(ok),'detail':detail})
old=zipfile.ZipFile(audit/'finalized_IJIT_source.zip')
main=(src/'main.tex').read_text();si=(src/'supplement.tex').read_text()
oldmain=old.read('main.tex').decode();oldsi=old.read('supplement.tex').decode()
# Table bodies do not change; class/float names and numbering layout may change.
def tabs(s):return re.findall(r'\\begin\{tabularx\}.*?\\end\{tabularx\}',s,re.S)
check('all main table bodies unchanged',tabs(main)==tabs(oldmain),len(tabs(main)))
for n in old.namelist():
 if n.startswith('tables/') and n.endswith('.tex'):check('unchanged SI table '+Path(n).name,(src/Path(n).name).read_bytes()==old.read(n))
mapping=json.loads((audit/'FIGURE_MAPPING.json').read_text())
for n,new in mapping.items():check('unchanged figure '+new,(src/new).read_bytes()==old.read('figures/'+n))
# Restore only editorial figure-name and float changes before comparing the results.
def norm(s):
 for n,new in mapping.items():s=s.replace('{'+new+'}','{'+n+'}')
 return s.replace('figure*','figure').replace('table*','table')
a=main.index(r'\section{Structural and Ranking Opportunities}');b=main.index(r'\section{Discussion and Limitations}')
a0=oldmain.index(r'\section{Structural and Ranking Opportunities}');b0=oldmain.index(r'\section{Discussion and Limitations}')
check('complete results sections unchanged',norm(main[a:b])==oldmain[a0:b0])
for label in ['sec:statistics']:
 a=main.index(r'\subsection{Evaluation and query-level inference}');b=main.index(r'\subsection{Evidence access and AI assistance}')
 a0=oldmain.index(r'\subsection{Evaluation and query-level inference}');b0=oldmain.index(r'\subsection{Evidence access and AI assistance}')
 check('statistical methods unchanged',main[a:b]==oldmain[a0:b0])
abs=re.search(r'\\abstract\{(.*?)\}\n\\keywords',main,re.S).group(1);wc=len(abs.split())
check('abstract length',150<=wc<=250,wc)
check('keyword count',4<=len(re.search(r'\\keywords\{([^}]+)',main).group(1).split(','))<=6)
check('main iicol',r'\documentclass[pdflatex,iicol,sn-basic,Numbered]' in main)
check('obsolete journal removed','International Journal of Information Technology' not in main+si)
check('no source subfolders',all('/' not in x for x in re.findall(r'\\input\{([^}]+)\}',main+si)))
for name,orig in [('main',oldmain),('supplement',oldsi)]:
 s=(src/(name+'.tex')).read_text();get=lambda t:set(k for m in re.findall(r'\\cite\w*\{([^}]+)\}',t) for k in m.split(','))
 check(name+' citation keys unchanged',get(s)==get(orig))
 labels=[]
 for f in src.glob('*.tex'):
  if f.name in ['authors.tex','declarations.tex','common.tex','Fig1.tex'] or f.stem==name or (name=='supplement' and f.stem not in ['main','supplement']):labels+=re.findall(r'\\label\{([^}]+)',f.read_text())
 check(name+' no duplicate source labels',len(labels)==len(set(labels)))
for name in ['main','supplement','main_anonymous','supplement_anonymous']:
 log=src/'build'/(name+'.log');s=log.read_text(errors='replace')
 check(name+' final log clean',not re.search(r'! |Overfull|undefined|multiply defined|There were undefined',s),{'underfull':s.count('Underfull')})
 check(name+' PDF exists',(src/(name+'.pdf')).is_file())
 b=src/'build'/(name+'.bbl');check(name+' bbl exists',b.is_file())
 if b.exists():check(name+' reference count',len(re.findall(r'\\bibitem',b.read_text()))==(32 if name.startswith('main') else 8),len(re.findall(r'\\bibitem',b.read_text())))
# Authorship/metadata verification uses poppler available with the LaTeX toolchain.
for name in ['main','supplement']:
 info=subprocess.check_output(['pdfinfo',str(src/(name+'.pdf'))]).decode();check(name+' identified PDF author','Soroush Vahidi' in info)
 text=subprocess.check_output(['pdftotext',str(src/(name+'.pdf')),'-']).decode()
 check(name+' identified text',all(x in text for x in ['Soroush Vahidi','sv96@njit.edu','0000-0003-1934-6282']))
 check(name+' no unresolved PDF markers','??' not in text)
for name in ['main_anonymous','supplement_anonymous']:
 info=subprocess.check_output(['pdfinfo',str(src/(name+'.pdf'))]).decode();author=re.search(r'^Author:[ \t]*(.*)$',info,re.M)
 check(name+' blank metadata author',not author or not author.group(1).strip())
 text=subprocess.check_output(['pdftotext',str(src/(name+'.pdf')),'-']).decode()
 check(name+' direct identifiers withheld',all(x not in text for x in ['sv96@njit.edu','0000-0003-1934-6282','SoroushVahidi/','New Jersey Institute of Technology']))
with zipfile.ZipFile(root/'packages/JDSA_sources.zip') as z:
 check('archive flat',all('/' not in n for n in z.namelist()))
 check('archive essential sources',all(x in z.namelist() for x in ['main.tex','supplement.tex','common.tex','authors.tex','declarations.tex','references.bib','sn-jnl.cls','sn-basic.bst','main.pdf','ESM_1.pdf','Fig1.tex','Fig2.pdf','Fig3.pdf','build.sh']))
 check('archive excludes confidential materials',not any('editorial' in n or 'response' in n or 'judgment' in n for n in z.namelist()))
metadata=json.loads((audit/'REFERENCE_METADATA.json').read_text());check('26 DOI identities verified',sum(x.get('http')==200 for x in metadata)==26)
inv=json.loads((audit/'SAVED_INVARIANTS.json').read_text());check('saved scientific invariants',inv['structural_records']==1025 and inv['acyclic']==646 and inv['cyclic']==379 and inv['corrected_comparisons']==35 and inv['corrected_holm_rejections']==0 and inv['independent_query_support_counts']=={'342':28,'290':7} and inv['envelope_graphs']==6)
result={'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','passed':sum(c['pass'] for c in checks),'total':len(checks),'checks':checks,'scientific_analyses_executed':False}
(audit/'DOCUMENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
for c in checks:
 if not c['pass']:print('FAILED',c)
raise SystemExit(result['status']!='PASS')
