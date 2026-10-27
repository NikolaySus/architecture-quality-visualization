"""Collapse evaluation protocols only when their pooled strict relation is total."""
import sys,json,hashlib
from pathlib import Path
from itertools import combinations
from collections import Counter
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from narrow_review import OBS,MM
from corpus import ROOT,load
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

METRICS={'spearman_rho':'Spearman ρ','kendall_tau':'Kendall τ'}
GROUPS={g['block']:g for g in load('groups')}
ATOMS={}; LABELS={};RECORDS={}
for o in OBS:
 node=o['method_id'] if o['method_id']!='M46' else o['method_variant_id']
 LABELS[node]=o['method_id']+' · '+MM[o['method_id']]['name']+((' / '+o['variant_label']) if o['method_id']=='M46' else '')
 for m in o['metrics']:
  key=(o['block'],o['n_train_predictor'],m['name'])
  assert node not in ATOMS.setdefault(key,{}),'Duplicate evaluation unit'
  ATOMS[key][node]=m['value'];RECORDS[(key,node)]=o['id']

def relation(keys):
 nodes=set().union(*(ATOMS[k] for k in keys));r={n:set() for n in nodes}
 for key in keys:
  for a,b in combinations(ATOMS[key],2):
   va,vb=ATOMS[key][a],ATOMS[key][b]
   if va>vb:r[a].add(b)
   elif vb>va:r[b].add(a)
 for k in sorted(nodes):
  for i in sorted(nodes):
   if k in r[i]:r[i]|=r[k]
 if any(n in r[n] for n in nodes):return 'cycle',[]
 if any(b not in r[a] and a not in r[b] for a,b in combinations(nodes,2)):return 'partial',[]
 return 'total',sorted(nodes,key=lambda n:-len(r[n]))

def solve():
 valid=[frozenset(c) for n in range(1,len(ATOMS)+1) for c in combinations(ATOMS,n) if relation(c)[0]=='total']
 maximal=[s for s in valid if not any(s<t for t in valid)]
 # In this corpus the maximal sets form a unique disjoint partition.
 assert Counter(k for s in maximal for k in s)==Counter({k:1 for k in ATOMS})
 return sorted(maximal,key=lambda s:min((k[0],0 if k[2]=='spearman_rho' else 1,k[1] or 0) for k in s))

OUT=ROOT/'output/pdf/narrow/04_evaluation_order.pdf'
for name,font in [('EO','DejaVuSans.ttf'),('EO-B','DejaVuSans-Bold.ttf')]:
 pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+font))
pdfmetrics.registerFontFamily('EO',normal='EO',bold='EO-B',italic='EO',boldItalic='EO-B')
styles={k:ParagraphStyle(k,fontName='EO-B' if k in ['title','h'] else 'EO',fontSize=s,leading=l,spaceAfter=6) for k,s,l in [('title',19,23),('h',12,16),('body',9,12),('cell',8.4,11.3),('small',8,10.5)]}
def p(t,s='body'):return Paragraph(t,styles[s])
def table(rows,widths=(88,179),headers=('Способ оценивания','Оцениваемые методы: от большей оценки к меньшей')):
 data=[[p(escape(h),'cell') for h in headers]]+[[p(c,'cell') for c in row] for row in rows]
 t=Table(data,colWidths=[v*mm for v in widths],repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ee')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f2f5f7'),colors.white]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 return t

