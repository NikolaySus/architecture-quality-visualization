"""Build the complete design contact sheet and inspectable evidence exports."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw
from variant_charts import CANDIDATES
from charts import export
from corpus import ROOT
out=ROOT/'exports/variants';out.mkdir(parents=True,exist_ok=True)
manifest=[]
for name,fn in CANDIDATES.items():
 fig,records=fn()
 for fmt in ['png','svg','pdf']:(out/(name+'.'+fmt)).write_bytes(export(fig,fmt))
 (out/(name+'.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 plt.close(fig)
 manifest.append(dict(id=name,records=len(records),figure=str(out/(name+'.pdf'))))
 print(name,len(records),flush=True)
(out/'experiments.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for start in range(0,len(manifest),6):
 sheet=Image.new('RGB',(1500,1250),'#ddd');draw=ImageDraw.Draw(sheet)
 for j,item in enumerate(manifest[start:start+6]):
  im=Image.open(out/(item['id']+'.png'));im.thumbnail((740,390));x=j%2*750;y=j//2*415
  sheet.paste(im,(x,y+22));draw.text((x+5,y+4),item['id'],fill='black')
 sheet.save(out/f'contact-{start}.png')
