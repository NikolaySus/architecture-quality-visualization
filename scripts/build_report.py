"""Build a self-contained Russian PDF and reproducible plot exports."""
import sys, io, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from corpus import load, ROOT, csv_bytes, comparison_methods, exclusion_reason
from charts import chart, family_overview_chart, report_family_groups, export
OUT=ROOT/'output/pdf'; OUT.mkdir(parents=True,exist_ok=True)
EX=ROOT/'exports'; EX.mkdir(exist_ok=True)
for suffix,font in [('', 'DejaVuSans.ttf'),('-Bold','DejaVuSans-Bold.ttf')]: pdfmetrics.registerFont(TTFont('DejaVu'+suffix,'/usr/share/fonts/truetype/dejavu/'+font))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyRU',fontName='DejaVu',fontSize=10,leading=15,textColor=colors.HexColor('#26364a'),spaceAfter=8))
styles.add(ParagraphStyle(name='TitleRU',parent=styles['BodyRU'],fontName='DejaVu-Bold',fontSize=25,leading=32,spaceAfter=17))
styles.add(ParagraphStyle(name='HeadRU',parent=styles['BodyRU'],fontName='DejaVu-Bold',fontSize=17,leading=23,spaceAfter=12,keepWithNext=True))
styles.add(ParagraphStyle(name='SmallRU',parent=styles['BodyRU'],fontSize=8,leading=11,spaceAfter=5))
styles.add(ParagraphStyle(name='CellRU',parent=styles['BodyRU'],fontSize=7.6,leading=10,spaceAfter=0,wordWrap='CJK'))
story=[]
def p(text,style='BodyRU'): return Paragraph(text,styles[style])
def text(t): story.append(p(t))
def heading(t): story.append(p(t,'HeadRU'))
def page(): story.append(PageBreak())
def table(headers,rows,widths):
    data=[[p(escape(str(c)),'CellRU') for c in headers]]+[[p(escape('' if c is None else str(c)),'CellRU') for c in row] for row in rows]
    t=Table(data,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dde9f1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f9')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#9bafc0'))]))
    story.append(t)
manifest=load('manifest'); papers=load('papers'); methods=load('methods'); observations=load('observations'); groups=load('groups'); all_methods=methods; methods=comparison_methods(); audit=load('access_audit'); pm={x['id']:x for x in papers}
def source(g):
    story.append(p(f"Источник: {g['paper_id']}, {escape(g['source_version'])}, {escape(g['locator'])}. <link href=\"{escape(g['url'])}\" color=\"#235c7d\">Открыть первоисточник</link>.",'SmallRU'))
def figure(fig,name,records,settings):
    for fmt in ['png','svg','pdf']: (EX/f'{name}.{fmt}').write_bytes(export(fig,fmt))
    data=export(fig,'png')
    width,height=fig.get_size_inches(); target_width=260*mm; target_height=target_width*height/width
    if target_height>125*mm: target_height=125*mm; target_width=target_height*width/height
    story.append(Image(io.BytesIO(data),width=target_width,height=target_height,hAlign='LEFT'))
    (EX/f'{name}.json').write_text(json.dumps(dict(corpus_version=manifest['version'],generated_at=datetime.now(timezone.utc).isoformat(),selection=settings,ids=[r['id'] for r in records]),ensure_ascii=False,indent=2))
    if records and 'metrics' in records[0]: (EX/f'{name}.csv').write_bytes(csv_bytes(records))
    else: (EX/f'{name}.csv').write_text(pd.DataFrame(records).to_csv(index=False))
    plt.close(fig)
