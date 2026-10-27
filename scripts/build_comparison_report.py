"""Build the final context-local comparison tables and conditional visual shortlist."""
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
D=ROOT/'data/comparability'; OUT=ROOT/'output/pdf/narrow'; E=ROOT/'exports/comparability/final'; E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'protocols.json').read_text()); R=json.loads((D/'records.json').read_text()); COVER=json.loads((D/'coverage.json').read_text())
PP={p['id']:p for p in P}; CODE={p['id']:f'C{i+1:02}' for i,p in enumerate(P)}
C={'static':('#487b9e','Граф / размеры'), 'weights':('#8e69a4','Только веса'), 'forward':('#53996e','Прямой проход'), 'derivatives':('#c58b38','Производные'), 'learned_static':('#a74e69','Предиктор: граф / текст'), 'learned_dynamic':('#685caa','Предиктор: proxy / кривые')}
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
# Full names next to protocols; grouping only repeats of precisely the same method/variant set.
families=[]
for p in P:
 if p['tier']=='auxiliary':continue
 key=(p['paper_id'],tuple(sorted((r['method_id'],r['variant']) for r in rs(p['id']))),p['tier'])
 found=next((f for f in families if f['key']==key),None)
 if found:found['ps'].append(p)
 else:families.append({'key':key,'ps':[p]})
story=[]
page(story,'Какие оценщики сравнимы и как',
 'Таблица связывает способ проверки оценщика с конкретными методами O1-O3. Оценщик выдаёт score архитектуры; эталон - её качество после обучения. Затем статья вычисляет корреляцию score с эталоном на наборе архитектур. Это проверка ранжирования, а не доказательство точности абсолютного прогноза качества.')
story.append(tab([
 ['Правило','Применение в этом документе'],
 ['Общая экспериментальная основа','Совпадают архитектуры или явно сопоставимая схема выборки, задача, эталон качества, бюджет обучения и режим проверки. Общего названия метрики или общего baseline недостаточно.'],
 ['Когда строки можно схлопнуть','Повторения одного протокола с одним составом методов компактно перечисляются вместе. Каждая задача и каждый H остаются отдельным контекстом Cxx с собственными результатами. Числа не усредняются между контекстами.'],
 ['Что значит порядок','Внутри контекста выбранная корреляция позволяет упорядочить результаты с возможными ничьими. Spearman ρ и Kendall τ могут дать разные порядки. Это не запрет на сравнение; единого строгого порядка сразу по всем задачам не предполагается.'],
 ['Подготовка оценщика','H - пары «архитектура, измеренное качество» для обучения, калибровки или поиска формулы. Такой доступ отделён от вычислений на новой архитектуре. Сравнимый результат не означает одинаковую цену метода.'],
 ['Уровень доказательства','Общий эксперимент авторов; либо таблица авторского сопоставления с ограниченной прослеживаемостью. Вспомогательные результаты вынесены в конец и не используются для основного отбора. Независимое воспроизведение в этом обзоре не выполнялось.'],
 ['Полнота','56 исходных ID: 41 в основных численных контекстах, 4 только во вспомогательных, 11 исключены с конкретной причиной. 31 контекст и 235 записей «вариант × контекст». Нет статуса «не уточнено» в общем сравнении.']
 ],[75,310]))
story.append(Spacer(1,14));story.append(para('Сначала - таблица «способ оценивания → методы» с полными названиями; затем точные результаты и требования. Источники кликабельны. Отдельный визуальный обзор 06_promising_methods.pdf объясняет условный отбор кандидатов.'))
for j,f in enumerate(families,1):
 ps=f['ps'];q=ps[0];rr=rs(q['id']);mids=sorted({r['method_id'] for r in rr})
 page(story,f'Способ оценивания {j:02} · '+q['paper_id'])
 contexts='<br/>'.join(esc(CODE[x['id']]+' · '+x['title'])+'; '+esc(str(x['sample'])) for x in ps)
 methods='<br/>'.join(esc(mid+' · '+MM[mid]['name']) for mid in mids)
 metrics=', '.join('Spearman ρ' if k=='spearman_rho' else 'Kendall τ' for k in sorted({k for r in rr for k in r['metrics']}))
 story.append(tab([['Способ оценивания и границы сравнения','Оцениваемые методы'],[contexts+'<br/><br/><b>Эталон:</b> '+esc('; '.join(dict.fromkeys(x['target'] for x in ps)))+'<br/><b>Метрика:</b> '+metrics+'<br/><br/>'+source(q),methods]],[195,190]))
 story.append(Spacer(1,12));story.append(para('Объединено только представление повторений; каждое Cxx ниже содержит отдельный результат. '+esc(q['notes']),'small'))
