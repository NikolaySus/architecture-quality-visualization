"""Alternative visual encodings over the same audited corpus; no metric fitting."""
from collections import Counter
import textwrap
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from corpus import load, comparison_methods, exclusion_reason, access, metric
from charts import dot, report_family_groups
TAX=load('visualization_taxonomies')
OPS=TAX['operation_groups']; ACC=TAX['access_groups']; AK=[a['key'] for a in ACC]
ACODE={a['key']:a['id'] for a in ACC}
COLORS=['#8996a4','#438da3','#c38c43']
PALE=['#eef0f3','#eaf5f6','#fff4e4']
METHODS=comparison_methods(); MM={m['id']:m for m in METHODS}
OP={mid:g['id'] for g in OPS for mid in g['ids']}
OBS=[o for o in load('observations') if exclusion_reason(o) is None]
FIGS={}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})

def frame(w=11.8,h=5.9):
 fig,ax=plt.subplots(figsize=(w,h));return fig,ax

def method_cells(groups):
 return [dict(group=g['id'],access=a,method_ids=[m['id'] for m in g['methods'] if m['data_access_at_use']==a],count=sum(m['data_access_at_use']==a for m in g['methods'])) for g in groups for a in AK]

def operation_groups(): return [{**g,'methods':[MM[i] for i in g['ids']]} for g in OPS]

def access_groups(): return [{**a,'methods':[m for m in METHODS if m['data_access_at_use']==a['key']]} for a in ACC]

def d_matrix():
 groups=operation_groups();cells=method_cells(groups)
 fig,ax=frame();fig.subplots_adjust(left=.35,right=.97,bottom=.18,top=.93)
 for y,g in enumerate(groups):
  for x,a in enumerate(AK):
   c=next(c for c in cells if c['group']==g['id'] and c['access']==a)
   ax.add_patch(Rectangle((x-.47,y-.43),.94,.86,facecolor=PALE[x] if c['count'] else '#fafafa',edgecolor='#d5dde1'))
   ax.text(x,y-.05,str(c['count']) if c['count'] else '0',ha='center',va='center',fontsize=18,weight='bold' if c['count'] else 'normal',color='#263b4c' if c['count'] else '#98a2ac')
   if c['count']:ax.text(x,y+.25,'метод' if c['count']==1 else 'методов',ha='center',fontsize=8,color='#526576')
 ax.set_xticks(range(3),[a['id']+' · '+a['short'].replace(' ','\n',1) for a in ACC],fontsize=10)
 ax.set_yticks(range(6),[g['id']+' · '+g['short']+'\nВсего '+str(len(g['methods'])) for g in groups],fontsize=10)
 ax.set(xlim=(-.55,2.55),ylim=(5.6,-.6));ax.tick_params(length=0,pad=12)
 for sp in ax.spines.values():sp.set_visible(False)
 return fig,cells

def d_facets():
 fig,axes=plt.subplots(1,3,figsize=(12,5.7),sharey=True);fig.subplots_adjust(left=.35,right=.97,wspace=.15,top=.86,bottom=.16)
 cells=method_cells(operation_groups())
 for x,(a,ax) in enumerate(zip(ACC,axes)):
  vals=[next(c['count'] for c in cells if c['group']==g['id'] and c['access']==a['key']) for g in OPS]
  ax.barh(range(6),vals,color=COLORS[x],height=.55)
  for y,n in enumerate(vals):ax.text(n+.3,y,str(n),va='center',fontsize=12)
  ax.set_title(a['id']+' · '+a['short'].replace(' ','\n',1)+'\nВсего '+str(sum(vals)),fontsize=11,pad=15)
  ax.set_xlim(0,max(c['count'] for c in cells)+2);ax.set_xticks([0,5,10,15]);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 axes[0].set_yticks(range(6),[g['id']+' · '+g['short'] for g in OPS],fontsize=10);axes[0].invert_yaxis()
 fig.text(.66,.035,'Число методов; единая шкала во всех трёх панелях',ha='center',fontsize=10)
 return fig,cells