story.append(Spacer(1,12*mm)); story.append(p('Предсказание качества<br/>нейросетевой архитектуры','TitleRU'))
text('Обзор исследовательского корпуса и объяснимые двумерные визуализации<br/>Редакция структуры отчёта: 13.10.2026')
text('<b>НИР3+Э · корпус от 29 сентября 2026 · версия '+manifest['version']+'</b>')
story.append(Spacer(1,8*mm))
table(['Источники','Методы в сравнении / всего','Наблюдения в корпусе','Подтверждённые text embedding'],[[len(papers),str(len(methods))+' / '+str(len(all_methods)),len(observations),0]],[65,65,65,65])
story.append(Spacer(1,8*mm))
text('Задача: при фиксированных данных и протоколе обучения предсказать итоговое качество или порядок архитектур до полного обучения. Численные результаты импортированы из handoff v0.2. Требования к входам уточнены по первоисточникам и авторскому коду 13.10.2026; новых экспериментов не проводилось.')
text('Главный результат: корпус позволяет изучать требования методов и зависимость качества ранжирования от числа меток. Полную зависимость «качество - стоимость» пока нельзя установить: известные тайминги неполны. Отсутствие данных отображается как пропуск.')
text('В основном сравнении 69 методов: пять точек D и пять таблиц расшифровки. Из 35 записей с пробелами 32 уточнены, 3 исключены и перечислены в конце с причинами. Исходные 72 записи и 68 наблюдений сохранены в корпусе. Приложение Streamlit и экспорт SVG/PNG/CSV используют тот же корпус и те же правила отбора.')
page(); heading('Как читать этот отчёт')
text('Одна численная точка - один метод/вариант, эксперимент и бюджет. Origin paper описывает происхождение механизма; evaluation paper содержит конкретное измерение. Между независимыми протоколами не строится общий рейтинг, тренд или Парето-фронт.')
table(['Представление','Готовность и ограничения'],[
['D · Карта методов','Пять семейств и таблиц, 69 допущенных методов. InTrain: синтетические входы и targets; подтверждён CV-протокол.'],
['E · Бюджет меток','G5: Kendall tau ± SD, 50 запусков. G7 вынесен в конец: target dataset не установлен.'],
['A · Время оценки','Полных проверенных query-time наблюдений нет. Предварительные времена сохранены в архивной таблице в конце.'],
['B · Доступ к данным','По одному протоколу; требования применения отдельно от discovery и исторических labels.'],
['C · Setup / новый кандидат','Нет совместимых полных пар затрат. Контекстные измерения доступны отдельно.'],
['F · Чувствительность','G1/G2/G4 разнесены по страницам. Это сравнение источников, а не контролируемый эксперимент смены входов.'],
['G8 · Контекст','Summary/search records вынесены в архивную таблицу в конце; в общее сравнение не входят.']],[58,202])
story.append(Spacer(1,5*mm))
text('Пунктирный круг с полупрозрачной заливкой: релевантный подход. Сплошной синий: наблюдение на NLP Transformer. Яркий розовый зарезервирован для моделей текстовых эмбеддингов; подтверждённых работ в корпусе 0. Это состояние корпуса, не доказательство отсутствия исследований.')
text('Уровни проверки источников унаследованы из handoff: '+', '.join(f'{k}: {v}' for k,v in sorted(Counter(p['verification_level'] for p in papers).items()))+'. F означает просмотр релевантных частей полного текста, A - abstract/страницу, M - библиографию. Полные авторские списки пока не извлечены; сохранены исходные отображаемые имена.')
page(); heading('D · Пять семейств методов')
text('Одна точка обозначает семейство D1-D5 и связана с таблицей на следующих страницах. Оси категориальные: семейство метода и доступ к данным. Для неоднородного семейства введена категория «разные требования»; число допущенных методов указано у каждой точки.')
fig,rr=family_overview_chart(methods); figure(fig,'D_five_families',rr,dict(plot='D',unit='family',taxonomy='data/report_families.json'))
text('Координата X учитывает получение входов для нового кандидата, включая ZCP-признаки; чтение кэша бенчмарка не считается data-free расчётом. Подготовка учитывается отдельно. «Разные требования» означает проверенную неоднородность, а не пробел в данных. Разметка / objective включает self-supervised targets; случайные targets без реальных примеров относятся к синтетическому входу.')

