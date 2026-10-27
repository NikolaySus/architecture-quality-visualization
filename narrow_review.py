"""Scoped evidence and visual designs for the three O1-O3 reviews."""
from collections import Counter
import textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from corpus import load, comparison_methods, exclusion_reason, access as base_access, metric
from charts import dot
from variant_charts import OP, ACODE, SHORT

AUDIT=load('narrow_method_audit')
ROWS={r['method_id']:r for r in AUDIT['methods']}
METHODS=[m for m in comparison_methods() if m['id'] in AUDIT['scope_ids']]
for m in METHODS:
 m['data_access_at_use']=ROWS[m['id']]['data_access_at_use']
MM={m['id']:m for m in METHODS}
OBS=[o for o in load('observations') if o['method_id'] in MM and exclusion_reason(o) is None]

def access(o,methods):
 for a in AUDIT.get('observation_access_overrides',[]):
  if (o['block'],o['method_id'])==(a['block'],a['method_id']):return a['data_access']
 return base_access(o,methods)
SIGNALS={'G':'Граф / размеры','W':'Значения весов','A':'Активации','D':'Производные',
         'WD':'Веса + производные','AD':'Активации + производные','GA':'Граф + активации',
         'GAD':'Граф + активации + производные','WAD':'Веса + активации + производные',
         'GWAD':'Все четыре источника'}
OPERATIONS={'graph':'Дескрипторы G','weights':'Только веса W','forward':'Прямые проходы','derivatives':'Прямые проходы\nи производные'}
INPUTS={'no_examples':'Без входных\nпримеров','synthetic':'Синтетические\nвходы','unlabeled':'Реальные X\nбез targets','objective':'Реальные X\nи objective'}
SETUPS={'fixed':'Заданная формула', 'distribution':'Настройка / согласование\nбез качеств',
        'search':'Поиск формулы по H','calibration':'Калибровка по H',
        'fit':'Обучение предиктора по H','curves':'Обучение по кривым',
        'prompt':'Примеры H в prompt'}
SCODE={s:f'P{i+1}' for i,s in enumerate(SETUPS)}
REP={'none':'Без отдельного предобучения представления', 'architecture_pretrain':'Предобучение на графах',
     'finetuned_lm':'Дообучение готового LM','frozen_lm':'Готовый замороженный LM','trained_lm':'Обученный LM по архитектурам'}
TRANSFORMS={'O1':'Прямой дескриптор','O2':'Фиксированная proxy-формула','O3':'Обученный / обусловленный\nпредиктор'}
PALETTE=['#467c91','#ba8948','#738b60','#8b6992']
CONFIGS=[
 dict(id='01_signal_mechanisms',prefix='S',title='Источники сигнала и механизмы',
      question='Какая информация о кандидате входит в оценку и как она превращается в прогноз?',
      xkey='operation_group',ykey='signal_profile',xlabels=TRANSFORMS,ylabels=SIGNALS,
      matrix_reason='Матрица признаков явно раскрывает состав комбинаций. 2D-карта остаётся основной: её точки имеют точные, непересекающиеся расшифровки.',
      conclusion='Наиболее полезное уточнение O2 - различение весов, откликов и производных. O3 стоит делить прежде всего по входным признакам: архитектурные кодировки и измеряемые ZCP требуют разных действий.'),
 dict(id='02_candidate_requirements',prefix='R',title='Что требуется для нового кандидата',
      question='Какие входы и операции нужны для получения полной оценки новой архитектуры?',
      xkey='use_inputs',ykey='operation',xlabels=INPUTS,ylabels=OPERATIONS,
      matrix_reason='2D-карта показывает крупные режимы применения. Матрица уточняет смешение реальных и синтетических входов, которое нельзя прочесть из одного N/U/T.',
      conclusion='Подразделение N полезно: отсутствие реальных данных не равно отсутствию входов и вычислений. Отдельные режимы - граф, веса, синтетический forward и синтетические производные.'),
 dict(id='03_estimator_preparation',prefix='P',point_prefix='T',title='Как подготавливается оценщик',
      question='Где используются исторические качества и что обучается до оценки нового кандидата?',
      xkey='access',ykey='setup',xlabels={'N':'Без реальных X','U':'Реальные X без targets','T':'Реальные X + objective'},ylabels=SETUPS,
      matrix_reason='2D-карта отделяет подготовку от применения. Матрица дополнительно показывает предобучение представления и готовые LM: эти признаки пересекаются со способом использования H.',
      conclusion='Поиск формулы, калибровка alpha, fit предиктора и примеры в prompt используют знания о качестве по-разному. Их объединение в одну категорию «обучаемый метод» скрывает существенные зависимости.'),
]