def d_profiles():
 groups=report_family_groups(METHODS);cells=method_cells(groups)
 fig,(ax,right)=plt.subplots(1,2,figsize=(12,5.6),gridspec_kw={'width_ratios':[4,1]});fig.subplots_adjust(left=.29,right=.98,top=.9,bottom=.18,wspace=.08)
 names=['Архитектурные признаки\nи предикторы','Zero-cost proxies','Кривые обучения\nи гибриды','Готовые / предсказанные\nвеса','Scaling laws']
 for y,g in enumerate(groups):
  left=0;counts=[]
  for x,a in enumerate(AK):
   n=next(c['count'] for c in cells if c['group']==g['id'] and c['access']==a);counts.append(n)
   if n:
    w=n/len(g['methods'])*100;ax.barh(y,w,left=left,height=.6,color=COLORS[x]);ax.text(left+w/2,y,f'{ACODE[a]}: {n}',ha='center',va='center',fontsize=10,color='white' if x==1 else '#172c3d');left+=w
  right.text(.15,y,str(len(g['methods'])),va='center',fontsize=15,weight='bold')
 ax.set_yticks(range(5),[g['id']+' · '+name for g,name in zip(groups,names)]);ax.set_ylim(4.65,-.65);ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100],['0%','25%','50%','75%','100%']);ax.set_xlabel('Доля внутри семейства; подпись сегмента = число методов')
 right.set_ylim(ax.get_ylim());right.axis('off');right.set_title('Всего',fontsize=10)
 fig.text(.3,.02,'N: без реальных примеров     U: без целевых ответов     T: с objective',fontsize=10)
 return fig,cells

def d_3d():
 """Experimental diagnostic only: categorical z adds evidence availability."""
 fig=plt.figure(figsize=(12,6.3));ax=fig.add_subplot(111,projection='3d');have={o['method_id'] for o in OBS};rows=[]
 for yi,g in enumerate(OPS):
  for xi,a in enumerate(AK):
   for zi in [0,1]:
    ids=[mid for mid in g['ids'] if MM[mid]['data_access_at_use']==a and (mid in have)==bool(zi)]
    if ids:
     ax.scatter(xi,yi,zi,s=50+30*len(ids),color=COLORS[xi],edgecolor='#273b4c',alpha=.85)
     ax.text(xi,yi,zi+.06,str(len(ids)),fontsize=9)
     rows.append(dict(operation=g['id'],access=a,numerical_evidence=bool(zi),method_ids=ids,count=len(ids)))
 ax.set_xticks(range(3),['N','U','T']);ax.set_yticks(range(6),[g['id'] for g in OPS]);ax.set_zticks([0,1],['Нет в сравнении','Есть в сравнении'],fontsize=8)
 ax.set_xlabel('Входы');ax.set_ylabel('Действие');ax.view_init(elev=22,azim=-53);ax.set_title('3D-проба: действие × входы × наличие численного результата',fontsize=12)
 fig.subplots_adjust(left=0,right=.9,top=.88,bottom=.06)
 return fig,rows

def d_evidence_facets():
 have={o['method_id'] for o in OBS};fig,axes=plt.subplots(1,2,figsize=(12,5.6),sharey=True);fig.subplots_adjust(left=.31,right=.98,top=.86,bottom=.13,wspace=.13);rows=[]
 for z,ax in enumerate(axes):
  for y,g in enumerate(OPS):
   for x,a in enumerate(AK):
    ids=[mid for mid in g['ids'] if MM[mid]['data_access_at_use']==a and (mid in have)==bool(z)]
    ax.add_patch(Rectangle((x-.47,y-.44),.94,.88,facecolor=PALE[x],edgecolor='white'))
    ax.text(x,y,str(len(ids)),ha='center',va='center',fontsize=14)
    rows.append(dict(operation=g['id'],access=a,numerical_evidence=bool(z),method_ids=ids,count=len(ids)))
  ax.set_xticks(range(3),['N','U','T']);ax.set_yticks(range(6),[g['id']+' · '+g['short'] for g in OPS],fontsize=9);ax.set(xlim=(-.5,2.5),ylim=(5.5,-.5));ax.tick_params(length=0)
  ax.set_title('Нет допущенных чисел' if not z else 'Есть допущенные числа',fontsize=12)
 return fig,rows