def ordered_row(keys):
 keys=sorted(keys,key=lambda k:(k[1] or 0,0 if k[2]=='spearman_rho' else 1))
 block=keys[0][0];g=GROUPS[block]
 left='<b>'+block+' · '+escape(g['search_space'])+' / '+escape(g['target_eval_dataset'])+'</b><br/>'
 if block=='G5':left+='Kendall τ, среднее по 50 повторам.<br/>Объединены H = 32, 128, 1024.<br/>Значения справа идут в этом порядке; разброс - SD, не доверительный интервал.'
 elif len(keys)>1:left+='Объединены Spearman ρ и Kendall τ.<br/>Значения справа: ρ / τ.'
 else:left+=METRICS[keys[0][2]]+'; больше - лучше.'
 if g['proxy_input_dataset']:left+='<br/>Вход: '+escape(g['proxy_input_dataset'])+'.'
 if block=='G6':left+='<br/>6 train / 1 validation / 1 test NAS runs. Варианты M46 сохранены отдельно.'
 left+='<br/><br/>'+g['paper_id']+' · '+escape(g['locator'])+'.<br/><link href="'+g['url']+'" color="#286080">Первоисточник</link>'
 status,order=relation(keys);assert status=='total'
 lines=[]
 for i,node in enumerate(order,1):
  values=[]
  for k in keys:
   if node in ATOMS[k]:
    v=f'{ATOMS[k][node]:.3f}'
    if block=='G5':
     o=next(o for o in OBS if o['id']==RECORDS[k,node]);v+=' ± '+str(o['metrics'][0]['uncertainty'])
    values.append(v)
  lines.append(str(i)+'. '+escape(LABELS[node])+' <b>['+' / '.join(values)+']</b>')
 return [left,'<br/>'.join(lines)]

