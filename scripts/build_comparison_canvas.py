"""Edition 11: display-only predictor families; scientific categories stay intact."""
import json, sys, textwrap
from pathlib import Path
from xml.sax.saxutils import escape as esc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corpus import ROOT, load
from narrow_review import MM, ROWS, INPUTS, SETUPS, OPERATIONS, REP
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, Image
from reportlab.lib.pagesizes import landscape, A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
D=ROOT/'data/comparability'; OUT=ROOT/'output/pdf/narrow'; E=ROOT/'exports/comparability/canvas'; E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'protocols.json').read_text()); R=json.loads((D/'records.json').read_text()); COVER=json.loads((D/'coverage.json').read_text())
PP={p['id']:p for p in P}; CODE={p['id']:f'C{i+1:02}' for i,p in enumerate(P)}
C={'static':('#555555','Граф / размеры'), 'weights':('#8844AA','Только веса'), 'forward':('#53996e','Прямой проход'), 'derivatives':('#D88700','Производные'), 'learned_static':('#a74e69','Предиктор: граф / текст'), 'learned_dynamic':('#685caa','Предиктор: proxy / кривые')}
# Display-only metadata: never used by keep(), rowkeys() or signature().
PREDICTOR_TYPES={
 'trees':{'label':'Деревья и ансамбли деревьев','color':'#0072B2','ids':['M36','M37','M38','M39','M52','M69']},
 'neural_representation':{'label':'Нейросетевые архитектурные представления','color':'#009E73','ids':['M42','M44','M45']},
 'language_model':{'label':'Языковые модели','color':'#303030','ids':['M46','M48']},
}
PREDICTOR_BY_ID={mid:key for key,value in PREDICTOR_TYPES.items() for mid in value['ids']}
def display_color(r):
 key=PREDICTOR_BY_ID.get(r['method_id'])
 return PREDICTOR_TYPES[key]['color'] if key else C[r['category']][0]
def type_cell(mid):
 key=PREDICTOR_BY_ID.get(mid)
 if not key:return 'Формула / дескриптор'
 value=PREDICTOR_TYPES[key]
 label=value['label']+(' (ExtraTrees)' if mid=='M52' else '')
 return '<font color="'+value['color']+'">●</font> '+label
def marked_name(r):
 return '<font color="'+display_color(r)+'">●</font> '+fullname(r)

for n,f in [('CV','DejaVuSans.ttf'),('CV-B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/usr/share/fonts/truetype/dejavu/'+f))
pdfmetrics.registerFontFamily('CV',normal='CV',bold='CV-B',italic='CV',boldItalic='CV-B')
S={k:ParagraphStyle(k,fontName='CV-B' if k=='title' else 'CV',fontSize=v,leading=l,spaceAfter=8) for k,v,l in [('title',24,29),('body',12,17),('cell',11,15),('small',10,14)]}
def para(t,s='body'):return Paragraph(t,S[s])
def tab(rows,widths):
 t=Table([[para(str(c),'cell') for c in row] for row in rows],colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ee')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f1f5f7'),colors.white]),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 return t

def page(story,title,body=''):
 if story:story.append(PageBreak())
 story.append(para(title,'title'))
 if body:story.append(para(body))
def source(p):return '<link color="#286080" href="'+p['url']+'">'+esc(p['paper_id']+' · '+p['locator'])+'</link>'
def footer(c,d):
 c.setFont('CV',9);c.setFillColor(colors.HexColor('#617381'));c.drawString(15*mm,10*mm,'O1-O3 · сравнимость оценщиков · 26.10.2026');c.drawRightString(405*mm,10*mm,str(d.page))
def build(story,filename,title):
 out=OUT/filename
 SimpleDocTemplate(str(out),pagesize=landscape(A3),leftMargin=15*mm,rightMargin=15*mm,topMargin=13*mm,bottomMargin=18*mm,title=title,author='Обзор O1-O3').build(story,onFirstPage=footer,onLaterPages=footer)
 print(out)
def rs(pid):return [r for r in R if r['protocol']==pid]
def fullname(r):return esc(r['method_id']+' · '+r['name'])
def metric(r,k):
 if k not in r['metrics']:return '—'
 v=f"{r['metrics'][k]:.3f}"
 if r.get('sd',{}).get(k) is not None:v+=f" ± {r['sd'][k]:.3f} SD"
 if r.get('se'):v+=f" ± {r['se'][0 if k=='spearman_rho' else 1]:.3f} SE"
 return v