for family in report_family_groups(methods):
    page(); heading(f"{family['id']} · {family['title']}")
    text(f"<b>Методов: {len(family['methods'])}.</b> "+escape(family['note']))
    text('Входы: G - архитектура; W0 - случайные веса; Wp - обученные/наследованные веса; X - реальные примеры; Y - метки или целевая функция; H - исторические пары «архитектура-качество»; LC - частичная кривая обучения. R/N/? - класс применения; P0-P2 - редакционный приоритет.')
    table([f"ID ({family['id']})",'Название метода / механизм и источники','Входы и первоначальные затраты','Класс; приоритет'],[[m['id'],m['mechanism'],m['requirements_raw'],m['application_evidence']] for m in family['methods']],[18,99,111,32])
for block in ['G5']:
    page(); g=next(g for g in groups if g['block']==block)
    heading('E · '+('GRAF: ценность дополнительных меток' if block=='G5' else 'COLE: отдельный протокол label-efficiency'))
    oo=[o for o in observations if o['block']==block]
    fig,rr=chart(oo,'E','kendall_tau',title=g['search_space']+' / '+g['target_eval_dataset'])
    figure(fig,'E_'+block,rr,dict(plot='E',metric='kendall_tau',group=g['id'],scale='log2')); source(g)
    text('M69: RF+OH; M36: RF+GRAF; M37: RF+ZCP; M38: RF+ZCP+GRAF. Показаны средние ± SD, 50 запусков; SD не является доверительным интервалом. Стоимость получения меток не извлечена. Рост N не переводится автоматически в секунды.' if block=='G5' else 'M49: frozen CodeLlama-Python-7B, PCA128, MLP pairwise head; 10 folds × 10 seeds. Это предсказание качества CV-архитектур. Target dataset Table 1 остаётся неуточнённым; эту кривую нельзя объединять с G5. Runtime неизвестен.')
page(); heading('A и C · Стоимость: сравнение пока недоступно')
text('Нет измерений с подтверждёнными аппаратурой и полным составом candidate-query затрат; нет совместимых пар setup/query. Поэтому точки времени и Парето-фронт в основном сравнении не строятся. Предварительные тайминги G2 сохранены в конце как архивные сведения.')
text('C_total(N) = C_setup + N × C_candidate. Кэширование benchmark labels и ZCP уменьшает цену повторного использования, но не стоимость их первоначального получения. Для active learning число платных оценок нужно учитывать отдельно.')
page(); heading('B · Требования при применении и корреляция')
g=next(g for g in groups if g['block']=='G1'); oo=[o for o in observations if o['block']=='G1']
fig,rr=chart(oo,'B',title='G1 · Только протокол LPZero / FlexiBERT'); figure(fig,'B_G1',rr,dict(plot='B',metric='spearman_rho',group=g['id'])); source(g)
text('Входы FlexiBERT проверены по авторской реализации P28: head importance и компоненты DSS используют реальные тексты и backward от суммы hidden states; task labels не требуются. NLP SynFlow здесь также получает реальные входы. LPZero использует head/activation tensors; поиск формулы учитывается в setup. Проверка входов не означает воспроизведение численных результатов.')
story.append(p('<link href="https://github.com/pprp/LPZero/tree/876432761a2ff67a77194018ebc88bdc42869974/lpzero" color="#235c7d">Авторский код LPZero, commit 8764327</link>: runner/eval_rank_bert.py; runner/eval_searched_bert.py; predictor/measures/synflow.py.','SmallRU'))
for block in ['G1','G2','G4','G6']:
    page(); g=next(g for g in groups if g['block']==block); heading(block+' · Результаты одного протокола')
    oo=[o for o in observations if o['block']==block]
    fig,rr=chart(oo,name='spearman_rho',title=g['search_space']+' / '+g['target_eval_dataset']+' · '+g['paper_id'])
    figure(fig,'metric_'+block,rr,dict(plot='metric',group=g['id'],metric='spearman_rho')); source(g)
    text({'G1':'15 наблюдений; proxy-input OpenWebText, 500 архитектур. Затраты кандидата неизвестны. Корреляция со средним GLUE не доказывает качество предсказания retrieval или sentence embedding.',
    'G2':'Показана только допущенная часть исходных 8 наблюдений; WikiText-103, batch=128, length=256. Исходная отрицательная корреляция SynFlow сохранена в архиве. Числа таблицы не заменены числами текста.',
    'G3':'5 извлечённых строк; 200 GPT-2 архитектур. Положительные значения сохранены в ориентации P28. Преобразование относительно perplexity не установлено; abs(rho) не применяется.',
    'G4':'Показана только допущенная часть исходных 11 наблюдений; OpenWebText, 500 FlexiBERT архитектур, weighted GLUE. Отличия от G1/G2 могут объясняться несколькими условиями, а не только входным датасетом.',
    'G6':'6 вариантов; CV-цель CIFAR-10. RoBERTa/ModernBERT внутри предиктора не меняют класс кандидатов. Около 9k пар; 6 train / 1 validation / 1 test NAS runs. Варианты M46 сохранены раздельно.'}[block])
