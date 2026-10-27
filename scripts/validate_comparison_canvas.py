"""Validate the single-sheet comparison export against edition 11."""
import json, hashlib, subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'exports/comparability/predictor_types';out=ROOT/'exports/comparability/canvas'
old=json.loads((base/'global_filtered_registry.json').read_text())
ps=json.loads((ROOT/'data/comparability/protocols.json').read_text());pp={p['id']:p for p in ps}
expected=[r for r in old['records'] if pp[r['protocol']]['tier']!='auxiliary' and r['method_id'] not in {'M46','M48'}]
a=json.loads((out/'canvas_registry.json').read_text());assert a['records']==expected
assert len(expected)==85 and len({r['method_id'] for r in expected})==17
og=json.loads((base/'grouped_registry.json').read_text())['groups']
assert [g['protocols'] for g in a['groups']]==[g['protocols'] for g in og]
assert len(a['groups'])==11
pdf=ROOT/'output/pdf/narrow/12_comparison_canvas.pdf';pages=PdfReader(pdf).pages;assert len(pages)==1
text=pages[0].extract_text()
for bad in ['M46','M48','ModernBERT','RoBERTa','Llama','C29','C30']:assert bad not in text,bad
for i,g in enumerate(a['groups'],1):
 t=PdfReader(out/f'panel_{i:02}.pdf').pages[0].extract_text()
 for r in expected:
  if r['protocol'] not in g['protocols']:continue
  assert r['method_id'] in t
  for v in r['metrics'].values():assert f'{v:.3f}' in t,(i,r)
xml=subprocess.check_output(['/usr/bin/pdftotext','-bbox',str(pdf),'-'])
for p in ET.fromstring(xml).findall('.//{*}page'):
 w,h=float(p.attrib['width']),float(p.attrib['height'])
 for x in p.findall('.//{*}word'):
  b=x.attrib;assert float(b['xMin'])>=0 and float(b['yMin'])>=0 and float(b['xMax'])<=w+.1 and float(b['yMax'])<=h+.1,x.text
oldpdf=ROOT/'output/pdf/narrow/11_predictor_types.pdf'
assert hashlib.sha256(oldpdf.read_bytes()).hexdigest()==json.loads((ROOT/'output/predictor_types_validation.json').read_text())['sha256']
result={'pages':1,'panels':11,'records':85,'methods':17,'numbers_checked':True,'text_bounds':'pass','version_11_unchanged':True,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}
(ROOT/'output/comparison_canvas_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
