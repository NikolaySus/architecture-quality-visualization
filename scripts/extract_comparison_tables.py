"""Readable snapshots of primary-source HTML tables, with immutable file hashes."""
from pathlib import Path
import json,hashlib
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'tmp/comparability';out.mkdir(exist_ok=True)
index=[]
for folder in ['tmp/source_audit','tmp/narrow_sources']:
 for path in sorted((ROOT/folder).glob('P*.html')):
  soup=BeautifulSoup(path.read_text(),'html.parser')
  for math in soup.find_all('math'):
   math.replace_with(math.get('alttext') or math.get_text(' ',strip=True))
  for ann in soup.find_all('annotation'):ann.decompose()
  tables=[]
  for table in soup.find_all('table'):
   if table.find_parent('table'):continue
   parent=table.find_parent('figure')
   caption=parent.find('figcaption') if parent else None
   if not caption:continue
   rows=[]
   for tr in table.find_all('tr'):
    cells=tr.find_all(['th','td'],recursive=False)
    if cells:rows.append([' '.join(td.get_text(' ',strip=True).split()) for td in cells])
   tables.append({'id':parent.get('id'),'caption':caption.get_text(' ',strip=True),'rows':rows})
  record={'source':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tables':tables}
  target=out/(path.stem+'_'+path.parent.name+'_tables.json');target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
  text='\n\n'.join(t['id']+' '+t['caption']+'\n'+'\n'.join(' | '.join(r) for r in t['rows']) for t in tables)
  target.with_suffix('.txt').write_text(text)
  index.append({'paper':path.stem,'file':str(target.relative_to(ROOT)),'tables':len(tables)})
(out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
print('Extracted',sum(i['tables'] for i in index),'tables from',len(index),'cached primary sources')
