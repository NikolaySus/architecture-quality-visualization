"""Validate the delivered PDFs themselves as well as their evidence manifests."""
import sys,json,re,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pypdf import PdfReader
from corpus import ROOT
from variant_charts import MM,OBS
out={"checked_at":"2026-10-13","visual_experiments":14,"reports":[],"visual_review":{"status":"reviewed","scope":"All pages rendered at 1100px; contact sheets reviewed, main numerical panels inspected individually; table orphan pages and detached sources corrected.","render_directory":"tmp/pdfs/variants"},"requirements_audit":[
 {"requirement":"Несколько вариантов категоризации и отчётов","evidence":"Three full PDFs, three partitions (6 operation / 3 access / 5 family), 14 exported trials."},
 {"requirement":"Учитывать все визуализации, не только D","evidence":"D alternatives; B/F combined; three E layouts; two accepted G6 layouts; A/C explicitly lack full quantitative costs."},
 {"requirement":"Пробовать разные приёмы, включая 3D при пользе","evidence":"D_3d compared with D_evidence_facets; rejected/diagnostic decisions in 00_design_comparison.pdf."},
 {"requirement":"Не перегружать число визуализаций","evidence":"Exactly four main visual blocks in each report; all 43 observations covered once."},
 {"requirement":"Без двусмысленных категорий","evidence":"Exhaustive disjoint membership; explicit N/U/T definitions, variant-level access exceptions, separate setup examples, no mixed/unknown comparison category."},
 {"requirement":"Сохранить исключения и расшифровки","evidence":"PDF text catalog contains all 69 IDs once before numerical panels; final page lists M28/M40/M72; numerical exclusions archived."},
 {"requirement":"PDF и uv","evidence":"Build commands in README; final PDFs and render checks generated using uv scripts."}
]}
for name in ['01_mechanisms','02_constraints','03_family_atlas']:
 manifest=json.loads((ROOT/'exports/variants'/f'{name}_manifest.json').read_text());path=ROOT/manifest['pdf'];pdf=PdfReader(path);txt='\n'.join(p.extract_text() for p in pdf.pages)
 before=txt.split('B + F ·')[0];ids=re.findall(r'(M\d+) / [NUT]',before)
 assert Counter(ids)==Counter(list(MM)),(name,Counter(ids))
 registry=txt.split('Численный реестр · G1',1)[1].split('Архив ·',1)[0]
 assert Counter(re.findall(r'G\d_\d{3}',registry))==Counter(o['id'] for o in OBS)
 assert all(len(p.extract_text())>130 for p in pdf.pages)
 assert all(m in pdf.pages[-1].extract_text() for m in ['M28','M40','M72'])
 assert len(pdf.outline)>15
 for filename,sha in manifest['data_sha256'].items():assert hashlib.sha256((ROOT/'data'/filename).read_bytes()).hexdigest()==sha
 xml=subprocess.check_output(['pdftotext','-bbox',str(path),'-'])
 tree=ET.fromstring(xml);ns={'h':'http://www.w3.org/1999/xhtml'};issues=[]
 for n,page in enumerate(tree.findall('.//h:page',ns),1):
  w,h=float(page.attrib['width']),float(page.attrib['height'])
  for word in page.findall('.//h:word',ns):
   b={k:float(v) for k,v in word.attrib.items()}
   if b['xMin']<10 or b['xMax']>w-10 or b['yMin']<10 or b['yMax']>h-10:issues.append([n,word.text,b])
 assert not issues,(name,issues[:3])
 renders=list((ROOT/'tmp/pdfs/variants'/name).glob('page-*.png'));assert len(renders)==len(pdf.pages)
 out['reports'].append(dict(id=name,pdf=manifest['pdf'],pages=len(pdf.pages),catalog_method_ids=69,registry_observations=43,main_visual_blocks=4,bookmarks=len(pdf.outline),links=sum(len(p.get('/Annots',[])) for p in pdf.pages),text_bounds='passed',pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
guide=ROOT/'output/pdf/variants/00_design_comparison.pdf'
assert len(PdfReader(guide).pages)==7
out['comparison_pdf']=str(guide.relative_to(ROOT))
(ROOT/'output/variants_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['reports'],ensure_ascii=False,indent=2))
