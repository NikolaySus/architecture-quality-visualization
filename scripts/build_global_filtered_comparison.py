"""Combined filtered edition; preserves the source registry and earlier PDFs."""
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
D=ROOT/'data/comparability'; OUT=ROOT/'output/pdf/narrow'; E=ROOT/'exports/comparability/global_filtered'; E.mkdir(parents=True,exist_ok=True)
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

ALL=R
BAD={r['method_id'] for r in ALL if r['metrics'].get('spearman_rho',1)<.4}
WITNESSES={mid:min((r for r in ALL if r['method_id']==mid and 'spearman_rho' in r['metrics']),key=lambda r:r['metrics']['spearman_rho']) for mid in BAD}

def keep(r):
 rho=r['metrics'].get('spearman_rho')
 return r['category']!='forward' and r['method_id'] not in BAD

R=[r for r in ALL if keep(r)]
primary=[r for r in R if PP[r['protocol']]['tier']!='auxiliary']
primary_ids=sorted({r['method_id'] for r in primary})
aux=[r for r in R if PP[r['protocol']]['tier']=='auxiliary']
removed=[dict(protocol=r['protocol'],method_id=r['method_id'],variant=r['variant'],reasons=(['green_forward'] if r['category']=='forward' else [])+(['method_has_rho_below_0.4'] if r['method_id'] in BAD else [])) for r in ALL if not keep(r)]
manifest={'filter':{'minimum_spearman':.4,'missing_spearman':'retain','exclude_category':'forward','unit':'method ID across all 235 original records, including auxiliary and green records','excluded_method_ids':sorted(BAD),'worst_case_witnesses':WITNESSES,'PPL':'use previously documented correlation with -PPL, not abs'},'records':R,'removed':removed,'primary_method_ids':primary_ids,'source_record_count':len(ALL),'retained_record_count':len(R),'primary_record_count':len(primary),'auxiliary_record_count':len(aux)}
(E/'global_filtered_registry.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
story=[]
page(story,'Оценщики O1-O3 · строгий отбор по методу',
 'Визуальный обзор и таблицы сравнимости объединены: каждый эксперимент содержит график, полные названия методов, точные корреляции и ссылку на источник. Глобальный фильтр: если хотя бы один опубликованный Spearman метода ниже 0,4, метод исключён во всех контекстах. Дополнительно исключены зелёные варианты «Прямой проход кандидата».')
story.append(tab([
 ['Правило отбора','Как оно применяется'],
 ['Единица отбора','ID метода во всём исходном реестре из 235 записей. Проверяются все задачи и варианты, включая вспомогательные и ранее скрытые зелёные строки. Один ρ < 0,4 исключает все записи этого ID; ρ = 0,4 допускается.'],
 ['Если Spearman отсутствует','Отсутствие Spearman не является провалом. Строка по Kendall остаётся только если у того же ID нигде нет ρ < 0,4. Для ID вообще без Spearman устойчивость относительно порога не проверена. Порог не применяется к Kendall.'],
 ['Что исключает зелёный цвет','Исключается категория forward из предыдущих документов. Производные и обученные proxy-предикторы остаются, хотя вычисление производных обычно также включает forward. Это фильтр по указанной цветовой категории, а не запрет любого запуска кандидата.'],
 ['Различие вариантов','LPZero (M25) имеет ρ=0,187 в C02: теперь исключён и его сильный GPT-2-вариант. Все backbones M46 рассматриваются как один ID; проверены все их опубликованные ρ. Forward LM-оценщика не является forward кандидата.'],
 ['Направление качества','Для GPT-2 сохраняется ранее заданное качество -PPL. Проверяется корреляция с ним, без взятия абсолютного значения. Отрицательная связь не проходит порог.'],
 ['Сравнимость','Результаты разных архитектурных выборок, targets и H не усредняются. ρ и τ могут задавать разные порядки. Фильтрация не делает оставшиеся методы универсальными лидерами.'],
 ['Охват после фильтра',f'{len(primary_ids)} ID в основном сравнении; {len(primary)} основных записей и {len(aux)} вспомогательных. Всего сохранено {len(R)} из {len(ALL)} записей. Вспомогательные результаты по-прежнему вне основного отбора.']
 ],[85,300]))
story.append(Spacer(1,10));story.append(para('Это устойчивость только в пределах собранных измерений. Методы проверены на разном числе задач; отсутствие провала у редко исследованного метода не доказывает превосходство. В конце для каждого исключённого по порогу ID приведён конкретный провал.','small'))
page(story,'Что осталось после глобального фильтра',
 'Из 32 ID предыдущего основного сравнения осталось 18. Ещё 3 ID представлены только вспомогательными таблицами. Важное различие: некоторые методы имеют проверенные Spearman, другие сохранены исключительно из-за отсутствия этой метрики.')
story.append(tab([
 ['Режим','Оставшиеся кандидаты / контроль','Основание и ограничение'],
 ['BERT / GLUE','M12 · LogSynFlow; M15 · EZNAS discovered proxy; M03 · FLOPs','C01/C02: LogSynFlow ρ=0.491/0.476; EZNAS 0.698/0.696. В C03 остался только FLOPs (0.652). M01 исключён из всех задач из-за слабых ViT-результатов.'],
 ['GPT-2 / WikiText-103','M02 · Decoder-only parameter count; M12 · LogSynFlow; M15 · EZNAS','C28: ρ=0.967 / 0.914 / 0.602. LPZero исключён по C02, несмотря на 0.980 здесь. Это действие заданного глобального правила, а не отрицание GPT-2-результата.'],
 ['CNN; допустимы короткие кривые','M52 · CoRA-Refine; M32 · Dextr; M17 · ZiCo','C05-C07: Refine сохраняется; Rank и AZ-NAS исключены из-за ViT. Для Refine нужны 1000 anchors × 30 эпох; одинакового охвата задач у него и Rank нет.'],
 ['CNN; отдельная авторская таблица','M33 · WRCor; M34 · WRCor voting','C15: WRCor ρ=0.812; voting 0.780/0.799. Это не доказательство устойчивости на тех задачах, где они не измерялись.'],
 ['Предикторы по H','M36 · GRAF + RF; M38 · GRAF + ZCP + RF','M36 имеет только Kendall. M38 имеет ρ=0.663 в C04 и Kendall в GRAF-контекстах. Нельзя приписывать всем H подтверждённый Spearman ≥ 0.4.'],
 ['einspace / CIFAR-10','M46 · Fine-tuned LM surrogate (Qin)','Все 8 вариантов M46 в реестре имеют ρ ≥ 0.679; ModernBERT-large + augmentation: 0.769. Подготовка по H и готовый LM; проверка на CV-цели.']
 ],[75,120,190]))
story.append(Spacer(1,14));story.append(tab([['Цвет','Что требуется при применении']]+[[f'<font color="{col}">● {name}</font>',desc] for (col,name),desc in zip([v for k,v in C.items() if k!='forward'],['Граф, размеры или счётчики операций.','Инициализированные веса.','Вычисление производных кандидата; входы/targets зависят от варианта.','Подготовленный оценщик получает граф или текст описания.','Подготовленный оценщик получает измеренные proxy или их комбинации.'])],[110,275]))

def graph(pid,rr):
 metric_name='spearman_rho' if all('spearman_rho' in r['metrics'] for r in rr) else 'kendall_tau'
 ordered=sorted(rr,key=lambda r:r['metrics'][metric_name])
 fig,ax=plt.subplots(figsize=(7.3,7.2))
 for y,r in enumerate(ordered):
  v=r['metrics'][metric_name];co=C[r['category']][0];ax.scatter(v,y,s=90,color=co)
  if r.get('sd',{}).get(metric_name):ax.errorbar(v,y,xerr=r['sd'][metric_name],color=co,capsize=3)
  ax.annotate(f'{v:.3f}',(v+r.get('sd',{}).get(metric_name,0),y),xytext=(8,0),textcoords='offset points',va='center',fontsize=11)
 labels=[r['method_id']+(' · '+r['variant'] if sum(x['method_id']==r['method_id'] for x in rr)>1 else '') for r in ordered]
 labels=[textwrap.fill(x,25) for x in labels]
 ax.set_yticks(range(len(rr)),labels,fontsize=11);ax.set_xlim(0,1.13);ax.set_ylim(-.7,max(len(rr)-.3,1));ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
 ax.set_xlabel('Spearman ρ' if metric_name=='spearman_rho' else 'Kendall τ · Spearman не опубликован',fontsize=11)
 if metric_name=='spearman_rho':ax.axvline(.4,color='#8696a0',ls='--',lw=1);ax.text(.4,1.01,'порог 0,4',transform=ax.get_xaxis_transform(),ha='center',fontsize=10,color='#617381')
 fig.tight_layout(pad=2);dest=E/(pid+'.png');fig.savefig(dest,dpi=170);fig.savefig(E/(pid+'.pdf'));plt.close(fig)
 return Image(str(dest),width=165*mm,height=163*mm)

for q in [p for p in P if p['tier']!='auxiliary' and rs(p['id'])]:
 rr=rs(q['id']);old=[r for r in ALL if r['protocol']==q['id']]
 missing=all('spearman_rho' not in r['metrics'] for r in rr)
 page(story,CODE[q['id']]+' · '+q['title'],
      '<b>Способ оценивания:</b> корреляция score оценщика с '+esc(q['target'])+'.<br/><b>Выборка / бюджет:</b> '+esc(str(q['sample']))+f'. Сохранено {len(rr)} из {len(old)} строк. '+('<b>Spearman не опубликован: порог 0,4 здесь не проверялся.</b>' if missing else 'У всех показанных ID нет ρ < 0,4 во всём исходном реестре.'))
 rows=[['Оцениваемый метод / вариант','Spearman ρ','Kendall τ']]
 for r in sorted(rr,key=lambda r:(r['method_id'],r['variant'])):
  rows.append([fullname(r)+'<br/><font size="9" color="#617381">'+esc(r['variant'])+'</font>',metric(r,'spearman_rho'),metric(r,'kendall_tau')])
 right=tab(rows,[137,40,43]);panel=Table([[graph(q['id'],rr),right]],colWidths=[170*mm,220*mm]);panel.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]));story.append(panel)
 story.append(Spacer(1,8));story.append(para(source(q)+'<br/>'+esc(q['notes']),'small'))
 story.append(para('Цвета - по легенде в начале. SD - стандартное отклонение, SE - стандартная ошибка; — = метрика не опубликована. Ранг на графике относится только к этому контексту.','small'))