def value(mid,key):
 if key=='operation_group':return OP[mid]
 if key=='access':return ACODE[MM[mid]['data_access_at_use']]
 return ROWS[mid][key]

def cells(cfg):
 result=[]
 for y in cfg['ylabels']:
  for x in cfg['xlabels']:
   ids=[m['id'] for m in METHODS if value(m['id'],cfg['xkey'])==x and value(m['id'],cfg['ykey'])==y]
   if ids:result.append(dict(id=f'{cfg.get("point_prefix",cfg["prefix"])}{len(result)+1:02d}',x=x,y=y,method_ids=ids,count=len(ids)))
 return result

def grouped_map(cfg):
 cc=cells(cfg);xx=list(cfg['xlabels']);yy=list(cfg['ylabels'])
 fig,ax=plt.subplots(figsize=(12,6.4));fig.subplots_adjust(left=.35,bottom=.18,right=.98,top=.96)
 for y in range(len(yy)):
  if y%2==0:ax.axhspan(y-.49,y+.49,color='#f2f5f7',zorder=0)
 for c in cc:
  x,y=xx.index(c['x']),yy.index(c['y'])
  ax.scatter(x,y,s=650+50*c['count'],color=PALETTE[x%4],alpha=.88,edgecolors='white',linewidths=1.2)
  ax.text(x,y,str(c['count']),ha='center',va='center',fontsize=12,weight='bold',color='white')
  ax.annotate(c['id'],(x,y),xytext=(30,0),textcoords='offset points',va='center',fontsize=9,color='#233d50')
 ax.set_xticks(range(len(xx)),[cfg['xlabels'][x] for x in xx],fontsize=10)
 ax.set_yticks(range(len(yy)),[(y+' · ' if cfg['ykey']=='signal_profile' else SCODE[y]+' · ' if cfg['ykey']=='setup' else '')+cfg['ylabels'][y] for y in yy],fontsize=10)
 ax.set(xlim=(-.55,len(xx)-.48),ylim=(len(yy)-.55,-.55));ax.tick_params(length=0,pad=9)
 ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 for s in ax.spines.values():s.set_visible(False)
 fig.text(.35,.035,'Число внутри точки = методы; код справа = таблица расшифровки. Оси категориальные.',fontsize=9)
 return fig,cc

def feature_definitions(cfg):
 if cfg['prefix']=='S':
  return [('G','Граф /\nразмеры',lambda r:'G' in r['signal_profile']),('W','Веса',lambda r:'W' in r['signal_profile']),('A','Активации',lambda r:'A' in r['signal_profile']),('D','Производные',lambda r:'D' in r['signal_profile'])]
 if cfg['prefix']=='R':
  return [('real','Реальные\nX',lambda r:r['use_inputs'] in ['unlabeled','objective']),('target','Реальный\nobjective',lambda r:r['use_inputs']=='objective'),('synthetic','Синтетический\nкомпонент',lambda r:r['synthetic_component']),('forward','Forward\nкандидата',lambda r:r['operation'] in ['forward','derivatives']),('backward','Производные\nкандидата',lambda r:r['operation']=='derivatives')]
 return [('H','Качества /\nкривые',lambda r:r['setup'] in ['search','calibration','fit','curves','prompt']),('formula','Поиск / fit\nформулы',lambda r:r['setup'] in ['search','calibration']),('predictor','Fit\nпредиктора',lambda r:r['setup'] in ['fit','curves']),('prompt','H в\nprompt',lambda r:r['setup']=='prompt'),('pretrain','Предобучение\nна графах',lambda r:r['representation']=='architecture_pretrain'),('LM','Готовый\nLM',lambda r:r['representation'] in ['frozen_lm','finetuned_lm'])]

