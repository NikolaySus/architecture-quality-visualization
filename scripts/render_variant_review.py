"""Render every delivered variant and generate contact sheets for visual QA."""
import subprocess,concurrent.futures
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
def render(pdf):
 out=ROOT/'tmp/pdfs/variants'/pdf.stem;out.mkdir(parents=True,exist_ok=True)
 for pattern in ['page-*.png','contact-*.png']:
  for old in out.glob(pattern):old.unlink()
 subprocess.run(['pdftoppm','-scale-to','1100','-png',str(pdf),str(out/'page')],check=True)
 files=sorted(out.glob('page-*.png'))
 for start in range(0,len(files),12):
  im=Image.new('RGB',(1500,1080),'#ddd');d=ImageDraw.Draw(im)
  for j,p in enumerate(files[start:start+12]):
   pic=Image.open(p);pic.thumbnail((490,245));x=j%3*500;y=j//3*270;im.paste(pic,(x,y+18));d.text((x+5,y+2),p.stem,fill='black')
  im.save(out/f'contact-{start}.png')
 return pdf.name,len(files)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for result in pool.map(render,sorted((ROOT/'output/pdf/variants').glob('*.pdf'))): print(result,flush=True)