BLOCKS=['G1','G2','G4']
SHORT={'G1':'G1 · P28 / FlexiBERT\nOpenWebText → GLUE','G2':'G2 · P29 / FlexiBERT\nWikiText-103 → GLUE','G4':'G4 · P32 / FlexiBERT\nOpenWebText → weighted GLUE'}

def bf_data(): return [o for o in OBS if o['block'] in BLOCKS]

def bf_aligned():
 obs=bf_data();ids=sorted({o['method_id'] for o in obs});fig,axes=plt.subplots(1,3,figsize=(12,5.8),sharey=True);fig.subplots_adjust(left=.26,right=.98,top=.87,bottom=.12,wspace=.12)
 for ax,b in zip(axes,BLOCKS):
  ax.set_title(SHORT[b],fontsize=10,pad=16);oo=[o for o in obs if o['block']==b]
  for o in oo:
   y=ids.index(o['method_id']);v=metric(o,'spearman_rho')['value'];dot(ax,v,y,o['domain'])
   ax.annotate(f'{v:.3f} {ACODE[access(o,MM)]}',(v,y),xytext=(9,0),textcoords='offset points',fontsize=10,va='center')
  ax.set_xlim(0,1.08);ax.set_xticks([0,.5,1]);ax.set_xlabel('Spearman ρ',fontsize=10);ax.grid(alpha=.15);ax.set_axisbelow(True)
 axes[0].set_yticks(range(len(ids)),[i+' '+textwrap.shorten(MM[i]['name'].split(' / ')[0],width=27,placeholder='…') for i in ids],fontsize=10);axes[0].set_ylim(len(ids)-.4,-.6)
 return fig,obs

def bf_heatmap():
 obs=bf_data();ids=sorted({o['method_id'] for o in obs});fig,ax=frame(12,5.8);fig.subplots_adjust(left=.31,right=.97,top=.86,bottom=.09)
 for y,mid in enumerate(ids):
  for x,b in enumerate(BLOCKS):
   o=next((o for o in obs if o['block']==b and o['method_id']==mid),None)
   v=metric(o,'spearman_rho')['value'] if o else None
   ax.add_patch(Rectangle((x-.48,y-.46),.96,.92,facecolor=plt.cm.Blues(.08+.65*v) if o else '#f4f4f4',edgecolor='white'))
   ax.text(x,y,f'{v:.3f}  ·  {ACODE[access(o,MM)]}' if o else '—',ha='center',va='center',fontsize=10,color='white' if o and v>.7 else '#203545')
 ax.set_xticks(range(3),[SHORT[b] for b in BLOCKS],fontsize=10);ax.xaxis.tick_top();ax.set_yticks(range(len(ids)),[i+' '+textwrap.shorten(MM[i]['name'].split(' / ')[0],width=29,placeholder='…') for i in ids],fontsize=10)
 ax.set(xlim=(-.5,2.5),ylim=(len(ids)-.5,-.5));ax.tick_params(length=0,pad=10)
 for sp in ax.spines.values():sp.set_visible(False)
 fig.text(.32,.015,'Цвет: Spearman ρ, общая шкала 0–1. Число сохраняет точность; буква = входы.',fontsize=10)
 return fig,obs

