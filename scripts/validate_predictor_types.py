"""Check exact selection, numerical coverage and layout bounds of the filtered PDF."""
import json,subprocess,hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
from report_runtime import pdftotext_path
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'data/comparability/records.json').read_text())
ps=json.loads((ROOT/'data/comparability/protocols.json').read_text());codes={p['id']:f'C{i+1:02}' for i,p in enumerate(ps)}
f=json.loads((ROOT/'exports/comparability/predictor_types/global_filtered_registry.json').read_text())
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
from collections import Counter
registry=json.loads((ROOT/'exports/comparability/predictor_types/grouped_registry.json').read_text())
assert registry['records']==expected
primary_pids=[p['id'] for p in ps if p['tier']!='auxiliary' and any(r['protocol']==p['id'] for r in expected)]
assert Counter(x for g in registry['groups'] for x in g['protocols'])==Counter(primary_pids)
def sig(pid):
 rr=[r for r in expected if r['protocol']==pid];counts=Counter(r['method_id'] for r in rr);out=[]
 for m in sorted({m for r in rr for m in r['metrics']}):
  vals={}
  for r in rr:vals.setdefault(r['metrics'][m],[]).append((r['method_id'],r['variant'] if counts[r['method_id']]>1 else ''))
  out.append((m,tuple(tuple(sorted(vals[v])) for v in sorted(vals,reverse=True))))
 return tuple(out)
assert len(registry['groups'])==11
for g in registry['groups']:assert len({sig(pid) for pid in g['protocols']})==1
assert any(g['protocols']==['old_G1','old_G2'] for g in registry['groups'])
assert next(g for g in registry['groups'] if 'graf_NAS-Bench-201_ImageNet16-120_1024' in g['protocols'])['protocols']==['graf_NAS-Bench-201_ImageNet16-120_1024']
# Display metadata must not affect scientific records, grouping or filtering.
old_registry=json.loads((ROOT/'exports/comparability/grouped/grouped_registry.json').read_text())
assert registry==old_registry
assert f==json.loads((ROOT/'exports/comparability/grouped/global_filtered_registry.json').read_text())
display=json.loads((ROOT/'exports/comparability/predictor_types/display_categories.json').read_text())
color_sets={
 'trees':('#A74E69',{'M36','M37','M38','M39','M52','M69'}),
 'neural_representation':('#D94701',{'M42','M44','M45'}),
 'language_model':('#303030',{'M46','M48'}),
}
colors_by_id={mid:(k,col) for k,(col,ids) in color_sets.items() for mid in ids}
original_colors={'static':'#487b9e','weights':'#8e69a4','derivatives':'#c58b38'}
assert len(display['records'])==100
assert {r['method_id'] for r in expected if r['category'].startswith('learned')}==set(colors_by_id)
for r,d in zip(expected,display['records']):
 assert (r['protocol'],r['method_id'],r['variant'],r['category'])==(d['protocol'],d['method_id'],d['variant'],d['source_category'])
 assert (d['display_category'],d['color'])==colors_by_id.get(r['method_id'],(r['category'],original_colors.get(r['category'])))
from PIL import Image,ImageColor
for i,g in enumerate(registry['groups'],1):
 pixels=Counter(Image.open(ROOT/f'exports/comparability/predictor_types/group_{i:02}.png').convert('RGB').getdata())
 colors={d['color'] for d in display['records'] if d['protocol'] in g['protocols']}
 assert all(pixels[ImageColor.getrgb(c)]>5 for c in colors),(i,colors)
 assert pixels[ImageColor.getrgb('#685caa')]==0
# Prior edition remains byte-for-byte intact.
old_pdf=ROOT/'output/pdf/narrow/10_grouped_comparisons.pdf'
assert hashlib.sha256(old_pdf.read_bytes()).hexdigest()==json.loads((ROOT/'output/grouped_comparison_validation.json').read_text())['sha256']
file=ROOT/'output/pdf/narrow/11_predictor_types.pdf';pdf=PdfReader(file);texts=[p.extract_text() for p in pdf.pages]
assert len(pdf.pages) in [26,27]
assert 'ExtraTrees' in ''.join(texts)
assert 'Тип оценщика' in ''.join(texts)
for r in expected:
 hit=[t for t in texts if codes[r['protocol']] in t and r['method_id'] in t]
 assert any(all(f'{v:.3f}' in t for v in r['metrics'].values()) for t in hit),r
xml=subprocess.check_output([pdftotext_path(),'-bbox',str(file),'-']);bad=[]
for i,p in enumerate(ET.fromstring(xml).findall('.//{*}page')):
 w,h=float(p.attrib['width']),float(p.attrib['height'])
 for x in p.findall('.//{*}word'):
  a=x.attrib
  if float(a['xMin'])<0 or float(a['yMin'])<0 or float(a['xMax'])>w+.1 or float(a['yMax'])>h+.1:bad.append((i+1,x.text))
assert not bad,bad
result={'pages':len(pdf.pages),'retained_records':len(expected),'primary_method_count':len(f['primary_method_ids']),'groups':len(registry['groups']),'same_orders_including_ties':True,'scientific_data_unchanged':True,'display_colors_checked':True,'version_10_unchanged':True,'filter_exact_match':True,'numbers_in_correct_context':True,'text_bounds':'pass','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(ROOT/'output/predictor_types_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
