"""Three complete, auditable PDF reports with different editorial taxonomies."""
import sys,json,hashlib,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether,CondPageBreak
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from corpus import ROOT,load,exclusion_reason,access,metric
from charts import report_family_groups
from variant_charts import METHODS,MM,OBS,OPS,ACC,AK,ACODE,OP,operation_groups,access_groups,TAX
OUT=ROOT/'output/pdf/variants';OUT.mkdir(parents=True,exist_ok=True)
EX=ROOT/'exports/variants'
for name,file in [('DV','DejaVuSans.ttf'),('DV-B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+file))
pdfmetrics.registerFontFamily('DV',normal='DV',bold='DV-B',italic='DV',boldItalic='DV-B')
S={
 'title':ParagraphStyle('title',fontName='DV-B',fontSize=24,leading=30,spaceAfter=14),
 'h':ParagraphStyle('h',fontName='DV-B',fontSize=16,leading=20,spaceAfter=10,keepWithNext=True),
 'body':ParagraphStyle('body',fontName='DV',fontSize=10,leading=14,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='DV',fontSize=8,leading=11,spaceAfter=5),
 'cell':ParagraphStyle('cell',fontName='DV',fontSize=8,leading=10.6,spaceAfter=0),
}
CONFIGS=[
 dict(id='01_mechanisms',title='Механизмы и условия применения',subtitle='Операционная классификация · 6 групп',D='D_matrix',BF='BF_aligned',E='E_budget_panels',G6='G6_dots',taxonomy='operation',audience='Для анализа различий между методами и выбора класса механизма.',tradeoff='Действие над кандидатом важнее исторического названия семейства. LC-Net, ParZC и CoRA-Rank получают явно обоснованные новые позиции.'),
 dict(id='02_constraints',title='Выбор по доступным данным',subtitle='Классификация по входам · 3 группы',D='D_facets',BF='BF_heatmap',E='E_lines',G6='G6_table',taxonomy='access',audience='Для практического выбора: начать с доступных входов, затем проверить подготовку.',tradeoff='Группы N/U/T описывают применение. N не обещает отсутствие подготовки, предобучения или исторических качеств.'),
 dict(id='03_family_atlas',title='Атлас семейств и результатов',subtitle='Тематическая классификация · 5 семейств',D='D_profiles',BF='BF_heatmap',E='E_matrix',G6='G6_table',taxonomy='family',audience='Для обзорного чтения и точной сверки значений без множества scatter-панелей.',tradeoff='Тематические семейства сохранены, их неоднородность показана составом N/U/T. Одинаковая длина полос означает 100%, а не одинаковое число методов.'),
]
PAPERS={p['id']:p for p in load('papers')};GROUPS={g['block']:g for g in load('groups')}
class Report:
 def __init__(self,path,title,tag):self.path=path;self.title=title;self.tag=tag;self.story=[];self.figures=[];self.catalog_ids=[]
 def p(self,s,style='body'):return Paragraph(s,S[style])
 def text(self,s,style='body'):self.story.append(self.p(s,style))
 def heading(self,s):self.text(s,'h')
 def page(self):self.story.append(PageBreak())
 def table(self,headers,rows,widths):
  table=Table([[self.p(escape(str(c)),'cell') for c in headers]]+[[self.p(escape(str(c)),'cell') for c in row] for row in rows],colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
  table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ee')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f5f7')]),('TOPPADDING',(0,0),(-1,-1),3.5),('BOTTOMPADDING',(0,0),(-1,-1),3.5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#a8bac7'))]))
  self.story.append(table)
 def figure(self,name,height=128):
  from PIL import Image as PILImage
  path=EX/(name+'.png');im=PILImage.open(path);w,h=im.size;scale=min(267*mm/w,height*mm/h)
  self.story.append(Image(str(path),width=w*scale,height=h*scale,hAlign='LEFT'));self.figures.append(name)
 def source(self,blocks):
  for b in blocks:
   g=GROUPS[b];self.text(f"{b}: {g['paper_id']} · {escape(g['source_version'])} · {escape(g['locator'])}. <link href=\"{escape(g['url'])}\" color=\"#286080\">Первоисточник</link>.",'small')
 def build(self):
  def footer(c,doc):
   c.setFillColor(colors.HexColor('#62798a'));c.setFont('DV',8);c.drawString(15*mm,10*mm,'Качество архитектуры · '+self.tag+' · аудит 13.10.2026');c.drawRightString(282*mm,10*mm,str(doc.page))
  class Document(SimpleDocTemplate):
   def afterFlowable(self,flowable):
    if isinstance(flowable,Paragraph) and flowable.style.name=='h':
     self._heading_count=getattr(self,'_heading_count',0)+1
     key='heading_'+str(self._heading_count)
     self.canv.bookmarkPage(key);self.canv.addOutlineEntry(flowable.getPlainText(),key,level=0)
  doc=Document(str(self.path),pagesize=landscape(A4),leftMargin=15*mm,rightMargin=15*mm,topMargin=13*mm,bottomMargin=18*mm,title=self.title,author='НИР3+Э')
  doc.build(self.story,onFirstPage=footer,onLaterPages=footer)

def cover(r,cfg):
 r.text('Предсказание качества<br/>нейросетевой архитектуры','title');r.text(cfg['title'],'h');r.text(cfg['subtitle']+' · '+cfg['audience'])
 r.table(['В сравнении','Численные данные','Что исключено'],[[f'{len(METHODS)} методов из 72',f'{len(OBS)} наблюдения из 68; {len({o["method_id"] for o in OBS})} ID методов','M28, M40, M72; неподтверждённые наблюдения перечислены в конце']],[75,83,109])
 r.story.append(Spacer(1,4*mm));r.text('Единица каталогизации: метод в конкретном проверенном варианте. Единица численного результата: метод/вариант × протокол × бюджет. Один ID может иметь несколько вариантов; на графиках они не объединяются средним.')
 r.text('<b>Как читать входы.</b> N — без реальных примеров; U — реальные примеры без целевых ответов; T — реальные примеры и objective, включая self-supervised targets. Синтетические targets без реальных примеров относятся к N. Требования учитывают получение признаков нового кандидата, а не только чтение готового кэша.')
 r.text('<b>A / C · Стоимость.</b> Полных измерений query-time и совместимых пар setup/query нет. Поэтому числовой оси времени, 3D-оси «стоимость» и Парето-фронта нет. Запись C_setup + N_candidates × C_query остаётся схемой учёта, а не рассчитанной кривой. Предварительные времена сохранены в конце.')
 r.text('Числа унаследованы из handoff; новых обучений нет. Аудит входов уточнил 32 записи, остальные 37 допущенных классификаций унаследованы. 0 подтверждённых исследований качества text embeddings в корпусе; это граница корпуса, а не вывод об отсутствии таких работ.','small')

def map_page(r,cfg):
 r.page();r.heading('D · '+cfg['subtitle']);r.text(cfg['tradeoff']);r.figure(cfg['D'],120)
 if cfg['taxonomy']=='family':
  r.text('Каждый метод учтён ровно один раз. Число в сегменте — количество методов, а не средняя точность. D1–D5 расшифрованы в следующих пяти таблицах. Нулевые доли не нарисованы.','small')
 else:
  r.text('O1: статические дескрипторы; O2: фиксированная оценка сигналов; O3: обученное отображение признаков; O4: частичное обучение кандидата; O5: оценка с готовыми весами; O6: fitted scaling relation. Числа — методы, не независимые статьи. Ноль означает пустую ячейку этого корпуса.','small')
 r.text('Доступ описывает вариант каталога. Для численных панелей используется вариант наблюдения: например, исходный SynFlow относится к N, а FlexiBERT-реализация G1 — к U. Полные названия и ограничения приведены сразу далее.','small')

def catalog(r,cfg):
 groups=operation_groups() if cfg['taxonomy']=='operation' else access_groups() if cfg['taxonomy']=='access' else report_family_groups(METHODS)
 for gi,g in enumerate(groups):
  if gi==0:r.page()
  else:r.story.extend([Spacer(1,5*mm),CondPageBreak(70*mm)])
  group_start=len(r.story)
  r.heading(g['id']+' · '+g['title']);r.text(g.get('definition',g.get('note','')),'small')
  members=sorted(g['methods'],key=lambda m:(AK.index(m['data_access_at_use']),m['id'])) if cfg['taxonomy']!='access' else sorted(g['methods'],key=lambda m:(OP[m['id']],m['id']))
  r.text(f"Всего {len(members)}. Входы N/U/T относятся к применению; подготовка описана в той же строке. Pxx отсылает к списку источников. [А] — уточнено аудитом, [H] — унаследовано из handoff.",'small')
  rows=[]
  for m in members:
   a=m.get('access_review');name=m['mechanism'].split(' | ')[0]
   if a:name+='\nВариант: '+a['variant_scope']
   req=m['requirements_raw']
   ref=(a['paper_id']+'; '+a['locator']) if a else ', '.join(dict.fromkeys([m['origin_paper_id']]+m['evaluation_paper_ids']))
   rows.append([m['id']+' / '+ACODE[m['data_access_at_use']]+'\n'+OP[m['id']],name,req,('[А] ' if a else '[H] ')+ref]);r.catalog_ids.append(m['id'])
  r.table(['ID / '+g['id']+' / входы','Полное название и вариант','Применение и подготовка','Основание'],rows,[20,79,125,43])
  if len(members)<=5:
   section=r.story[group_start:];r.story[group_start:]=[KeepTogether(section)]

def numeric_pages(r,cfg):
 r.page();r.heading('B + F · Корреляции и входы по протоколам')
 r.text('Три независимых протокола NLP Transformer. Общая шкала помогает читать значения, но не создаёт общего рейтинга и не изолирует влияние входного датасета. N/U/T относится к реализации в этой панели.','small')
 r.figure(cfg['BF'],119)
 r.text('Показаны 25 допущенных наблюдений. Пробел / «—» означает отсутствие допущенного измерения, не ноль. Ось и цвет отображают исходные положительные ρ в диапазоне 0–1; отрицательные значения исключённых записей сохранены в архиве без изменения знака.','small');r.source(['G1','G2','G4'])
 r.page();r.heading('E · Что меняется с бюджетом исторических качеств')
 r.text('G5 · NAS-Bench-101 / CIFAR-10. RF одинакового типа, четыре набора признаков. Все 12 сочетаний метод × бюджет сохранены.','small');r.figure(cfg['E'],112)
 r.text('H — число архитектур с известным итоговым качеством, не число примеров X и не время. Среднее Kendall τ ± SD по 50 запускам; SD не является доверительным интервалом. Сравнение допустимо внутри G5. Рост H не пересчитывается в секунды.','small')
 r.text('При H=32: GRAF 0.54±0.08, one-hot 0.24±0.09; при H=1024: 0.71±0.01 и 0.60±0.02. Различия средних не доказывают статистическую значимость. ZCP-варианты требуют T при получении признаков нового кандидата; GRAF/one-hot — N.','small');r.source(['G5'])
 r.page();r.heading('G6 · Предикторы: две метрики без смешения шкал')
 r.text('Отдельная CV-задача CIFAR-10. LM используется как предиктор архитектур; это не делает оцениваемые архитектуры NLP-моделями. Четыре варианта M46 сохранены раздельно.','small');r.figure(cfg['G6'],112)
 r.text('Spearman ρ и Kendall τ — разные метрики; между ними не проводится соединяющая линия и не вычисляется среднее. Пунктирные круги обозначают релевантные CV-подходы. Для табличного варианта домен задан заголовком. N/U/T в таблице описывает входы нового кандидата, а не подготовку LM.','small')
 r.text('Около 9k пар; 6 train / 1 validation / 1 test NAS runs. Численные отличия 0.745 и 0.746 не превращаются в вывод о значимом превосходстве: разброс для этих строк не извлечён.','small');r.source(['G6'])

def synthesis(r,cfg):
 r.page();r.heading('Что можно заключить по этой структуре')
 r.text('<b>Входы и механизм — независимые вопросы.</b> В каталоге N: 30, U: 18, T: 21 метод. У обученных отображений O3 есть все три режима: 12 / 1 / 6. Поэтому ни «surrogate», ни «zero-cost» не задают требования к данным однозначно.')
 r.text('<b>Две стадии нельзя сворачивать в одну ось стоимости.</b> Ниже показаны разные виды подготовки; это четыре примера, а не универсальная классификация всех setup-процедур.')
 r.table(['Метод','Подготовка','Новый кандидат'],[
 ['M36 · GRAF + RF','Исторические пары архитектура–качество → обучение RF','Граф → GRAF → RF. Входы N.'],
 ['M37 · ZCP + RF','Исторические качества и ZCP → обучение RF','Сеть + X + objective → полный ZCP-вектор → RF. Входы T.'],
 ['M54 · LC-Net','Кривые других конфигураций → Bayesian network','Конфигурация x и эпоха t → прогноз. Входы N; частичная кривая кандидата не обязательна.'],
 ['M52 · CoRA-Refine','Короткое обучение anchors + validation-кривые → residual model','jacov и другие признаки нового кандидата → rank/refinement. Входы U.']],[43,108,116])
 r.story.append(Spacer(1,3*mm));r.text('<b>Гранулярность выбрана по различиям действий.</b> Разделение O1/O3 отделяет прямые дескрипторы от обученного отображения; перенос LC-Net и CoRA-Refine убирает ложное требование частичного обучения каждого кандидата. Более мелкие подсемейства сигналов можно читать по названиям, не добавляя десятки категорий на общую карту.','small')
 r.text('<b>Чего данные не подтверждают.</b> Общего победителя по всем протоколам, полной цены применения, причинного эффекта датасета и переноса на sentence embeddings. Структура отчёта не заменяет отсутствующие измерения.','small')

def references(r):
 r.page();r.heading('Источники и воспроизводимость')
 r.text('Пятьдесят источников исходного корпуса. Полные названия сохранены; данные handoff не подменены новой версией статьи. Дополнительная проверка входов имеет отдельные версии и локаторы ниже.','small')
 for p in PAPERS.values():
  text=escape(p['id']+' · '+p['title'])+'<br/><link href="'+escape(p['canonical_url'])+'" color="#286080">'+escape(p['canonical_url'])+'</link>'
  r.story.append(KeepTogether([r.p(text,'small'),Spacer(1,1.5*mm)]))
 r.page();r.heading('Проверка входов · источники уточнений')
 r.text('32 уточнения по первоисточникам/авторскому коду. Это проверка требований, не воспроизведение экспериментов. Остальные 37 допущенных классификаций унаследованы. Хеши загрузок: data/source_audit/downloads.json; решения: data/access_audit.json.','small')
 for a in load('access_audit'):
  if a['status']!='resolved':continue
  text=escape(a['method_id']+' · '+a['variant_scope'])+'<br/>'+escape(a['paper_id']+' · '+a['locator']+' · '+a['source_version'])+'<br/><link href="'+escape(a['url'])+'" color="#286080">Проверенный источник</link>'
  r.story.append(KeepTogether([r.p(text,'small'),Spacer(1,1*mm)]))
 r.text('Для G1 M04/M20/M21 проверены авторские runner/eval_rank_bert.py и predictor/measures/synflow.py в LPZero, commit 876432761a2ff67a77194018ebc88bdc42869974. Применение использует реальные тексты; свойства исходного CV-варианта сюда не копируются.','small')

def numerical_tables(r, observations=None, methods=None, access_fn=access):
 observations = OBS if observations is None else observations
 methods = MM if methods is None else methods
 for b in ['G1','G2','G4','G5','G6']:
  if b in ['G1','G2','G5']:r.page()
  else:r.story.append(Spacer(1,5*mm))
  section_start=len(r.story)
  r.heading('Численный реестр · '+b);r.source([b]);oo=[o for o in observations if o['block']==b]
  def value(o,key):
   m=metric(o,key)
   return '—' if not m else str(m['value'])+(' ± '+str(m['uncertainty'])+' SD' if m['uncertainty'] is not None else '')
  rows=[[o['id'],o['method_id']+' · '+o['variant_label'],ACODE[access_fn(o,methods)],o.get('n_train_predictor') or '—',value(o,'spearman_rho'),value(o,'kendall_tau')] for o in oo]
  r.table(['Наблюдение','Метод / вариант','Входы','H','Spearman ρ','Kendall τ'],rows,[27,113,17,20,45,45])
  r.text('«—» означает неприменимый или отсутствующий показатель; значения не заменяются нулём. H относится только к соответствующему протоколу, не к стоимости.','small')
  section=r.story[section_start:];r.story[section_start:]=[KeepTogether(section)]

def exclusions(r):
 r.page();r.heading('Архив · Исключённые наблюдения и времена')
 r.text('Исходные записи сохраняются для проверки. Метод может оставаться в каталоге по подтверждённому варианту, хотя конкретное наблюдение исключено. Ни одно значение из этой таблицы не участвует в основных численных графиках; исключение — корреляция строки, у которой исключён только timing.','small')
 rows=[]
 for o in load('observations'):
  reason=exclusion_reason(o)
  if reason or o['costs']:
   values='; '.join(m['name']+'='+str(m['value']) for m in o['metrics'])
   if o['costs']:values+='; reported time='+str(o['costs'][0]['value'])+' s'
   rows.append([o['id'],o['method_id'] or 'M26/M27',values,reason or 'Исключён только timing: аппаратура и полный scope не установлены.'])
 r.table(['Наблюдение','Метод','Исходные значения','Причина'],rows,[26,22,83,136])
 r.page();r.heading('Методы, не поддающиеся анализу в текущем корпусе')
 r.text('Три записи исключены из карты и всех основных сравнений. Это ограничение выполненной проверки, а не принципиальная невозможность анализа.')
 for a in load('access_audit'):
  if a['status']!='excluded':continue
  m=next(m for m in load('methods') if m['id']==a['method_id']);r.heading(m['id']+' · '+m['name']);r.text(escape(a['reason']));r.text('<link href="'+escape(a['url'])+'" color="#286080">Источник / попытка доступа</link> · '+escape(a['locator']),'small')

def build(cfg):
 r=Report(OUT/(cfg['id']+'.pdf'),cfg['title'],cfg['id'])
 cover(r,cfg);map_page(r,cfg);catalog(r,cfg);numeric_pages(r,cfg);synthesis(r,cfg);references(r);numerical_tables(r);exclusions(r);r.build()
 pages=len(PdfReader(r.path).pages)
 payload=dict(config=cfg,pdf=str(r.path.relative_to(ROOT)),pages=pages,figures=r.figures,method_ids=r.catalog_ids,observation_ids=[o['id'] for o in OBS],excluded_method_ids=['M28','M40','M72'],data_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*.json')})
 (EX/(cfg['id']+'_manifest.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');print(cfg['id'],pages,flush=True)
if __name__=='__main__':
 for cfg in CONFIGS:build(cfg)