def bf_ranked():
 obs=bf_data();fig,axes=plt.subplots(1,3,figsize=(12,5.8));fig.subplots_adjust(left=.065,right=.98,top=.86,bottom=.14,wspace=.24)
 for ax,b in zip(axes,BLOCKS):
  oo=sorted([o for o in obs if o['block']==b],key=lambda o:metric(o,'spearman_rho')['value'],reverse=True)
  for y,o in enumerate(oo):
   v=metric(o,'spearman_rho')['value'];ax.axhspan(y-.43,y+.43,color=PALE[AK.index(access(o,MM))],alpha=.6)
   ax.plot([0,v],[y,y],color='#bcc9d1',lw=1);dot(ax,v,y,o['domain'])
   ax.text(.02,y-.23,o['method_id']+' · '+ACODE[access(o,MM)],fontsize=8)
   ax.text(min(v+.05,.91),y,f'{v:.3f}',fontsize=8,va='center')
  ax.set(xlim=(0,1.05),ylim=(14.7,-.7));ax.set_yticks([]);ax.set_xticks([0,.5,1]);ax.set_title(SHORT[b],fontsize=10,pad=18);ax.set_xlabel('Spearman ρ');ax.grid(axis='x',alpha=.2)
 return fig,obs


def e_lines():
 obs=[o for o in OBS if o['block']=='G5'];fig,axes=plt.subplots(1,4,figsize=(12,4.9),sharex=True,sharey=True);fig.subplots_adjust(left=.07,right=.99,top=.84,bottom=.19,wspace=.12)
 for ax,mid in zip(axes,['M69','M36','M37','M38']):
  oo=sorted([o for o in obs if o['method_id']==mid],key=lambda o:o['n_train_predictor']);xx=[o['n_train_predictor'] for o in oo];vv=[metric(o,'kendall_tau')['value'] for o in oo];sd=[metric(o,'kendall_tau')['uncertainty'] for o in oo]
  ax.plot(xx,vv,color='#8294a3',lw=1.3)
  for o,x,v,s in zip(oo,xx,vv,sd):
   ax.errorbar(x,v,yerr=s,color='#677f90',capsize=4);dot(ax,x,v,'relevant');ax.annotate(f'{v:.2f} ± {s:.2f}',(x,v+s),xytext=(0,8),textcoords='offset points',ha='left' if x==32 else 'right' if x==1024 else 'center',fontsize=9)
  ax.set_xscale('log',base=2);ax.set_xticks([32,128,1024],['32','128','1024']);ax.set_xlim(18,1700);ax.set_ylim(0,1);ax.set_title(mid+' · '+oo[0]['variant_label'].replace('RF + ','').replace(' + ',' +\n')+'\nВходы '+ACODE[MM[mid]['data_access_at_use']],fontsize=10);ax.grid(alpha=.15);ax.set_xlabel('Число меток H')
 axes[0].set_ylabel('Kendall τ; отрезки ± SD')
 return fig,obs

def e_budget_panels():
 obs=[o for o in OBS if o['block']=='G5'];fig,axes=plt.subplots(1,3,figsize=(12,4.9),sharey=True);fig.subplots_adjust(left=.2,right=.98,top=.82,bottom=.18,wspace=.16);ids=['M69','M36','M37','M38']
 for ax,n in zip(axes,[32,128,1024]):
  for y,mid in enumerate(ids):
   o=next(o for o in obs if o['method_id']==mid and o['n_train_predictor']==n);v=metric(o,'kendall_tau')['value'];sd=metric(o,'kendall_tau')['uncertainty']
   ax.errorbar(v,y,xerr=sd,color='#718796',capsize=4);dot(ax,v,y,'relevant');ax.text(v,y-.25,f'{v:.2f} ± {sd:.2f}',ha='center',fontsize=9)
  ax.set_xlim(0,1);ax.set_xticks([0,.5,1]);ax.set_title(f'H = {n} меток',fontsize=12);ax.set_xlabel('Kendall τ ± SD');ax.grid(alpha=.16)
 axes[0].set_yticks(range(4),[i+' · '+next(o['variant_label'] for o in obs if o['method_id']==i) for i in ids],fontsize=10);axes[0].set_ylim(3.7,-.7)
 return fig,obs