# Exact numbers, full names, variants and both metrics. Page chunks prevent very long rows.
for q in [p for p in P if p['tier']!='auxiliary']:
 rr=rs(q['id'])
 for start in range(0,len(rr),12):
  page(story,CODE[q['id']]+' · '+q['title']+(' · продолжение' if start else ''),
       '<b>Эталон:</b> '+esc(q['target'])+' · <b>Выборка / бюджет:</b> '+esc(str(q['sample']))+'<br/>'+source(q))
  story.append(tab([['Метод: полное название','Вариант в этом эксперименте','Spearman ρ','Kendall τ']]+[[fullname(r),esc(r['variant']),metric(r,'spearman_rho'),metric(r,'kendall_tau')] for r in rr[start:start+12]],[130,145,55,55]))
  story.append(Spacer(1,10));story.append(para(esc(q['notes']),'small'))
  story.append(para('— = метрика не приведена в использованной таблице; SD - разброс повторов, SE - стандартная ошибка среднего. Ни SD, ни порядок округлённых средних не являются тестом значимости.','small'))
# Requirements are catalogue defaults; explicit variants cannot inherit them silently.
incs=[x for x in COVER if x['status']=='numeric_cohort']
for start in range(0,len(incs),7):
 page(story,'Требования методов · '+str(start//7+1),
 'Это определения вариантов исходного каталога. В G1 Electra-реализации SNIP, GraSP, GradNorm, Fisher и LogSynFlow используют X без downstream-targets; P29 отдельно сообщает forward/backward для своих адаптаций. GPT-2 LPZero использует производные, в отличие от FlexiBERT-формулы. Требования одного варианта не переносятся автоматически на другой.')
 rows=[['Метод','Новый кандидат','Подготовка','Граница варианта / уточнение']]
 for x in incs[start:start+7]:
  mid=x['method_id'];a=ROWS[mid]
  rows.append([esc(mid+' · '+x['name']),esc((INPUTS[a['use_inputs']]+'; '+OPERATIONS[a['operation']]).replace('\n',' ')),esc((SETUPS[a['setup']]+'; '+REP[a['representation']]).replace('\n',' ')),esc(a['note'])])
 story.append(tab(rows,[95,75,85,130]))
 story.append(para('X - реальные входы; objective - целевая функция/targets; синтетические входы не требуют реальных X. Forward LM-предиктора не является запуском оцениваемой архитектуры. Полный набор ZCP включает затраты получения признаков, даже если benchmark отдаёт их из кэша.','small'))
for q in [p for p in P if p['tier']=='auxiliary']:
 page(story,'Вне общего отбора · '+CODE[q['id']]+' · '+q['title'],esc(q['notes']))
 story.append(para('<b>Эталон:</b> '+esc(q['target'])+'; <b>выборка / бюджет:</b> '+esc(str(q['sample']))+'<br/>'+source(q)))
 story.append(tab([['Метод','Вариант','ρ, как указано','τ, как указано']]+[[fullname(r),esc(r['variant']),metric(r,'spearman_rho'),metric(r,'kendall_tau')] for r in rs(q['id'])],[130,145,55,55]))
excluded=[x for x in COVER if x['status']=='excluded'];papers={x['id']:x for x in load('papers')}
for start in range(0,len(excluded),4):
 page(story,'Не включены в общее сравнение · '+str(start//4+1),'Исключение относится к данному обзору и зафиксированному варианту. Оно не означает низкое качество метода или отсутствие любых исследований о нём.')
 rows=[['Метод','Почему нельзя включить','Проверенный источник / место']]
 for x in excluded[start:start+4]:
  pid=x['review_locator'][:3];url=papers[pid]['canonical_url']
  if pid=='P17':url='https://arxiv.org/pdf/1910.11858v3'
  if pid=='P47':url='https://arxiv.org/pdf/2307.09365v1'
  rows.append([esc(x['method_id']+' · '+x['name']),esc(x['review']),'<link color="#286080" href="'+url+'">'+esc(x['review_locator'])+'</link>'])
 story.append(tab(rows,[100,205,80]))
build(story,'07_comparability_tables.pdf','Какие оценщики сравнимы и как: O1-O3')

# A compact visual report: one shared ordering per panel, not an aggregate leaderboard.
short=[
 ('BERT; реальные тексты; без H для подготовки',['M22','M29'],['old_G1','old_G2','old_G4'],'Attention confidence: ρ=0.666/0.714/0.666 в трёх отдельных протоколах. SWAP-Score: 0.711 в P32.','M22 - устойчивый кандидат среди этих протоколов; M29 - лидер одной таблицы. Нет прямого основания объявить SWAP лучше LPZero из другой статьи.'),
 ('GPT-2; дешёвый контроль без запуска сети',['M02'],['gpt2_wikitext'],'Число decoder-параметров: ρ=0.967, τ=0.847 с -PPL. LPZero: 0.980/0.886.','M02 - обязательный простой baseline; близость средних не доказывает статистическую эквивалентность. LPZero требует другого варианта формулы и вычислений.'),
 ('CNN; нет исторических качеств H',['M51','M18'],['cora_nb201_0','cora_nb201_1','cora_nb201_2'],'CoRA-Rank лидирует среди вариантов без коротких обучающих кривых на трёх NB201 targets. AZ-NAS - сильная альтернатива.','Для CoRA нужны реальные X и производные; gate согласуется на наборе архитектур. Успех не переносится автоматически на ViT.'),
 ('CNN; допустимо обучение anchors',['M52'],['cora_nb201_0','cora_nb201_1','cora_nb201_2'],'CoRA-Refine повышает корреляции относительно Rank.','1000 anchors × 30 эпох - дополнительный бюджет. Выбирать только при допустимой подготовке по validation-кривым.'),
 ('Есть H; важна оценка без запуска кандидата',['M36','M38'],[p['id'] for p in P if p['id'].startswith('graf_')],'GRAF + RF использует граф; GRAF + ZCP + RF обычно повышает среднее τ.','M38 требует proxy, включая X, objective и производные. BRP-NAS даёт ничью 0.84 на IM16/H=1024; строгого универсального лидера нет.'),
 ('einspace; есть обучающие пары и готовый LM',['M46'],['old_G6'],'ModernBERT-large + augmentation: ρ=0.769, τ=0.628; лучшие значения в этой группе.','Дообучение LM по H, затем описание новой архитектуры. Проверено на CV-цели CIFAR-10, а не на NLP-моделях.')]
(D/'shortlist.json').write_text(json.dumps([dict(condition=a,method_ids=b,protocols=c,evidence=d,caution=e) for a,b,c,d,e in short],ensure_ascii=False,indent=2)+'\n')
main=[]
page(main,'Перспективные оценщики: выбор по условиям',
 'Результат обзора - условный список кандидатов, а не общий рейтинг. Основание: корреляция с качеством обученных архитектур в сопоставимых экспериментах, требования к применению и проверка границ переноса. Подробная таблица «способ оценивания → методы», числа и исключения: 07_comparability_tables.pdf.')
main.append(tab([['Условия','Кандидаты','Основание','Ограничение']]+[[esc(a),'<br/>'.join(esc(m+' · '+MM[m]['name']) for m in b),esc(d),esc(e)] for a,b,c,d,e in short],[65,75,115,130]))
page(main,'Легенда и правила отбора',
 'Цвет показывает, как получается оценка, а не насколько хорош метод. «Предиктор» обозначает обучение/обусловливание оценщика; исторические качества могут также понадобиться для поиска фиксированной формулы.')
main.append(tab([['Цвет / род','Что нужно для оценки новой архитектуры']]+[[f'<font color="{v[0]}">● {v[1]}</font>',d] for v,d in zip(C.values(),['Описание графа, размеры или счётчики операций.','Инициализированные веса; без входного batch.','Forward кандидата. Реальные или синтетические X зависят от варианта.','Производные кандидата; наличие targets зависит от варианта.','Обученный/обусловленный оценщик получает граф или текст описания.','Обученный оценщик получает измеряемые proxy; для них нужна новая сеть.'])],[115,270]))
main.append(Spacer(1,15));main.append(para('H - исторические пары архитектура-качество. Для EZNAS/LPZero поиск формулы использует H, хотя применение найденной формулы не является обучением нового предиктора. Для CoRA-Refine нужны кривые anchors. Для 3-shot LM H входит в prompt.'))
main.append(para('Правило отбора: лидерство внутри конкретной группы или полезный компромисс требований. Это редакционный выбор кандидатов на дальнейшую проверку, а не статистически доказанное превосходство. Нет общего балла, сравнения времени на разных устройствах или усреднения корреляций разных задач.'))
main.append(para('Проверены все 56 ID: 41 имеет основные сравнения; M44/M45/M48/M68 оставлены только во вспомогательных таблицах; 11 исключены с причинами. Неотобранный метод не объявляется слабым.'))
SHORT={'M01':'Parameters','M02':'Decoder parameters','M03':'FLOPs','M11':'NASWOT / Activation Distance','M18':'AZ-NAS','M25':'LPZero','M30':'SWAP-reg','M36':'GRAF + RF','M37':'ZCP + RF','M38':'GRAF + ZCP + RF','M39':'GRAF + ZCP + XGB','M42':'BRP-NAS','M51':'CoRA-Rank','M52':'CoRA-Refine','M69':'One-hot + RF'}
def label(r):
 name=r['variant'] if r['method_id'] in ['M46','M47','M34'] else SHORT.get(r['method_id'],r['name'])
 return r['method_id']+' '+name

def draw(name,ids,metric_name='spearman_rho'):
 fig,axes=plt.subplots(1,len(ids),figsize=(20,9.5),squeeze=False)
 for ax,pid in zip(axes[0],ids):
  rr=sorted([r for r in rs(pid) if metric_name in r['metrics']],key=lambda r:r['metrics'][metric_name])
  for y,r in enumerate(rr):
   v=r['metrics'][metric_name];co=C[r['category']][0];ax.scatter(v,y,s=85,color=co,zorder=3)
   if r.get('sd',{}).get(metric_name):ax.errorbar(v,y,xerr=r['sd'][metric_name],color=co,capsize=3)
   ax.annotate(f'{v:.3f}',(v,y),xytext=(6,0),textcoords='offset points',fontsize=11,va='center')
  ax.set_yticks(range(len(rr)),[textwrap.fill(label(r),27 if len(ids)>1 else 65) for r in rr],fontsize=11)
  lo=min([r['metrics'][metric_name] for r in rr]+[0])-.07; ax.set_xlim(lo,1.13)
  title=CODE[pid]+' · '+PP[pid]['title'];ax.set_title(textwrap.fill(title,48),fontsize=12,pad=15)
  ax.set_xlabel('Spearman ρ' if metric_name=='spearman_rho' else 'Kendall τ',fontsize=12);ax.axvline(0,lw=.7,color='#bbb');ax.grid(axis='x',alpha=.2);ax.spines[['top','left','right']].set_visible(False);ax.tick_params(axis='y',length=0)
 fig.tight_layout(pad=2,w_pad=3);fig.savefig(E/(name+'.png'),dpi=170);fig.savefig(E/(name+'.pdf'));plt.close(fig)
 return name

def plotted(title,body,name,ids):
 page(main,title,body);main.append(Image(str(E/(name+'.png')),width=385*mm,height=183*mm));main.append(para('Источники: '+'; '.join(source(PP[i]) for i in dict.fromkeys(ids)),'small'))
# Separate NLP panels avoid clutter and keep source names/negative values readable.
for pid,title,body in [
 ('old_G1','BERT: GLUE, входы OpenWebText','LPZero лидирует в этой таблице (ρ=0.748). Поиск формулы использовал 50 архитектур; независимость discovery и evaluation полностью не установлена. Не переносить преимущество на другой proxy-input.'),
 ('old_G2','BERT: GLUE, входы WikiText-103','Полная проверенная колонка: 17 методов. LPZero здесь имеет ρ=0.187; NASWOT/Activation Distance - 0.739, Attention confidence - 0.714. Ours не включён: вариант alpha нельзя надёжно отнести к M26 или M27.'),
 ('old_G4','BERT: взвешенный GLUE','SWAP-Score имеет ρ=0.711 в этой группе. Агрегация GLUE отличается от других протоколов, поэтому числа остаются отдельными. Ни один результат не является прямой проверкой качества текстовых эмбеддингов.'),
 ('gpt2_wikitext','GPT-2: качество как отрицательная perplexity','Меньшая PPL лучше. Для единого направления приведены -ρ и -τ исходной таблицы; это не абсолютные значения. В частности, положительная исходная корреляция GraSP с PPL превращается в отрицательную с качеством.')]:
 plotted(title,body,draw(pid,[pid]),[pid])
ids=['cora_nb201_'+str(i) for i in range(3)]
plotted('CNN: один live-протокол на 15 625 архитектурах','CoRA-Rank лидирует среди вариантов без anchor-кривых; Refine добавляет 1000 anchors × 30 эпох. На графике ρ; τ приведён в таблицах и поддерживает этот вывод. Fisher/Plain из внешнего источника исключены из live-группы.',draw('cora',ids),ids)
ids=[p['id'] for p in P if p['id'].startswith('cora_vit_')]
fig,ax=plt.subplots(figsize=(20,9.5));mids=['M51','M18','M01','M09']
for y,mid in enumerate(mids):
 for x,pid in enumerate(ids):
  r=next(r for r in rs(pid) if r['method_id']==mid);ax.scatter(x,y,s=1900,color=C[r['category']][0]);ax.text(x,y,f"{r['metrics']['spearman_rho']:.3f}",color='white',ha='center',va='center',fontsize=14,weight='bold')
ax.set_yticks(range(4),[m+' '+SHORT.get(m,MM[m]['name']) for m in mids],fontsize=13);ax.set_xticks(range(len(ids)),[textwrap.fill(PP[i]['title'].split(' / ',1)[1],14) for i in ids],fontsize=12)
ax.set(xlim=(-.7,len(ids)-.3),ylim=(3.7,-.7));ax.spines[:].set_visible(False);ax.tick_params(length=0,pad=15);fig.tight_layout();fig.savefig(E/'vit.png',dpi=170);fig.savefig(E/'vit.pdf');plt.close(fig)
plotted('Проверка переноса: на ViT победитель меняется','Одинаковый размер кругов; число - Spearman ρ; цвет - род метода. 200 AutoFormer-Tiny subnets в каждом target. Эти результаты ограничивают рекомендации по CoRA: успех на CNN не даёт общего преимущества на ViT.','vit',ids[:1])
plotted('WRCor: подвыборка и полный benchmark различаются','Показана колонка real полного NAS-Bench-201/CIFAR-10: WRCor 0.812, SJW 0.799. У SJW на подвыборке было 0.851. WRCor остаётся узким кандидатом одной авторской таблицы; исходный код требует X и objective.',draw('wrcor',['wrcor_nb201_full']),['wrcor_nb201_full'])
# All GRAF budgets in an exact-value matrix, without a cross-task average.
ids=[p['id'] for p in P if p['id'].startswith('graf_')]; mids=['M69','M36','M37','M38','M42']
fig,ax=plt.subplots(figsize=(20,9.5))
for y,pid in enumerate(ids):
 ax.axhspan(y-.48,y+.48,color='#f2f5f7' if y%2==0 else 'white')
 for x,mid in enumerate(mids):
  rr=[r for r in rs(pid) if r['method_id']==mid]
  if rr:
   r=rr[0];ax.text(x,y,f"{r['metrics']['kendall_tau']:.2f} ± {r['sd']['kendall_tau']:.2f}",ha='center',va='center',fontsize=13,color=C[r['category']][0])
  else:ax.text(x,y,'—',ha='center',va='center',color='#999')
ax.set_yticks(range(len(ids)),[PP[i]['title'].replace('NAS-Bench-','NB') for i in ids],fontsize=12);ax.set_xticks(range(5),[m+'\n'+SHORT[m] for m in mids],fontsize=12);ax.xaxis.tick_top();ax.set(xlim=(-.6,4.6),ylim=(len(ids)-.5,-.6));ax.spines[:].set_visible(False);ax.tick_params(length=0,pad=13);fig.tight_layout();fig.savefig(E/'graf_all.png',dpi=170);fig.savefig(E/'graf_all.pdf');plt.close(fig)
plotted('Предикторы: бюджет H и состав признаков','Среднее Kendall τ ± SD по 50 повторам. Каждая строка - отдельный контекст. BRP-NAS добавлен только там, где есть сопоставление в Table 28; конкретное совпадение split IDs не заявлено. Числа не доказывают значимость разницы.','graf_all',[ids[0],next(i for i in ids if '201_CIFAR-10' in i)])
plotted('einspace: обученный LM и другие оценщики','Общий evaluation set: Table 1 и Table 7 P14. 6 NAS runs для обучения / 1 validation / 1 test, около 9k пар суммарно. Лучший вариант ModernBERT-large + augmentation: ρ=0.769, τ=0.628. 3-shot LM не достигают этого уровня.',draw('einspace',['old_G6']),['old_G6'])
page(main,'Границы выводов и состав исключений','Кандидат в этом обзоре - метод для проверки в указанном режиме. Для новой задачи сначала нужен общий тест: одни архитектуры, один эталон после обучения, фиксированный H и split, одинаковая агрегация качества. Отдельно учитывать стоимость подготовки и оценки кандидата.')
main.append(tab([['Статус','Методы','Причина ограничения'],['Вспомогательные, вне основного отбора','M44 CATE; M45 Arch2vec; M48 ONNX-Net; M68 Hidden Covariance','ONNX-таблицы авторов не дают достаточной прослеживаемости общего rerun; RNN-график оставлен как опубликован из-за неоднозначной знаковой конвенции.'],['Исключены из общего сравнения','; '.join(esc(x['method_id']+' '+x['name']) for x in excluded),'Различаются оцениваемый объект/метрика; точный вариант, target или общий эксперимент не закреплены. Индивидуальные причины и ссылки приведены в конце 07_comparability_tables.pdf.'],['Узкие дополнительные кандидаты','M25 LPZero; M15 EZNAS; M33 WRCor','LPZero зависит от протокола и поиска формулы. EZNAS также требует поиска по H. WRCor силён в одной таблице; общего доказательства переноса нет.']],[70,160,155]))
main.append(Spacer(1,15));main.append(para('Ограничение цели: в использованных общих экспериментах нет прямой проверки качества текстовых эмбеддингов. Результаты GLUE, perplexity и CV помогают выбрать кандидатов, но не заменяют такую проверку.'))
build(main,'06_promising_methods.pdf','Перспективные оценщики O1-O3: условный отбор')
(E/'manifest.json').write_text(json.dumps({'protocols':len(P),'records':len(R),'scope':len(COVER),'grouped_table_rows':len(families),'outputs':['06_promising_methods.pdf','07_comparability_tables.pdf']},ensure_ascii=False,indent=2)+'\n')