page(); heading('Выводы и конкретные пробелы')
text('Пять семейств сохранены как обзор механизмов. Аудит не даёт основания делить их только ради более однородных точек: D1 содержит статические признаки и обучаемые предикторы; D3 включает LC-Net без частичной кривой нового кандидата. Эти различия отражены в таблицах. Для прикладного выбора нужно читать обе стадии требований.')
text('<b>Бюджет информации важен.</b> В G5 при N=32 RF+GRAF даёт tau=0.54±0.08 против 0.24±0.09 у one-hot. При N=1024 значения равны 0.71±0.01 и 0.60±0.02. Это наблюдение одного протокола; SD не позволяет само по себе объявить статистическое превосходство.')
text('<b>Свойства метода зависят от этапа.</b> Дешёвое применение может требовать дорогого discovery, pretraining или исторических quality labels. «Zero-cost» - название семейства, не буквальное отсутствие вычислений. Для выбора под data-free постановку нужно проверять отдельно setup и новый кандидат.')
text('<b>Перенос на эмбеддинги остаётся гипотезой.</b> В корпусе есть NLP Transformer, но нет подтверждённого предсказания качества архитектур bi-encoder для retrieval/STS. STS-B внутри GLUE и embeddings архитектур не закрывают этот пробел.')
text('<b>Результат аудита входов.</b> 32 пробела закрыты; 3 записи исключены из сравнения. Проверка затронула конкретные варианты: свойства исходного ViT DSS не перенесены на NLP, а setup CoRA-Refine отделён от оценки нового кандидата. Остальные 37 классификаций унаследованы из handoff; это не повторная полная верификация всех 72 методов.')
text('Следующие содержательные проверки: точный вариант FLAN и его затраты; полный текст T-Razor; использование targets в EPE-NAS. Для численного сравнения остаются отдельные барьеры: вариант ZeroLM, G7 target dataset, ориентация G3 и полный runtime scope G2. Эти записи не участвуют в графиках основной части.')
page(); heading('Аудит требований · 13.10.2026')
text('Источник и область проверки каждой ранее незаполненной записи. Решение относится к указанному варианту, а не ко всем адаптациям метода. Проверенные тексты закреплены версией и SHA-256 в data/source_audit/downloads.json; авторский код — commit. Исходный handoff сохранён.')
for a in audit:
    if a['status']!='resolved': continue
    story.append(KeepTogether([p('<b>'+a['method_id']+' · '+escape(a['variant_scope'])+'</b>','SmallRU'),p(escape(a['paper_id']+' · '+a['locator']+' · версия '+a['source_version']),'SmallRU'),p('<link href="'+escape(a['url'])+'" color="#235c7d">Первоисточник / авторский код</link>','SmallRU')]))
