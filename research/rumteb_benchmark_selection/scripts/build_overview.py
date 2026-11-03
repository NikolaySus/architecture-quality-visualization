from pathlib import Path
import openpyxl
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parent.parent
book = openpyxl.load_workbook(ROOT / 'inputs/MTEB_rus_v1_1_23_benchmarks.xlsx', data_only=True)
rows = list(book.worksheets[0].iter_rows(min_row=6, max_row=28, values_only=True))
sources = {r[0]: r for r in book.worksheets[1].iter_rows(min_row=5, values_only=True) if r[0]}

names = {
 'MIRACL':'MIRACL (ru)', 'PARA_PLUS':'ParaPhraser Plus', 'RIA':'RIA News Dataset',
 'GEO':'Yandex Geo Reviews 2023', 'RUSCI':'RuSciBench (ru+en)',
 'INAPP':'Inappropriate Messages v3', 'RUREVIEWS':'RuReviews', 'KINO':'Kinopoisk / blinoff',
 'SENSITIVE':'Sensitive Topics v3', 'MASSIVE':'MASSIVE (ru)', 'CEDR':'CEDR v0.1.1',
 'PARA':'ParaPhraser (ручной)', 'STSB':'stsb-multi-mt (ru, DeepL)',
 'TERRA':'TERRa / RussianSuperGLUE', 'RUBQ':'RuBQ 2.0', 'STS22':'SemEval-2022 Task 8 (ru)'
}
units = {'пассажи':'пассажей', 'кластеры':'кластеров', 'новостные статьи':'статей',
 'отзывы':'отзывов','языковые записи':'языковых записей','сообщения':'сообщений',
 'рецензии':'рецензия','реплики':'реплика','тексты':'текстов',
 'пары заголовков':'пара заголовков','пары предложений':'пар предложений',
 'пары текстов':'пара текстов','вопросы':'вопросов','пары статей':'пар статей'}
categories = {'Retrieval':'Поиск','Reranking':'Переранжирование',
 'Classification':'Классификация','Clustering':'Кластеризация',
 'MultilabelClassification':'Многометочная классификация',
 'STS':'Семантическое сходство (STS)','PairClassification':'Классификация пар'}
reasons = [
 'Релевантность размечена носителями языка с контролем качества. Валидация v2 отдельно не установлена; объём — исходный корпус, не запросы.',
 'Подтверждены человеческие оценки релевантности MIRACL. Переносимость результата reranking на прикладную систему отдельно не доказана.',
 'Проверены ранжирование и генерация парафраз, но не классификация по шести рубрикам ruMTEB. Объём указан в кластерах, не в заголовках или парах.',
 'Исходная задача — генерация заголовков. Связь «заголовок — статья» не валидирована как поисковая релевантность; объём — полный исходный выпуск.',
 'Реальные отзывы и оценки пользователей подтверждены. Их валидность как эталона семантики или внешнего качества эмбеддингов не установлена.',
 'Используется первая рубрика организации. Её валидность как эталона семантической кластеризации отзывов не установлена.',
 'Статья обосновывает научную рубрикацию ГРНТИ и сравнивает модели. Внешняя валидность конкретной подвыборки ruMTEB не установлена.',
 'Постановка рубрикации OECD и сравнение моделей не доказывают внешнюю валидность конкретной адаптации ruMTEB.',
 'Классы ГРНТИ служат эталоном кластеров. Отдельная проверка валидности этой кластеризационной адаптации не найдена.',
 'Классы OECD служат эталоном кластеров. Отдельная проверка валидности этой кластеризационной адаптации не найдена.',
 'Для версии 3: Krippendorff α = 0,65 после отбора по уверенности и согласию. Подтверждена надёжность разметки, а не универсальность оценки.',
 'Есть противоречия между текстом и звёздной оценкой; реальное распределение классов неизвестно. Выпуск: 3 × 30 000; после отбора MTEB — 75 000.',
 'Указана работа по анализу тональности. Внешняя валидность конкретной выборки MTEB не установлена; в адаптации — 13 500 объектов.',
 'Обоснована таксономия тем, проверена согласованность разметки. Вывод ограничен этой таксономией; это отдельный набор от Inappropriate Messages.',
 'Описаны профессиональная локализация и контроль качества для NLU. Общая внешняя валидность ruMTEB не установлена; в статье ruMTEB — 16 521 реплика.',
 '18 сценариев входят в исходную разметку. Отдельная валидация MTEB-классификации сценариев вне исходной intent/slot-оценки не установлена.',
 'Отбор разметчиков, ≥3 аннотации на текст, устранение дублей. Это контроль разметки, не внешняя валидность; 9 410 — исправленная версия.',
 'Ручная разметка трёх классов парафраз. Преобразование классов в шкалу STS отдельно не валидировано; 7 227 train + 1 924 test.',
 'Перевод DeepL сохраняет исходные метки. Сохранение человеческих оценок сходства после перевода не подтверждено; в ruMTEB — 7 824 пары.',
 'Повторная разметка, human accuracy = 0,92 подтверждают исходную NLI-задачу, но не оценку сходством эмбеддингов; MTEB использует 307 validation-пар.',
 'Реальные вопросы, абзацы с ответами; исследованы paragraph retrieval и QA. Перенос на произвольный RAG не доказан; в ruMTEB 2 845 запросов.',
 'Подтверждены вопросы и абзацы с ответами. Отбор кандидатов и протокол reranking ruMTEB отдельно не валидированы; в адаптации 1 551 запрос.',
 'Krippendorff α = 0,77 (OVERALL) — для всего исследования, не отдельно ru. Исходно 287 русских пар, в ruMTEB — 265; 289 — число аннотаций.'
]

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(297), Mm(210)
sec.top_margin = sec.bottom_margin = Mm(6)
sec.left_margin = sec.right_margin = Mm(7)
normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(10)
normal.paragraph_format.space_after = Pt(0)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.line_spacing = Pt(10.3)
doc.core_properties.title = 'Обоснованность 23 бенчмарков ruMTEB'
doc.core_properties.subject = 'Сводка по трём листам MTEB_rus_v1_1_23_benchmarks.xlsx'
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(12)
r = p.add_run('Обоснованность 23 бенчмарков ruMTEB · MTEB(rus, v1.1)')
r.bold = True
r.font.size = Pt(12)
p.paragraph_format.line_spacing = Pt(13)