for start in range(0,len(primary_ids),7):
 page(story,'Требования методов после глобального отбора · '+str(start//7+1),
 'Каталожные определения с оговорками для конкретных реализаций. В G1 Electra-реализации SNIP, GraSP, GradNorm, Fisher и LogSynFlow используют X без downstream-targets. Для P29 учитывается указанная авторами операция; требования CV-реализаций не переносятся автоматически на NLP.')
 rows=[['Полное название','Новый кандидат','Подготовка','Контексты после фильтра']]
 for mid in primary_ids[start:start+7]:
  a=ROWS[mid];req=(INPUTS[a['use_inputs']]+'; '+OPERATIONS[a['operation']]).replace('\n',' ')
  if mid=='M25':req='Только оставшийся GPT-2 вариант: производные кандидата; не зелёная FlexiBERT-формула.'
  contexts=', '.join(CODE[p['id']] for p in P if p['tier']!='auxiliary' and any(r['method_id']==mid for r in rs(p['id'])))
  rows.append([esc(mid+' · '+MM[mid]['name']),esc(req),esc((SETUPS[a['setup']]+'; '+REP[a['representation']]).replace('\n',' ')),contexts])
 story.append(tab(rows,[110,100,100,75]))
 story.append(para('Полный набор ZCP включает стоимость получения признаков, даже если benchmark отдаёт кэш. Поиск формул EZNAS/LPZero использует H. Forward LM-предиктора не равен forward оцениваемого кандидата.','small'))

for q in [p for p in P if p['tier']=='auxiliary' and rs(p['id'])]:
 page(story,'Вспомогательное сравнение · '+CODE[q['id']]+' · '+q['title'],
 'Прошло численный/цветовой фильтр, но сохраняет прежние ограничения сопоставимости. Не используется для основного отбора. '+esc(q['notes']))
 story.append(para('<b>Способ оценивания:</b> Kendall τ с '+esc(q['target'])+'. <b>Spearman не опубликован; порог не проверялся.</b><br/>'+source(q)))
 story.append(tab([['Метод','Вариант','Kendall τ']]+[[fullname(r),esc(r['variant']),metric(r,'kendall_tau')] for r in rs(q['id'])],[145,170,70]))

page(story,'Контексты без оставшихся методов',
 'Все семь ViT-контекстов исчезли: методы в них имеют хотя бы один Spearman ниже 0,4. Сохраняем сведения об исчезнувших экспериментах, чтобы не выдавать отсутствие страниц за отсутствие измерений.')
empty=[p for p in P if not rs(p['id'])]
story.append(tab([['Контекст','Источник']]+[[esc(CODE[p['id']]+' · '+p['title']),source(p)] for p in empty],[230,155]))
story.append(Spacer(1,12));story.append(para('Проверка шла по полному исходному реестру, до удаления зелёных строк и локального фильтра версии 08. Вспомогательные числа также участвуют в запрете, но не становятся основными доказательствами превосходства.','small'))
for start in range(0,len(BAD),7):
 page(story,'Глобально исключены по Spearman · '+str(start//7+1),
 'Для каждого ID показан минимальный зарегистрированный Spearman и конкретный контекст. Этого одного результата достаточно для исключения всех записей ID по новому правилу. Причина не является выводом о слабости на каждой задаче.')
 rows=[['Метод','Минимальный ρ','Контекст / вариант','Источник']]
 for mid in sorted(BAD)[start:start+7]:
  r=WITNESSES[mid];p=PP[r['protocol']]
  rows.append([esc(mid+' · '+MM[mid]['name']),f"{r['metrics']['spearman_rho']:.3f}",esc(CODE[p['id']]+' · '+p['title']+'; '+r['variant']),source(p)])
 story.append(tab(rows,[105,30,165,85]))
 if start==0:story.append(para('Результаты P27/C31 сохранены с опубликованной знаковой конвенцией и прежним вспомогательным статусом. Здесь они используются как консервативный запрет по правилу «хоть где-то», а не как основание общего ранжирования.','small'))
green_only=sorted({r['method_id'] for r in ALL}-{r['method_id'] for r in R}-BAD)
page(story,'Остальные ограничения отбора',
 'Эти ID не имеют зарегистрированного Spearman ниже 0,4, но исключены оставшимся ограничением на зелёную категорию forward.')
story.append(tab([['Метод','Причина']]+[[esc(mid+' · '+MM[mid]['name']),'Все доступные записи относятся к зелёной категории forward.'] for mid in green_only],[220,165]))
no_rho=sorted({r['method_id'] for r in R if not any(x['method_id']==r['method_id'] and 'spearman_rho' in x['metrics'] for x in ALL)})
story.append(Spacer(1,15));story.append(para('Сохранены без единого Spearman в реестре','title'))
story.append(para('; '.join(esc(mid+' · '+MM[mid]['name']) for mid in no_rho)))
story.append(para('Для этих ID новый порог не был проверен ни в одной задаче. Они не исключены, поскольку исходное условие применяется только при наличии Spearman. Вспомогательные ID M44/M45/M48 по-прежнему вне основного отбора.'))
excluded=[x for x in COVER if x['status']=='excluded'];papers={x['id']:x for x in load('papers')}
for start in range(0,len(excluded),4):
 page(story,'Исключены ещё при проверке сравнимости · '+str(start//4+1),
 'Эти методы не участвовали в общем численном сравнении до нового фильтра. Порог не устраняет причины исключения; отсутствие сопоставимого результата не означает слабость метода.')
 rows=[['Метод','Причина','Источник / место']]
 for x in excluded[start:start+4]:
  pid=x['review_locator'][:3];url=papers[pid]['canonical_url']
  if pid=='P17':url='https://arxiv.org/pdf/1910.11858v3'
  if pid=='P47':url='https://arxiv.org/pdf/2307.09365v1'
  rows.append([esc(x['method_id']+' · '+x['name']),esc(x['review']),'<link color="#286080" href="'+url+'">'+esc(x['review_locator'])+'</link>'])
 story.append(tab(rows,[100,205,80]))
 story.append(Spacer(1,12));story.append(para('Исходные PDF 06/07/08 и реестр результатов сохранены. Данная редакция не добавляет экспериментов и не утверждает статистической значимости различий. Прямая проверка качества текстовых эмбеддингов в этих группах отсутствует.','small'))
build(story,'09_global_filtered_combined.pdf','Оценщики O1-O3: глобальный порог Spearman 0.4 по ID метода')
print(json.dumps({'records':len(R),'primary_ids':len(primary_ids),'primary_records':len(primary),'auxiliary_records':len(aux)},ensure_ascii=False))
