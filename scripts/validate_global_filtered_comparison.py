"""Check exact selection, numerical coverage and layout bounds of the filtered PDF."""
import json,subprocess,hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'data/comparability/records.json').read_text())
ps=json.loads((ROOT/'data/comparability/protocols.json').read_text());codes={p['id']:f'C{i+1:02}' for i,p in enumerate(ps)}
f=json.loads((ROOT/'exports/comparability/global_filtered/global_filtered_registry.json').read_text())
bad_ids={r['method_id'] for r in source if r['metrics'].get('spearman_rho',1)<.4}
expected=[r for r in source if r['category']!='forward' and r['method_id'] not in bad_ids]
assert set(f['filter']['excluded_method_ids'])==bad_ids
assert f['records']==expected
assert len(f['removed'])+len(expected)==len(source)
assert all(r['category']!='forward' for r in expected)
assert any('spearman_rho' not in r['metrics'] for r in expected)
assert not any(r['protocol']=='old_G1' and r['method_id']=='M25' for r in expected)
assert not any(r['method_id'] in {'M01','M25','M51','M18'} for r in expected)
assert all(not any(x['method_id']==r['method_id'] and x['metrics'].get('spearman_rho',1)<.4 for x in source) for r in expected)
assert any(r['method_id']=='M69' and r['metrics'].get('kendall_tau')==.24 for r in expected)
file=ROOT/'output/pdf/narrow/09_global_filtered_combined.pdf';pdf=PdfReader(file);texts=[p.extract_text() for p in pdf.pages]
for r in expected:
 hit=[t for t in texts if codes[r['protocol']]+' · ' in t and r['method_id'] in t]
 assert any(all(f'{v:.3f}' in t for v in r['metrics'].values()) for t in hit),r
xml=subprocess.check_output(['/usr/bin/pdftotext','-bbox',str(file),'-']);bad=[]
for i,p in enumerate(ET.fromstring(xml).findall('.//{*}page')):
 w,h=float(p.attrib['width']),float(p.attrib['height'])
 for x in p.findall('.//{*}word'):
  a=x.attrib
  if float(a['xMin'])<0 or float(a['yMin'])<0 or float(a['xMax'])>w+.1 or float(a['yMax'])>h+.1:bad.append((i+1,x.text))
assert not bad,bad
result={'pages':len(pdf.pages),'retained_records':len(expected),'primary_method_count':len(f['primary_method_ids']),'filter_exact_match':True,'numbers_in_correct_context':True,'text_bounds':'pass','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(ROOT/'output/global_filtered_comparison_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