def link(p, text, url, bold=False):
    if not url:
        r = p.add_run(text); r.bold = bold; return
    el = OxmlElement('w:hyperlink')
    el.set(qn('r:id'), p.part.relate_to(url, RT.HYPERLINK, is_external=True))
    r = OxmlElement('w:r'); pr = OxmlElement('w:rPr')
    fonts = OxmlElement('w:rFonts')
    for a in ('ascii','hAnsi','cs'): fonts.set(qn('w:'+a), 'Times New Roman')
    pr.append(fonts)
    size=OxmlElement('w:sz');size.set(qn('w:val'),'20');pr.append(size)
    color=OxmlElement('w:color');color.set(qn('w:val'),'1F4E79');pr.append(color)
    if bold: pr.append(OxmlElement('w:b'))
    r.append(pr); t=OxmlElement('w:t');t.text=text;r.append(t);el.append(r);p._p.append(el)

table = doc.add_table(rows=1, cols=6)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.autofit = False
widths = [7, 55, 51, 25, 128, 17]
for col,w in zip(table.columns,widths): col.width=Mm(w)
pr=table._tbl.tblPr
margins=OxmlElement('w:tblCellMar')
for side,val in [('top',0),('bottom',0),('left',45),('right',45)]:
    el=OxmlElement('w:'+side);el.set(qn('w:w'),str(val));el.set(qn('w:type'),'dxa');margins.append(el)
pr.append(margins)
borders=OxmlElement('w:tblBorders')
for side in ['top','left','bottom','right','insideH','insideV']:
    el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'BCC8D3');borders.append(el)
pr.append(borders)
for c,t in zip(table.rows[0].cells,['№','Бенчмарк / категория','Исходный набор / объём','Вердикт¹','Подтверждение и граница вывода','Подходит']):
    c.text=t
    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E3EBF2');c._tc.get_or_add_tcPr().append(shade)
    for r in c.paragraphs[0].runs:r.bold=True
table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
for row,reason in zip(rows,reasons):
    number,bench,category,dataset,volume,unit,lang,verdict,explanation,sid=row
    cells=table.add_row().cells
    cells[0].text=str(number)
    p=cells[1].paragraphs[0]; p.add_run(bench); p.add_run('\n'+categories[category])
    p=cells[2].paragraphs[0]
    src=sources[sid]
    link(p,names[sid],src[9])
    count_unit = 'сообщения' if sid == 'SENSITIVE' else units[unit]
    p.add_run('\n'+f'{volume:,}'.replace(',',' ')+' '+count_unit)
    p=cells[3].paragraphs[0]
    link(p,'Достаточно' if verdict.startswith('Частично') else 'Не обоснован',src[10] or src[9])
    cells[4].text=reason
    if number % 2 == 0:
        for c in cells:
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'F3F6F8');c._tc.get_or_add_tcPr().append(shade)
    category_color = {'Retrieval': 'C6EFCE', 'Reranking': 'FFEB9C'}.get(category, 'FFC7CE')
    verdict_color = 'FFEB9C' if verdict.startswith('Частично') else 'FFC7CE'
    input_colors = (category_color, verdict_color)
    suitable_color = 'FFC7CE' if 'FFC7CE' in input_colors else 'FFEB9C' if 'FFEB9C' in input_colors else 'C6EFCE'
    for c, color in [(cells[1], category_color), (cells[3], verdict_color), (cells[5], suitable_color)]:
        cell_pr = c._tc.get_or_add_tcPr()
        for existing in list(cell_pr.findall(qn('w:shd'))):
            cell_pr.remove(existing)
        shade = OxmlElement('w:shd')
        shade.set(qn('w:fill'), color)
        cell_pr.append(shade)
for row in table.rows:
    row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    for c,w in zip(row.cells,widths):
        c.width=Mm(w);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

notes = [
 '¹ «Достаточно»: подтверждена разметка / исходная задача, не внешняя валидность MTEB-адаптации. «Не обоснован»: валидация не найдена, что не доказывает бесполезность. Объёмы исходных наборов ≠ тесты MTEB; сортировка не отражает качество.',
]
for i,txt in enumerate(notes):
    p=doc.add_paragraph(txt)
    if i==0:p.paragraph_format.space_before=Pt(3)
(ROOT/'output').mkdir(parents=True,exist_ok=True)
out=ROOT/'output/overview.docx'
doc.save(out)
print(out)
assert len(doc.tables)==1 and len(table.rows)==24
assert len(sources)==16, list(sources)