from collections import Counter
def rowkeys(rr):
 counts=Counter(r['method_id'] for r in rr)
 return {(r['method_id'],r['variant'] if counts[r['method_id']]>1 else ''):r for r in rr}

NAMES={'M02':'Decoder parameter count','M03':'FLOPs','M12':'LogSynFlow','M13':'TE-NAS','M15':'EZNAS','M17':'ZiCo','M32':'Dextr','M33':'WRCor','M36':'GRAF + RF','M37':'ZCP + RF','M38':'GRAF + ZCP + RF','M39':'GRAF + ZCP + XGB','M42':'BRP-NAS','M52':'CoRA-Refine','M69':'One-hot + RF','M70':'L2 norm'}

def display(k,r):
 if k[1]:return r['variant'] if r['method_id']=='M46' else 'WRCor voting / '+r['variant'].replace(' (Ours)','')
 return NAMES.get(r['method_id'],r['name'])

def ctxlabel(q):
 pid=q['id']
 if pid=='old_G1':return 'OpenWebText'
 if pid=='old_G2':return 'WikiText-103'
 if pid.startswith('cora_nb201'):return q['title'].split(' / ')[-1]
 if pid.startswith('graf_'):return q['title']
 return q['title']

def grouped_title(qq):
 ids=[q['id'] for q in qq]
 if len(qq)==1:return qq[0]['title'].replace('inputs:','входы:')
 if ids==['old_G1','old_G2']:return 'FlexiBERT / GLUE · OpenWebText и WikiText-103'
 if all(i.startswith('cora_nb201') for i in ids):return 'NAS-Bench-201 · три датасета, общий порядок методов'
 return 'Предикторы по H · совпадающий порядок Kendall'

MARKERS=['o','D','s','^','v','P']

def group_graph(index,qq,keys,metric_name):
 plot_height=max(2.3, min(7.8, .5*len(keys)+.4*len(qq)+1.2))
 fig,ax=plt.subplots(figsize=(7.8,plot_height))
 for j,q in enumerate(qq):
  keyed=rowkeys(rs(q['id']));offset=(j-(len(qq)-1)/2)*min(.15,.5/max(1,len(qq)-1))
  for y,k in enumerate(keys):
   r=keyed[k];v=r['metrics'][metric_name];co=display_color(r)
   sd=r.get('sd',{}).get(metric_name,0)
   if sd:ax.errorbar(v,y+offset,xerr=sd,color=co,capsize=2,lw=1,zorder=2)
   ax.scatter(v,y+offset,s=70,marker=MARKERS[j],color=co,edgecolors='white',linewidths=.5,zorder=3)
   if len(qq)==1:ax.annotate(f'{v:.3f}',(v+sd,y),xytext=(7,0),textcoords='offset points',va='center',fontsize=11)
 ref=rowkeys(rs(qq[0]['id']))
 ax.set_yticks(range(len(keys)),[textwrap.fill(display(k,ref[k]),26) for k in keys],fontsize=12)
 ax.set(xlim=(0,1.13),ylim=(len(keys)-.25,-.75))
 ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
 ax.set_xlabel('Spearman ρ' if metric_name=='spearman_rho' else 'Kendall τ (Spearman не опубликован)',fontsize=12)
 if metric_name=='spearman_rho':ax.axvline(.4,color='#9aa8b1',ls='--',lw=.8)
 if len(qq)>1:
  fig.legend(handles=[Line2D([],[],marker=MARKERS[j],color='#546877',linestyle='none',label=ctxlabel(q)+' ('+CODE[q['id']]+')',markersize=8) for j,q in enumerate(qq)],loc='lower center',ncol=1,frameon=False,fontsize=11)
 fig.tight_layout(rect=[0,(.23*len(qq)+.3)/plot_height if len(qq)>1 else 0,1,1],pad=1.2)
 path=E/f'group_{index:02}.png';fig.savefig(path,dpi=180);fig.savefig(E/f'group_{index:02}.pdf');plt.close(fig)
 return Image(str(path),width=180*mm,height=180*mm)

