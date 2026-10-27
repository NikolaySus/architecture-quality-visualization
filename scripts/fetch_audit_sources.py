"""Download specific primary sources for a reproducible access-requirements audit."""
import concurrent.futures, hashlib, io, json, re, sys
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
import requests
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
    def __init__(self): super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ['script','style']: self.skip+=1
        if t in ['p','h1','h2','h3','h4','tr','li','section']: self.parts.append('\n')
    def handle_endtag(self,t):
        if t in ['script','style']: self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)
SOURCES={
'P01':'https://arxiv.org/html/2101.08134',
'P06':'https://arxiv.org/html/2102.11535',
'P08':'https://arxiv.org/html/2209.07413',
'P09':'https://arxiv.org/html/2207.05135v2',
'P11':'https://openaccess.thecvf.com/content/CVPR2024/papers/Lee_AZ-NAS_Assembling_Zero-Cost_Proxies_for_Network_Architecture_Search_CVPR_2024_paper.pdf',
'P12':'https://arxiv.org/html/2404.16551v2',
'P13':'https://arxiv.org/html/2403.02484v1',
'P20':'https://arxiv.org/html/1705.10823',
'P21':'https://aaronkl.github.io/assets/pdf/lcnet.pdf',
'P22':'https://www.ijcai.org/Proceedings/15/Papers/487.pdf',
'P24':'https://arxiv.org/html/2104.01177',
'P25':'https://arxiv.org/html/2111.03602',
'P27':'https://aclanthology.org/2023.acl-long.142.pdf',
'P28':'https://aclanthology.org/2024.findings-emnlp.502.pdf',
'P29':'https://arxiv.org/html/2503.18646v1',
'P30':'https://arxiv.org/html/2203.12217',
'P31':'https://www.jdl.link/doc/2011/20241226_10_Training-Free_Transformer_Architecture_Search_With_Zero-Cost_Proxy_Guided_Evolution.pdf',
'P33':'https://arxiv.org/html/2402.02105',
'P35':'https://arxiv.org/html/2605.15649v1',
'P36':'https://openaccess.thecvf.com/content/CVPR2026/papers/Zhou_InTrain_Intrinsic_Trainability_for_Zero-Cost_Neural_Architecture_Search_CVPR_2026_paper.pdf',
'P37':'https://arxiv.org/html/2609.14184',
'P38':'https://arxiv.org/html/2609.11884',
'P39':'https://arxiv.org/html/2001.08361',
'P40':'https://arxiv.org/html/2203.15556',
'P41':'https://aclanthology.org/2023.findings-emnlp.825.pdf',
'P42':'https://aclanthology.org/2024.emnlp-main.319.pdf',
'P43':'https://aclanthology.org/2020.acl-main.686.pdf',
'P44':'https://aclanthology.org/2021.acl-long.400.pdf',
'P45':'https://arxiv.org/html/2110.13100',
'P46':'https://arxiv.org/html/2210.03230v1',
'P47':'https://link.springer.com/article/10.1007/s11263-024-02265-7',
'P50':'https://arxiv.org/html/2507.08841',
}
def get(item):
    pid,url=item; dest=ROOT/'tmp/source_audit'/pid; record={'paper_id':pid,'requested_url':url,'accessed_at':datetime.now(timezone.utc).isoformat()}
    try:
        r=requests.get(url,timeout=30);record.update(status_code=r.status_code,resolved_url=r.url)
        r.raise_for_status(); raw=r.content
        if raw.startswith(b'%PDF'):
            txt='\n'.join(f'\nPDF PAGE {i+1}\n'+p.extract_text() for i,p in enumerate(PdfReader(io.BytesIO(raw)).pages));ext='.pdf'
        else:
            parser=Text();parser.feed(r.text);txt='\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip());ext='.html'
        if len(txt.strip()) < 200: raise ValueError('Empty or unusable source text')
        dest.with_suffix(ext).write_bytes(raw);dest.with_suffix('.txt').write_text(txt)
        record.update(sha256=hashlib.sha256(raw).hexdigest(),text_chars=len(txt),local_text=str(dest.with_suffix('.txt').relative_to(ROOT)),status='downloaded')
        versions=re.findall(r'arXiv:\s*(\d{4}\.\d{4,5}v\d+)',txt)
        record['source_version']=versions[0] if versions else 'official_pdf' if ext=='.pdf' else 'version_not_detected'
    except Exception as e:record.update(status='failed',error=str(e))
    print(pid,record['status'],record.get('text_chars',record.get('error')),flush=True)
    return record
if __name__ == '__main__':
    selected={k:v for k,v in SOURCES.items() if not sys.argv[1:] or k in sys.argv[1:]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: records=list(pool.map(get,selected.items()))
    target=ROOT/'data/source_audit/downloads.json'
    prior=json.loads(target.read_text()) if target.exists() else []
    target.write_text(json.dumps([r for r in prior if r['paper_id'] not in selected]+records,ensure_ascii=False,indent=2)+'\n')