def feature_profiles(cfg):
 features=feature_definitions(cfg);profiles={}
 for mid,r in ROWS.items():
  bits=tuple(int(f[2](r)) for f in features)
  profiles.setdefault(bits,[]).append(mid)
 return features,sorted(profiles.items(),key=lambda p:(sum(p[0]),p[0]))

def feature_matrix(cfg):
 features,profiles=feature_profiles(cfg)
 fig,(ax,right)=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[3,2]})
 fig.subplots_adjust(left=.09,right=.98,bottom=.1,top=.82,wspace=.12)
 records=[]
 for y,(bits,ids) in enumerate(profiles):
  for x,b in enumerate(bits):
   ax.add_patch(Rectangle((x-.47,y-.43),.94,.86,facecolor='#467c91' if b else '#edf1f3'))
   ax.text(x,y,'●' if b else '·',ha='center',va='center',color='white' if b else '#95a4ae',fontsize=15)
  right.text(0,y,textwrap.fill(', '.join(ids),width=44),va='center',fontsize=8)
  records.append(dict(profile=f'F{y+1:02d}',features=dict(zip([f[0] for f in features],bits)),method_ids=ids,count=len(ids)))
 ax.set_xticks(range(len(features)),[f[1] for f in features]);ax.xaxis.tick_top()
 ax.set_yticks(range(len(profiles)),[f'F{y+1:02d} · {len(ids)}' for y,(_,ids) in enumerate(profiles)])
 ax.set(xlim=(-.5,len(features)-.5),ylim=(len(profiles)-.6,-.6));ax.tick_params(length=0,pad=10)
 right.set(xlim=(0,1),ylim=ax.get_ylim());right.axis('off');right.set_title('Методы с одинаковым набором признаков',fontsize=10,pad=18)
 for s in ax.spines.values():s.set_visible(False)
 fig.text(.1,.025,'● = признак присутствует в выбранном варианте; · = не требуется / не входит в определение.',fontsize=9)
 return fig,records

def observation_code(o,cfg):
 mid=o['method_id'];r=ROWS[mid]
 if cfg['prefix']=='S':return r['signal_profile']
 if cfg['prefix']=='R':return ACODE[access(o,MM)]
 return SCODE[r['setup']]

def numeric_bf(cfg):
 oo=[o for o in OBS if o['block'] in ['G1','G2','G4']]
 order={c['y']:i for i,c in enumerate(cells(cfg))}
 ids=sorted({o['method_id'] for o in oo},key=lambda mid:(order[value(mid,cfg['ykey'])],mid))
 fig,axes=plt.subplots(1,3,figsize=(12,6.1),sharey=True);fig.subplots_adjust(left=.31,right=.98,top=.88,bottom=.12,wspace=.13)
 for ax,b in zip(axes,['G1','G2','G4']):
  ax.set_title(SHORT[b],fontsize=10,pad=15)
  for y,mid in enumerate(ids):
   if y%2==0:ax.axhspan(y-.48,y+.48,color='#f4f6f7',zorder=0)
  for o in [o for o in oo if o['block']==b]:
   v=metric(o,'spearman_rho')['value'];y=ids.index(o['method_id']);dot(ax,v,y,o['domain'])
   ax.annotate(f'{v:.3f} {observation_code(o,cfg)}',(v,y),xytext=(6,0),textcoords='offset points',va='center',fontsize=9)
  ax.set_xlim(0,1.15);ax.set_xticks([0,.5,1]);ax.set_xlabel('Spearman ρ');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
 axes[0].set_yticks(range(len(ids)),[mid+' '+textwrap.shorten(MM[mid]['name'].split(' / ')[0],width=30,placeholder='…') for mid in ids],fontsize=9)
 axes[0].set_ylim(len(ids)-.4,-.6)
 return fig,oo

def design_metrics(cfg):
 cc=cells(cfg);features,profiles=feature_profiles(cfg)
 return dict(map_points=len(cc),map_cells=len(cfg['xlabels'])*len(cfg['ylabels']),singletons=sum(c['count']==1 for c in cc),
             largest_group=max(c['count'] for c in cc),matrix_profiles=len(profiles),matrix_features=len(features))
