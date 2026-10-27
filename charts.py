"""One rendering path for the app, vector PDF, SVG and PNG."""
import io, json, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.legend_handler import HandlerPatch
from matplotlib.colors import to_rgba
from corpus import load, metric, eligible, access
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#b3bfcc','axes.labelcolor':'#26364a','text.color':'#26364a','svg.fonttype':'none','pdf.fonttype':42})
STYLES={'relevant':dict(facecolor=to_rgba('#8196aa',.35),edgecolor='#64788c',linestyle=(0,(2,1.4))), 'nlp_transformer':dict(facecolor='#4588ad',edgecolor='#235c7d',linestyle='solid'), 'text_embedding':dict(facecolor='#e95184',edgecolor='#a92658',linestyle='solid')}
LABELS={'relevant':'Релевантные подходы','nlp_transformer':'NLP Transformer','text_embedding':'Модели эмбеддингов текстов - 0 подтверждённых работ'}
ACCESS={'none':'Реальные входы\nне нужны','unlabeled':'Входы\nбез разметки','labeled_or_objective':'Разметка /\nцелевая функция'}
METRICS={'spearman_rho':'Spearman rho','kendall_tau':'Kendall tau','top100_recall':'Top-100 recall'}
class CircleHandler(HandlerPatch):
    def create_artists(self,legend,orig_handle,xdescent,ydescent,width,height,fontsize,trans):
        p=Circle((width/2-xdescent,height/2-ydescent),height*.44)
        self.update_prop(p,orig_handle,legend); p.set_transform(trans); return [p]
def legend(fig):
    handles=[Circle((0,0),1,**v) for v in STYLES.values()]
    fig.legend(handles,list(LABELS.values()),loc='lower left',bbox_to_anchor=(.02,.005),frameon=False,fontsize=8,handler_map={Circle:CircleHandler()},ncol=1)
def dot(ax,x,y,cls,oid=None):
    da=DrawingArea(13,13,0,0)
    p=Circle((6.5,6.5),5,linewidth=1.2,**STYLES[cls]); da.add_artist(p)
    if oid:
        p.set_gid('point_'+oid); p.set_url('/?observation='+oid)
    artist=AnnotationBbox(da,(x,y),frameon=False,pad=0); ax.add_artist(artist)
    return p

