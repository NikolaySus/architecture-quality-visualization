"""Render the deliverables and check corpus, PDF and export invariants."""
import sys,json,subprocess,concurrent.futures,hashlib,re
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
from pypdf import PdfReader
from corpus import ROOT,load
from narrow_review import CONFIGS,MM,OBS,ROWS,cells,feature_profiles

def render(pdf):
 out=ROOT/'tmp/pdfs/narrow'/pdf.stem;out.mkdir(parents=True,exist_ok=True)
 for pattern in ['page-*.png','contact-*.png']:
  for p in out.glob(pattern):p.unlink()
 subprocess.run(['pdftoppm','-scale-to','1400','-png',str(pdf),str(out/'page')],check=True)
 pages=sorted(out.glob('page-*.png'))
 for start in range(0,len(pages),6):
  sheet=Image.new('RGB',(1600,1740),'#dce0e3');d=ImageDraw.Draw(sheet)
  for j,p in enumerate(pages[start:start+6]):
   im=Image.open(p);im.thumbnail((790,548));x=j%2*800;y=j//2*580
   sheet.paste(im,(x,y+22));d.text((x+6,y+4),pdf.stem+' '+p.stem,fill='black')
  sheet.save(out/f'contact-{start:02d}.png')
 subprocess.run(['pdftotext','-bbox',str(pdf),str(out/'bbox.html')],check=True)
 tree=ET.parse(out/'bbox.html');violations=[]
 for n,p in enumerate(tree.iter('{http://www.w3.org/1999/xhtml}page'),1):
  w,h=float(p.attrib['width']),float(p.attrib['height'])
  for word in p.iter('{http://www.w3.org/1999/xhtml}word'):
   a=word.attrib
   if float(a['xMin'])<0 or float(a['xMax'])>w or float(a['yMin'])<0 or float(a['yMax'])>h:violations.append([n,word.text])
 assert not violations,(pdf.name,violations)
 reader=PdfReader(pdf)
 assert len(pages)==len(reader.pages)
 return dict(pdf=pdf.name,pages=len(pages),bounds_violations=violations,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())

def validate():
 raw={o['id']:o for o in load('observations')}
 for cfg in CONFIGS:
  name=cfg['id'];manifest=json.loads((ROOT/'exports/narrow'/f'{name}_manifest.json').read_text())
  for filename,digest in manifest['inputs_sha256'].items():
   assert hashlib.sha256((ROOT/'data'/filename).read_bytes()).hexdigest()==digest
  assert Counter(manifest['method_ids'])==Counter(list(MM))
  assert Counter(mid for c in cells(cfg) for mid in c['method_ids'])==Counter(list(MM))
  assert Counter(mid for _,ids in feature_profiles(cfg)[1] for mid in ids)==Counter(list(MM))
  records=[]
  for suffix in ['BF','E','G6']:records+=json.loads((ROOT/'exports/narrow'/f'{name}_{suffix}.json').read_text())
  assert Counter(o['id'] for o in records)==Counter(o['id'] for o in OBS)
  assert all(o==raw[o['id']] for o in records)
  from narrow_review import access
  assert manifest['observation_access']=={o['id']:access(o,MM) for o in OBS}
  reader=PdfReader(ROOT/manifest['pdf']);texts=[p.extract_text() for p in reader.pages];text='\n'.join(texts)
  catalog=text.split('Расшифровка точек · полные названия методов',1)[1].split('Состав признаков · проверка выбранных осей',1)[0]
  # IDs in cell descriptions may repeat; every method has a full name in the PDF catalog.
  for mid,m in MM.items():assert mid in catalog and m['name'].replace('`','') in catalog.replace('`','').replace('\n',' '),(name,mid)
  assert 'Методы, не поддающиеся анализу' in texts[-1]
  assert all(len(t)>130 for t in texts)
  for o in OBS:assert o['id'] in text
  assert len(reader.outline)>10
  assert sum(len(p.get('/Annots',[])) for p in reader.pages)>30
 assert len(MM)==len(ROWS)==56 and len(OBS)==43
 assert all(r['status']=='included' and r['evidence'] for r in ROWS.values())

if __name__=='__main__':
 validate()
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  results=list(pool.map(render,sorted((ROOT/'output/pdf/narrow').glob('*.pdf'))))
 payload=dict(status='passed',methods=56,observations=43,checks=['scope partitions','source-backed categories','unchanged numeric records','full catalog names','PDF bounds','links and outlines','all pages rendered'],pdfs=results)
 (ROOT/'output/narrow_validation.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(payload,ensure_ascii=False,indent=2))
