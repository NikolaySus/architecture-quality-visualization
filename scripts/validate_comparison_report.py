"""Validate numeric/context coverage and PDF page bounds after rendering."""
import json,subprocess,hashlib,re
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/comparability';OUT=ROOT/'output/pdf/narrow'
P=json.loads((D/'protocols.json').read_text());R=json.loads((D/'records.json').read_text());C=json.loads((D/'coverage.json').read_text())
code={p['id']:f'C{i+1:02}' for i,p in enumerate(P)}
report={}
for name in ['06_promising_methods','07_comparability_tables']:
 path=OUT/(name+'.pdf');pdf=PdfReader(path);texts=[p.extract_text() for p in pdf.pages]
 assert all(len(t)>160 for t in texts)
 xml=subprocess.check_output(['/usr/bin/pdftotext','-bbox',str(path),'-'])
 tree=ET.fromstring(xml);bad=[]
 for i,page in enumerate(tree.findall('.//{*}page')):
  w,h=float(page.attrib['width']),float(page.attrib['height'])
  for word in page.findall('.//{*}word'):
   a=word.attrib
   if float(a['xMin'])<0 or float(a['yMin'])<0 or float(a['xMax'])>w+.1 or float(a['yMax'])>h+.1:bad.append((i+1,word.text))
 assert not bad,bad
 report[name]={'pages':len(pdf.pages),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'text_bounds':'pass','links':sum(len(p.get('/Annots',[])) for p in pdf.pages)}
 if name=='07_comparability_tables':
  full=' '.join(texts)
  for c in C:assert c['method_id'] in full and c['name'] in re.sub(r'\s+',' ',full),(c['method_id'],c['name'])
  for r in R:
   hits=[t for t in texts if code[r['protocol']]+' · ' in t and r['method_id'] in t]
   assert any(all(f'{v:.3f}' in t for v in r['metrics'].values()) for t in hits),r
  report[name]['numeric_records_checked']=len(R)
  report[name]['method_names_checked']=len(C)
(ROOT/'output/comparison_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