def group_table(qq,keys):
 mets=[m for m in ['spearman_rho','kendall_tau'] if m in rs(qq[0]['id'])[0]['metrics']]
 n=len(mets);header=['Метод / вариант'];sub=['Полное название'];spans=[]
 for j,q in enumerate(qq):
  at=1+j*n;header += [esc(ctxlabel(q))+'<br/>'+CODE[q['id']]]+['']*(n-1)
  if n>1:spans.append(('SPAN',(at,0),(at+n-1,0)))
  sub += ['Spearman ρ' if m=='spearman_rho' else 'Kendall τ' for m in mets]
 rows=[header,sub];ref=rowkeys(rs(qq[0]['id']))
 for k in keys:
  r=ref[k];name=esc(r['name'])+'<br/><font size="8" color="#617381">'+esc(r['method_id']+(' · '+r['variant'] if k[1] else ''))+'</font>'
  rows.append([name]+[metric(rowkeys(rs(q['id']))[k],m) for q in qq for m in mets])
 style=ParagraphStyle('dense',fontName='CV',fontSize=10.5,leading=13.5)
 widths=[85*mm]+[(135/(len(qq)*n))*mm]*(len(qq)*n)
 t=Table([[Paragraph(str(c),style) for c in row] for row in rows],colWidths=widths,repeatRows=2,hAlign='LEFT')
 t.setStyle(TableStyle(spans+[('SPAN',(0,0),(0,1)),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,1),colors.HexColor('#dce8ee')),('ROWBACKGROUNDS',(0,2),(-1,-1),[colors.HexColor('#f1f5f7'),colors.white]),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
 return t


from reportlab.pdfgen import canvas
from pypdf import PdfReader,PdfWriter,Transformation
from io import BytesIO
from math import ceil
base=ROOT/'exports/comparability/predictor_types'
original=json.loads((base/'global_filtered_registry.json').read_text())
oldgroups=json.loads((base/'grouped_registry.json').read_text())['groups']
excluded_ids=set(PREDICTOR_TYPES['language_model']['ids'])
R=[r for r in original['records'] if PP[r['protocol']]['tier']!='auxiliary' and r['method_id'] not in excluded_ids]
groups=[{'contexts':[PP[p] for p in g['protocols'] if rs(p)]} for g in oldgroups]
groups=[g for g in groups if g['contexts']]
W,H=420*mm,270*mm
panel_files=[]
panel_heights=[]
for index,g in enumerate(groups,1):
 qq=g['contexts'];ref=rowkeys(rs(qq[0]['id']))
 metric_name='spearman_rho' if 'spearman_rho' in next(iter(ref.values()))['metrics'] else 'kendall_tau'
 keys=sorted(ref,key=lambda k:(-ref[k]['metrics'][metric_name],k))
 group_graph(index,qq,keys,metric_name)
 graph=PdfReader(E/f'group_{index:02}.pdf').pages[0]
 gh=180*mm*float(graph.mediabox.height)/float(graph.mediabox.width)
 t=group_table(qq,keys);_,th=t.wrap(220*mm,270*mm)
 title=' / '.join(CODE[q['id']] for q in qq)+' · '+esc(grouped_title(qq))
 desc='<br/>'.join('<b>'+esc(ctxlabel(q))+'</b>: '+esc(q['target'])+'; '+esc(str(q['sample'])) for q in qq)
 headh=sum(Paragraph(txt,ParagraphStyle('measure',fontName='CV',fontSize=size,leading=size*1.35)).wrap(404*mm,270*mm)[1]+5 for txt,size in [(title,16),(desc,10)])
 H=8*mm+headh+2*mm+max(gh,th)+18*mm
 panel_heights.append(H)
 buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(W,H))
 def paragraph(text,x,y,w,size=10):
  p=Paragraph(text,ParagraphStyle('panel',fontName='CV',fontSize=size,leading=size*1.35))
  _,h=p.wrap(w,H);p.drawOn(c,x,y-h);return y-h-5
 y=H-8*mm
 y=paragraph(' / '.join(CODE[q['id']] for q in qq)+' · '+esc(grouped_title(qq)),8*mm,y,404*mm,16)
 desc='<br/>'.join('<b>'+esc(ctxlabel(q))+'</b>: '+esc(q['target'])+'; '+esc(str(q['sample'])) for q in qq)
 y=paragraph(desc,8*mm,y,404*mm,10)
 graph_top=y-2*mm;graph_bottom=graph_top-gh
 t=group_table(qq,keys);_,th=t.wrap(220*mm,H)
 assert graph_bottom>16*mm and graph_top-th>16*mm,(index,graph_bottom,th)
 t.drawOn(c,192*mm,graph_top-th)
 sources=list({(q['url'],q['locator']):q for q in qq}.values())
 paragraph('Источники: '+'; '.join(source(q) for q in sources),8*mm,12*mm,404*mm,10)
 c.showPage();c.save()
 panel=PdfReader(buffer).pages[0];graph=PdfReader(E/f'group_{index:02}.pdf').pages[0]
 scale=180*mm/float(graph.mediabox.width)
 panel.merge_transformed_page(graph,Transformation().scale(scale).translate(8*mm,graph_bottom))
 writer=PdfWriter();writer.add_page(panel);path=E/f'panel_{index:02}.pdf'
 with path.open('wb') as f:writer.write(f)
 panel_files.append(path)