page(); heading('Приложение A · Все 50 источников')
text('Полные названия и канонические ссылки. Отображаемые авторы унаследованы из handoff; et al. не заменяет полный список.')
for paper in papers:
    story.append(KeepTogether([p(escape(paper['id']+' · '+paper['title']),'BodyRU'),p(escape(paper['bibliography_raw'])+' · уровень '+paper['verification_level'],'SmallRU'),p('<link href="'+escape(paper['canonical_url'])+'" color="#235c7d">'+escape(paper['canonical_url'])+'</link>','SmallRU'),Spacer(1,3*mm)]))
page(); heading('Приложение B · Допущенные численные наблюдения')
text('Значения заявлены авторами и импортированы из handoff. Идентификатор G отсылает к источнику и locator в начале блока. «-» означает отсутствие извлечённого значения. Знак сохранён.')
first_group=True
for g in groups:
    if not any(o['block']==g['block'] and exclusion_reason(o) is None for o in observations): continue
    if not first_group: page()
    first_group=False
    heading(g['block']+' · '+g['id']); source(g)
    oo=[o for o in observations if o['block']==g['block'] and exclusion_reason(o) is None]
    rr=[]
    for o in oo:
        mt={m['name']:m for m in o['metrics']}
        def val(n):
            m=mt.get(n)
            return '-' if not m else str(m['value'])+(' ± '+str(m['uncertainty'])+' SD' if m['uncertainty'] is not None else '')
        rr.append([o['id'],o['method_id'] or 'M26/M27',o['variant_label'],o.get('n_train_predictor') or '-',val('kendall_tau'),val('spearman_rho')])
    table(['Observation','Метод','Вариант','N labels','tau','rho'],rr,[25,23,125,23,32,32])
page(); heading('Архив · Результаты вне общего сравнения')
text('Это исходные записи, а не сопоставимые точки. Причина исключения относится к наблюдению: метод может оставаться в карте D по проверенному варианту. Неизвестные времена не заменяются нулём.')
rows=[]
for o in observations:
    reason=exclusion_reason(o)
    if reason or o['costs']:
        values='; '.join(m['name']+'='+str(m['value']) for m in o['metrics'])
        if o['costs']: values+='; reported time='+str(o['costs'][0]['value'])+' s'
        rows.append([o['id']+' / '+o['block'],o['method_id'] or 'M26/M27',values,reason or 'Только timing исключён: аппаратура / полный scope не установлены; корреляция может оставаться в основном сравнении.'])
table(['ID / группа','Метод','Исходные значения','Причина исключения'],rows,[28,24,88,120])
page(); heading('Методы, не поддающиеся анализу в текущем корпусе')
text('Исключены из общего сравнения и пяти таблиц основной части. Это ограничение имеющихся сведений и выполненной проверки, а не утверждение о принципиальной невозможности анализа метода. Возврат возможен после устранения указанной причины.')
for a in audit:
    if a['status']!='excluded': continue
    m=next(m for m in all_methods if m['id']==a['method_id'])
    heading(m['id']+' · '+m['name'])
    text(escape(m['mechanism']))
    text(escape(a['reason']))
    story.append(p(escape(a['paper_id']+' · '+a['locator'])+'<br/><link href="'+escape(a['url'])+'" color="#235c7d">Проверенный источник / попытка доступа</link>','SmallRU'))
def footer(c,doc):
    c.setFont('DejaVu',8); c.setFillColor(colors.HexColor('#6a7d8f')); c.drawString(16*mm,11*mm,'НИР3+Э · Качество архитектуры · Корпус v0.2 / 29.09.2026'); c.drawRightString(281*mm,11*mm,str(doc.page))
path=OUT/'architecture_quality_report.pdf'
doc=SimpleDocTemplate(str(path),pagesize=landscape(A4),rightMargin=16*mm,leftMargin=16*mm,topMargin=14*mm,bottomMargin=19*mm,title='Предсказание качества нейросетевой архитектуры',author='Исследовательский корпус НИР3+Э')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(EX/'observations.csv').write_bytes(csv_bytes(observations))
print(path)