def chart(observations,plot='metric',name='spearman_rho',scale='linear',linthresh=.5,provisional=False,methods=None,title=None,zoom=None):
    methods=methods or {m['id']:m for m in load('methods')}
    accepted=[o for o in observations if eligible(o,plot,name,provisional) is None]
    if plot=='A' and zoom is not None: accepted=[o for o in accepted if o['costs'][0]['value']<=zoom]
    fig,ax=plt.subplots(figsize=(10.5,6.5)); fig.subplots_adjust(left=.13,right=.94,bottom=.27,top=.84)
    ax.set_title(title or plot,loc='left',fontsize=13,pad=22)
    ax.grid(alpha=.16); ax.set_axisbelow(True)
    if not accepted:
        ax.text(.5,.5,'Нет сопоставимых данных для этого графика',ha='center',va='center',transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([]); legend(fig); return fig,accepted
    if len({o['comparison_group_id'] for o in accepted})>1:
        raise ValueError('One comparison group per chart required')
    ax.set_ylabel(METRICS[name]+(' (исходный знак)' if any(o.get('sign_status','').startswith('unresolved') for o in accepted) else ''))
    ax.set_ylim(-1.07,1.1) if name!='top100_recall' else ax.set_ylim(0,1.08)
    if plot=='E':
        for vid in dict.fromkeys(o['method_variant_id'] for o in accepted):
            oo=sorted([o for o in accepted if o['method_variant_id']==vid],key=lambda o:o['n_train_predictor'])
            xx=[o['n_train_predictor'] for o in oo]; yy=[metric(o,name)['value'] for o in oo]
            ax.plot(xx,yy,color='#a2abb4',lw=1)
            for o,x,y in zip(oo,xx,yy):
                sd=metric(o,name)['uncertainty']
                if sd is not None: ax.errorbar(x,y,yerr=sd,fmt='none',color='#7b8c9c',capsize=3,lw=1)
                dot(ax,x,y,o['domain'],o['id'])
            ax.annotate(oo[0]['method_id'],(xx[-1],yy[-1]),xytext=(10,7 if oo[0]['method_id']=='M38' else -7 if oo[0]['method_id']=='M36' else 0),textcoords='offset points',fontsize=9)
        ax.set_xscale('log',base=2); ticks=sorted({o['n_train_predictor'] for o in accepted}); ax.set_xticks(ticks,[str(t) for t in ticks]); ax.set_xlim(min(ticks)*.75,max(ticks)*1.65)
        ax.set_xlabel('Число архитектур с известным качеством (labels; не время)')
        ax.set_ylim(0,1)
    elif plot=='A':
        for i,o in enumerate(accepted):
            x=o['costs'][0]['value']; y=metric(o,name)['value']; dot(ax,x,y,o['domain'],o['id'])
            ax.annotate(o['method_id'] or 'ZeroLM*',(x,y),xytext=(6,8 if i%2 else -15),textcoords='offset points',fontsize=8)
        if scale=='symlog':
            ax.set_xscale('symlog',linthresh=linthresh)
            ax.set_xticks([0,.1,.5,1,2,5,10],['0','0.1','0.5','1','2','5','10'])
        ax.set_xlim(0,zoom if zoom is not None else max(o['costs'][0]['value'] for o in accepted)*1.2)
        ax.set_xlabel(f'Reported average time, s | {scale}'+(f'; linthresh={linthresh:g} s' if scale=='symlog' else ''))
        ax.text(0,1.015,'Предварительно: device / полный scope не установлены; Парето выключен',transform=ax.transAxes,fontsize=8)
    elif plot=='B':
        for cat_idx,cat in enumerate(ACCESS):
            oo=[o for o in accepted if access(o,methods)==cat]
            for i,o in enumerate(oo):
                x=cat_idx+((i/(len(oo)-1)-.5)*.72 if len(oo)>1 else 0); y=metric(o,name)['value']; dot(ax,x,y,o['domain'],o['id'])
                ax.annotate(o['method_id'] or 'ZeroLM*',(x,y),xytext=(0,10 if i%2==0 else -14),textcoords='offset points',ha='center',fontsize=7)
        ax.set_xticks(range(len(ACCESS)),ACCESS.values()); ax.set_xlim(-.5,len(ACCESS)-.5); ax.set_xlabel('Доступ при применении; discovery и исторические labels учитываются отдельно')
    else:
        accepted=sorted(accepted,key=lambda o:(o['method_id'] or 'M26',o['variant_label']))
        ax.set_xticks(range(len(accepted)),[o['variant_label'] if len(accepted)<=7 else o['method_id'] or 'ZeroLM*' for o in accepted],rotation=25 if len(accepted)<=7 else 0,ha='right' if len(accepted)<=7 else 'center',fontsize=8)
        ax.set_xlim(-.6,len(accepted)-.4)
        for i,o in enumerate(accepted): dot(ax,i,metric(o,name)['value'],o['domain'],o['id'])
        ax.set_xlabel('Метод / вариант; порядок по ID, не общий рейтинг')
    legend(fig); return fig,accepted

def map_chart(methods):
    verified=[m for m in methods if m['visual_class'] is not None and m.get('analysis_status')!='excluded']
    fam=list(dict.fromkeys(f for m in verified for f in m['family_tags']))
    heights=[]
    for f in fam:
        heights.append(max(1,max(math.ceil(sum(f in m['family_tags'] and m['data_access_at_use']==a for m in verified)/4) for a in ACCESS)))
    centers=[]; cursor=0
    for h in heights:
        centers.append(cursor+(h-1)/2); cursor+=h+1
    fig,ax=plt.subplots(figsize=(11,9 if len(fam)>5 else 5.8)); fig.subplots_adjust(left=.24,right=.97,top=.86,bottom=.24)
    for yi,f in enumerate(fam):
        for xi,a in enumerate(ACCESS):
            cell=[m for m in verified if f in m['family_tags'] and m['data_access_at_use']==a]
            for j,m in enumerate(cell):
                x=xi+(j%4-1.5)*.19; y=centers[yi]+(j//4-(math.ceil(len(cell)/4)-1)/2)
                dot(ax,x,y,m['visual_class'],m['id']); ax.annotate(m['id'],(x,y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=7)
    ax.set_xlim(-.55,len(ACCESS)-.45); ax.set_ylim(max(cursor-1,1),-1); ax.set_yticks(centers,fam); ax.set_xticks(range(len(ACCESS)),ACCESS.values()); ax.grid(alpha=.15)
    if not verified: ax.text(.5,.5,'Нет методов с подтверждённым классом в выбранных фильтрах',ha='center',transform=ax.transAxes)
    ax.set_title('Карта механизмов и требований к реальным данным',loc='left',fontsize=14,pad=20)
    ax.set_xlabel('Смещения внутри ячеек служат читаемости и не имеют численного смысла')
    legend(fig); return fig,verified

def export(fig,fmt):
    buf=io.BytesIO(); fig.savefig(buf,format=fmt,dpi=180); return buf.getvalue()

def interactive_svg(fig, records):
    import xml.etree.ElementTree as ET
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    root=ET.fromstring(export(fig,'svg'))
    byid={o['id']:o for o in records}
    for node in root.iter():
        ident=node.attrib.get('id','')
        if ident.startswith('point_') and ident[6:] in byid:
            title=ET.Element('{http://www.w3.org/2000/svg}title'); title.text=json.dumps(byid[ident[6:]],ensure_ascii=False,indent=1); node.insert(0,title)
        if node.tag.endswith('}a'): node.set('target','_blank')
    root.set('width','100%'); root.set('height','100%')
    return ET.tostring(root,encoding='unicode')


def report_family_groups(methods):
    """Editorial partition for the PDF; method-level evidence stays unchanged."""
    groups=[]
    assigned=[]
    for family in load('report_families'):
        members=[m for m in methods if set(m['family_tags']) & set(family['family_tags'])]
        assigned.extend(m['id'] for m in members)
        groups.append({**family,'methods':members})
    if sorted(assigned)!=sorted(m['id'] for m in methods):
        raise ValueError('Report families must cover every method exactly once')
    return groups


def family_overview_chart(methods):
    """A categorical 2D plot with exactly one point per report family."""
    methods=[m for m in methods if m.get('analysis_status')!='excluded']
    groups=report_family_groups(methods)
    categories=['none','unlabeled','labeled_or_objective','mixed']
    labels=['Реальные входы\nне нужны','Входы\nбез разметки','Разметка /\nцелевая функция','Разные требования\nвнутри семейства']
    row_labels=['D1 · Архитектурные признаки\nи предикторы','D2 · Zero-cost proxies','D3 · Частичное обучение\nи кривые обучения','D4 · Обученные или\nпредсказанные веса','D5 · Scaling laws']
    fig,ax=plt.subplots(figsize=(12,5.5))
    fig.subplots_adjust(left=.28,right=.98,top=.90,bottom=.23)
    records=[]
    for i,group in enumerate(groups):
        known={m['data_access_at_use'] for m in group['methods']} - {'unknown'}
        category='mixed' if len(known)>1 else next(iter(known)) if known else 'none'
        n_known=sum(m['data_access_at_use']!='unknown' for m in group['methods'])
        x=categories.index(category)
        point=ax.scatter([x],[i],s=130,facecolor='#64788c',edgecolor='#26364a',linewidth=1.2,zorder=3)
        point.set_gid('family_'+group['id'])
        ax.annotate(f"{group['id']} · методов: {len(group['methods'])}",(x,i),xytext=(0,17),textcoords='offset points',ha='center',fontsize=10,weight='bold')
        ax.annotate(f"Входы уточнены: {n_known}/{len(group['methods'])}",(x,i),xytext=(0,-22),textcoords='offset points',ha='center',fontsize=8)
        records.append({k:v for k,v in group.items() if k!='methods'} | {'method_ids':[m['id'] for m in group['methods']],'data_access_category':category,'n_access_known':n_known,'known_access_categories':sorted(known)})
    ax.set_xlim(-.65,3.65); ax.set_ylim(4.65,-.65)
    ax.set_xticks(range(4),labels,fontsize=9); ax.set_yticks(range(5),row_labels,fontsize=10)
    ax.set_xlabel('Доступ к данным при применении (включая получение признаков нового кандидата)',labelpad=13)
    ax.set_ylabel('Семейство методов',labelpad=13)
    ax.grid(alpha=.22); ax.set_axisbelow(True)
    ax.set_title('Пять семейств: механизм × требования к данным',loc='left',fontsize=13,pad=16)
    return fig,records