# One vector canvas: preserve each panel's original reading scale.
margin=10*mm;gap=0*mm;header=0*mm;cols=2;rows=ceil(len(groups)/cols)
column_heights=[sum(panel_heights[col::2]) for col in range(2)]
CW=2*W+2*margin+gap;CH=header+max(column_heights)+2*margin
buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(CW,CH))
c.setTitle('Оценщики O1-O3 · единый холст без языковых моделей · версия 12')
# The shorter right column leaves room for the common heading and legend.
hx=margin+W+8*mm;hy=CH-margin-8*mm;hw=W-16*mm
header_bottom=margin+column_heights[1]
def header_paragraph(text,size=12,leading=16,bold=False):
 global hy
 p=Paragraph(text,ParagraphStyle('header',fontName='CV-B' if bold else 'CV',fontSize=size,leading=leading))
 _,height=p.wrap(hw,300);p.drawOn(c,hx,hy-height);hy-=height+6
header_paragraph('Оценщики O1-O3 · сравнения C01–C28<br/>Без языковых моделей',20,25,True)
header_paragraph('Глобальный фильтр версии 11 сохранён. Маркеры обозначают контексты; цвет — категорию. Значения не усредняются. Интервалы на графиках — SD повторов.')
legend=[('Граф / размеры',C['static'][0]),('Только веса',C['weights'][0]),('Производные',C['derivatives'][0]),('Деревья и ансамбли деревьев','#0072B2'),('Нейросетевые архитектурные представления','#009E73')]
for j,(name,col) in enumerate(legend):
 x=hx+(j%2)*(hw/2);y=hy-12-(j//2)*18
 c.setFillColor(colors.HexColor(col));c.circle(x+3,y+3,3,fill=1,stroke=0)
 c.setFillColor(colors.HexColor('#263743'));c.setFont('CV',12);c.drawString(x+12,y,name)
hy-=3*18+5
header_paragraph('Цвет / категория: семейство оценщика или род вычислений; одинаковый цвет не означает одинаковую стоимость. C08–C14 отсутствуют после глобального фильтра.',10,14)
assert hy>=header_bottom+4*mm,(hy,header_bottom)
for i in range(len(groups)):
 x=margin+(i%2)*(W+gap);y=margin+column_heights[i%2]-sum(panel_heights[i%2:i:2])-panel_heights[i]
 c.setStrokeColor(colors.HexColor('#cbd5db'));c.rect(x,y,W,panel_heights[i],stroke=1,fill=0)
c.showPage();c.save();sheet=PdfReader(buffer).pages[0]
for i,path in enumerate(panel_files):
 x=margin+(i%2)*(W+gap);y=margin+column_heights[i%2]-sum(panel_heights[i%2:i:2])-panel_heights[i]
 sheet.merge_transformed_page(PdfReader(path).pages[0],Transformation().translate(x,y))
writer=PdfWriter();writer.add_page(sheet)
out=OUT/'12_comparison_canvas.pdf'
with out.open('wb') as f:writer.write(f)
manifest={'records':R,'excluded_category':'language_model','excluded_method_ids':sorted(excluded_ids),'groups':[{'protocols':[q['id'] for q in g['contexts']]} for g in groups],'pages':1,'size_mm':[CW/mm,CH/mm],'panels':len(groups),'panel_heights_mm':[h/mm for h in panel_heights]}
(E/'canvas_registry.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(out);print(json.dumps({'records':len(R),'methods':len({r['method_id'] for r in R}),'panels':len(groups),'size_mm':manifest['size_mm']}))