def e_matrix():
 obs=[o for o in OBS if o['block']=='G5'];fig,ax=frame(12,4.8);fig.subplots_adjust(left=.25,right=.97,top=.81,bottom=.15);ids=['M69','M36','M37','M38']
 for y,mid in enumerate(ids):
  for x,n in enumerate([32,128,1024]):
   o=next(o for o in obs if o['method_id']==mid and o['n_train_predictor']==n);v=metric(o,'kendall_tau')['value'];sd=metric(o,'kendall_tau')['uncertainty']
   ax.add_patch(Rectangle((x-.48,y-.44),.96,.88,facecolor=plt.cm.Greys(.07+.5*v),edgecolor='white'))
   ax.text(x,y,f'{v:.2f} ± {sd:.2f}',ha='center',va='center',fontsize=15)
 ax.set_xticks(range(3),['H = 32','H = 128','H = 1024']);ax.xaxis.tick_top();ax.set_yticks(range(4),[i+' · '+next(o['variant_label'] for o in obs if o['method_id']==i) for i in ids]);ax.set(xlim=(-.5,2.5),ylim=(3.5,-.5));ax.tick_params(length=0,pad=15)
 for sp in ax.spines.values():sp.set_visible(False)
 fig.text(.26,.025,'Kendall τ ± SD, 50 запусков; цвет = среднее на общей шкале 0–1.',fontsize=11)
 return fig,obs

def g6_dots():
 obs=[o for o in OBS if o['block']=='G6'];fig,axes=plt.subplots(1,2,figsize=(12,4.6),sharey=True);fig.subplots_adjust(left=.4,right=.98,top=.86,bottom=.15,wspace=.2)
 for ax,key,title in zip(axes,['spearman_rho','kendall_tau'],['Spearman ρ','Kendall τ']):
  for y,o in enumerate(obs):
   v=metric(o,key)['value'];dot(ax,v,y,'relevant');ax.annotate(f'{v:.3f}',(v,y),xytext=(10,0),textcoords='offset points',va='center',fontsize=10)
  ax.set_xlim(0,1);ax.set_xticks([0,.5,1]);ax.set_title(title);ax.grid(alpha=.15)
 axes[0].set_yticks(range(6),[o['method_id']+' · '+o['variant_label'] for o in obs],fontsize=9);axes[0].set_ylim(5.6,-.6)
 return fig,obs

def g6_table():
 obs=[o for o in OBS if o['block']=='G6'];fig,ax=frame(12,4.4);ax.axis('off')
 rows=[[o['method_id']+' · '+o['variant_label'],ACODE[access(o,MM)],f"{metric(o,'spearman_rho')['value']:.3f}",f"{metric(o,'kendall_tau')['value']:.3f}"] for o in obs]
 tab=ax.table(cellText=rows,colLabels=['Вариант','Входы','Spearman ρ','Kendall τ'],colWidths=[.60,.10,.15,.15],cellLoc='left',bbox=[0,.08,1,.84]);tab.auto_set_font_size(False);tab.set_fontsize(11)
 for (r,c),cell in tab.get_celld().items():cell.set_edgecolor('white');cell.set_facecolor('#dce7ee' if r==0 else '#f1f5f7' if r%2 else '#fff')
 return fig,obs

def g6_scatter():
 obs=[o for o in OBS if o['block']=='G6'];fig,ax=frame(10,5.8)
 for o in obs:
  x=metric(o,'spearman_rho')['value'];y=metric(o,'kendall_tau')['value'];dot(ax,x,y,'relevant');ax.annotate(o['variant_label'],(x,y),fontsize=9,xytext=(6,4),textcoords='offset points')
 ax.set(xlim=(0,1),ylim=(0,1),xlabel='Spearman ρ',ylabel='Kendall τ');ax.grid(alpha=.15);fig.tight_layout();return fig,obs

CANDIDATES={'D_matrix':d_matrix,'D_facets':d_facets,'D_profiles':d_profiles,'D_3d':d_3d,'D_evidence_facets':d_evidence_facets,'BF_aligned':bf_aligned,'BF_heatmap':bf_heatmap,'BF_ranked':bf_ranked,'E_lines':e_lines,'E_budget_panels':e_budget_panels,'E_matrix':e_matrix,'G6_dots':g6_dots,'G6_table':g6_table,'G6_scatter':g6_scatter}