def build():
 sets=solve();assert len(sets)==7
 story=[p('Способ оценивания → оцениваемые методы O1-O3','title'),p('Линейный порядок по опубликованным численным оценкам. Строки объединены только при отсутствии противоречий и несравнимых пар. Позиция 1 имеет наибольшую оценку. Это не проверка статистического превосходства.','small')]
 story.append(table([ordered_row(s) for s in sets if next(iter(s))[0]=='G1']))
 story += [PageBreak(),p('Согласованные объединения и отдельный протокол','title'),table([ordered_row(s) for s in sets if next(iter(s))[0] in ['G2','G4','G5']]),Spacer(1,8),p('G2: обе метрики дают один порядок трёх методов. G5: порядок четырёх методов совпадает при каждом бюджете H. Числа разных метрик и бюджетов не усредняются. G4 остаётся отдельной строкой.','small')]
 story += [PageBreak(),p('Разные метрики - разные порядки','title'),table([ordered_row(s) for s in sets if next(iter(s))[0]=='G6']),Spacer(1,8),p('В G6 Spearman ставит ModernBERT-base выше ModernBERT-large (0.746 > 0.745), а Kendall - ниже (0.597 < 0.612). Поэтому объединять эти два способа нельзя. Варианты backbone и augmentation не схлопываются в одну запись M46.','body'),p('Результаты относятся к указанным реализациям и условиям. Рейтинг здесь сравнивает качество оценщиков архитектуры; это не порядок самих архитектур.','small')]
 story += [PageBreak(),p('Правило схлопывания и границы вывода','title')]
 for t in [
 '<b>Единица способа.</b> Протокол × метрика × бюджет H. Из 43 допущенных наблюдений получены 10 способов: G1 (ρ, τ), G2 (ρ, τ), G4 (ρ), G5 (τ при трёх H), G6 (ρ, τ). Отдельные варианты M46 являются отдельными оцениваемыми объектами.',
 '<b>Строгое сравнение.</b> Для каждого способа проводится ребро A → B, если опубликованное значение A строго больше B. Равенство округлённых значений само по себе не задаёт строгого порядка. Затем для объединения берутся все рёбра и их транзитивное замыкание.',
 '<b>Условие.</b> Не должно быть циклов; для любой пары различных объектов должен существовать путь ровно в одном направлении. Это равносильно единственному топологическому порядку. Несравнимые пары нельзя произвольно расставлять, а противоречия нельзя устранять усреднением.',
 '<b>Полнота проверки.</b> Проверены все 1023 непустых подмножества 10 способов. Найдены 7 максимальных по включению допустимых наборов; в этом корпусе они не пересекаются и образуют единственное разбиение. Объединены только две метрики G2 и три бюджета G5. Каждый из 10 способов представлен ровно один раз.',
 '<b>Между протоколами.</b> Совпадающий ID использован лишь для проверки возможности общего порядка; это не утверждение эквивалентности реализаций. Ни одно объединение разных G не прошло даже формальную проверку. Поэтому перенос численного превосходства между задачами здесь не выполняется.',
 '<b>Что именно доказано.</b> Согласованность порядка опубликованных точечных оценок в извлечённой выборке. Для G5 использованы средние; SD не позволяет автоматически заключить значимость различий. Новые результаты из статей в этом документе не извлекались.'
 ]:story.append(p(t))
 story.append(table([
 ['G1: ρ + τ','M20 / M23: по ρ 0.175 > 0.171, по τ 0.021 < 0.050. Противоречие.'],
 ['G1 + G2; G2 + G4','M11 / M22: G1 и G4 ставят M22 выше M11; обе метрики G2 дают обратный порядок.'],
 ['G1 τ + G4 ρ','Нет порядка между M29 SWAP-Score и M25 LPZero: оба выше M22, но связь между ними не установлена. Для G1 ρ + G4 дополнительно меняется порядок M10 / M11.'],
 ['G5 + G6','M38 общий, но M36 и M39 оба ниже M38 и между собой не сравнимы. Остальные несвязанные протоколы также оставляют несравнимые пары.']
 ],headers=('Необъединённые способы','Пример препятствия'),widths=(62,205)))
 story += [PageBreak(),p('Методы без строки численного порядка','title'),p('24 из 56 ID имеют допущенные численные результаты (27 объектов с учётом четырёх вариантов M46). Для остальных 32 ID ниже нет достаточных допущенных данных в текущей выборке. Это ограничение корпуса, а не утверждение, что метод невозможно оценить. Эти строки не являются рейтингами.','body')]
 observed={o['method_id'] for o in OBS};missing=sorted(set(MM)-observed)
 rows=[]
 for mid in missing:
  reason='Нет извлечённого допущенного численного результата.'
  if mid=='M02':reason='G3: не установлена ориентация корреляции с perplexity.'
  elif mid in ['M26','M27']:reason='Численная строка ZeroLM не закреплена за вариантом alpha.'
  elif mid=='M49':reason='G7: не установлен целевой dataset таблицы.'
  elif mid in ['M50','M51','M52']:reason='G8: сводные результаты поиска, вне сопоставимого протокола корреляций.'
  elif mid=='M19':reason='Не подтверждены условия входов извлечённой NLP-адаптации.'
  rows.append([escape(mid+' · '+MM[mid]['name']),reason])
 story.append(table(rows,widths=(128,139),headers=('Метод O1-O3','Почему отсутствует в основном порядке')))
 story.append(p('M28, M40 и M72 ранее исключены из анализируемых 56 методов и сюда не добавлены. O4-O6 находятся за границами темы. Аудит исходных данных: 13.10.2026; построение этой таблицы: 26.10.2026.','small'))
 def footer(c,d):
  c.setFont('EO',8);c.setFillColor(colors.HexColor('#62798a'));c.drawString(15*mm,9*mm,'O1-O3 · способы оценивания · 26.10.2026');c.drawRightString(282*mm,9*mm,str(d.page))
 OUT.parent.mkdir(parents=True,exist_ok=True)
 SimpleDocTemplate(str(OUT),pagesize=landscape(A4),leftMargin=15*mm,rightMargin=15*mm,topMargin=13*mm,bottomMargin=17*mm,title='Способы оценивания методов O1-O3',author='').build(story,onFirstPage=footer,onLaterPages=footer)
 payload={'checked_subsets':2**len(ATOMS)-1,'atomic_ways':len(ATOMS),'rows':[{'ways':[list(k) for k in sorted(s,key=str)],'order':relation(s)[1]} for s in sets],'methods_with_results':sorted(observed),'methods_without_results':missing,'observation_ids':[o['id'] for o in OBS],'inputs_sha256':{n:hashlib.sha256((ROOT/'data'/n).read_bytes()).hexdigest() for n in ['observations.json','narrow_method_audit.json','groups.json']}}
 (ROOT/'exports/narrow/04_evaluation_order.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(OUT)
if __name__=='__main__':build()
