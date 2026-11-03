import json
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_LINE_SPACING
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT=Path(__file__).resolve().parent.parent
(ROOT/'output').mkdir(parents=True,exist_ok=True)
doc=Document(ROOT/'inputs/overview_template.docx')
# Correct the unit established by directly counting the pinned query and qrels files.
cell=doc.tables[0].rows[21].cells[4]
for p in cell.paragraphs:
    for run in p.runs:
        run.text=run.text.replace('в ruMTEB 2 845 запросов.', 'в ruMTEB 1 692 запроса.')

SHA='46003a16451d7221b9df6c435311480a3b5d6ebd'
GH=f'https://github.com/embeddings-benchmark/mteb/blob/{SHA}/'
MIRACL='https://aclanthology.org/2023.tacl-1.63.pdf'
RUBQ='https://github.com/vladislavneon/RuBQ/tree/master/RuBQ_2.0'
RUSPEC='https://github.com/vladislavneon/RuBQ/blob/master/RuBQ_2.0/specification_v2.0.md'
RUPAPER='https://doi.org/10.1007/978-3-030-77385-4_32'
RUMTEB='https://arxiv.org/html/2408.12503v1#A3.SS6'

def hyperlink(p, label, url):
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    f=OxmlElement('w:rFonts');f.set(qn('w:ascii'),'Times New Roman');f.set(qn('w:hAnsi'),'Times New Roman');pr.append(f)
    sz=OxmlElement('w:sz');sz.set(qn('w:val'),'20');pr.append(sz)
    co=OxmlElement('w:color');co.set(qn('w:val'),'1F4E79');pr.append(co)
    r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

def para(cell, text, bold=False, first=False):
    p=cell.paragraphs[0] if first else cell.add_paragraph()
    p.paragraph_format.line_spacing=Pt(10.5)
    p.paragraph_format.space_after=Pt(1)
    r=p.add_run(text);r.font.size=Pt(10);r.bold=bold
    return p

p=doc.add_paragraph()
p.paragraph_format.page_break_before=True
p.paragraph_format.line_spacing=Pt(14)
p.paragraph_format.space_after=Pt(4)
r=p.add_run('Четыре подходящих бенчмарка поиска и переранжирования');r.bold=True;r.font.size=Pt(12)

t=doc.add_table(rows=1,cols=5);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
widths=[36,64,64,57,62]
for col,w in zip(t.columns,widths):col.width=Mm(w)
pr=t._tbl.tblPr
for tag in ['tblBorders','tblCellMar']:
    src=doc.tables[0]._tbl.tblPr.find(qn('w:'+tag))
    if src is not None:pr.append(deepcopy(src))
mar=pr.find(qn('w:tblCellMar'))
for el in mar:
    el.set(qn('w:w'),'65' if el.tag in (qn('w:left'),qn('w:right')) else '20')
headers=['Бенчмарк и версия','Набор и числа','Организация и использование','Метрики оценки','Валидация и ограничения']
for c,label in zip(t.rows[0].cells,headers):
    para(c,label,bold=True,first=True)
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E3EBF2');c._tc.get_or_add_tcPr().append(sh)
t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))

records=json.loads((ROOT/'data/selected_benchmarks.json').read_text(encoding='utf-8'))

for rec in records:
    rec['cols'][2].insert(1, 'Дополнительно: Recall@k, MRR@k, ' + ('nDCG@k' if rec['name']=='RuBQReranking' else 'MAP@k') + '; k = 1, 3, 5, 10, 20, 100, 1000.')
    cells=t.add_row().cells
    display_name=rec['name'].replace('RetrievalHardNegatives','Retrieval\nHardNegatives')
    para(cells[0],display_name,bold=True,first=True)
    para(cells[0],rec['kind'])
    for c,parts in zip(cells[1:],rec['cols']):
        for i,txt in enumerate(parts):
            p=para(c,txt,first=i==0)
            if 'лидер¹: ' in txt:
                prefix,score=txt.split('лидер¹: ')
                p.runs[0].text=prefix+'лидер¹: '
                r=p.add_run(score.rstrip('.'));r.font.size=Pt(10);r.font.color.rgb=RGBColor.from_string('0070C0');r.bold=True
                p.add_run('.').font.size=Pt(10)
    citation={'MIRACLRetrievalHardNegatives.v2':'[1, разд. 4.2–4.3]', 'MIRACLReranking':'[1, разд. 4.3]', 'RuBQRetrieval':'[2]', 'RuBQReranking':'[3, прил. A.3.6]'}
    para(cells[4],citation[rec['name']])
    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'C6EFCE' if rec['kind']=='Поиск' else 'FFEB9C');cells[0]._tc.get_or_add_tcPr().append(shade)
for row in t.rows:
    row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    for c,w in zip(row.cells,widths):c.width=Mm(w);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

p=doc.add_paragraph()
p.paragraph_format.space_before=Pt(3)
p.paragraph_format.space_after=Pt(3)
p.paragraph_format.line_spacing=Pt(11.5)
p.add_run('¹ Лидер среди эмбеддинговых моделей: ai-sage/Giga-Embeddings-instruct-10B-A1.8B-0826. Значения в шкале 0–1; проверены 15.09.2026.')

p=doc.add_paragraph()
p.paragraph_format.space_before=Pt(5)
p.paragraph_format.space_after=Pt(3)
p.paragraph_format.line_spacing=Pt(14)
r=p.add_run('Общая организация и использование данных');r.bold=True;r.font.size=Pt(12)
for label,text in [
    ('Retrieval (поиск). ', 'Даны общий корпус документов, набор запросов и qrels — эталонные связи «ID запроса — ID документа — релевантность». Для каждого запроса модель ранжирует документы общего корпуса. Qrels используются для оценки результата и не подаются модели как вход.'),
    ('Reranking (переранжирование). ', 'Для каждого запроса заранее задан свой список кандидатов с эталонными метками релевантности. Модель меняет порядок только внутри этого списка; самостоятельный поиск по полному корпусу в данный этап не входит. Метки используются для оценки, а не как вход модели.'),
    ('Для моделей эмбеддингов. ', 'В обеих схемах запрос и документы кодируются в векторы; документы сортируются по убыванию s(q,d) = cos(e(q), e(d)).')
]:
    p=doc.add_paragraph()
    p.paragraph_format.line_spacing=Pt(11.5)
    p.paragraph_format.space_after=Pt(3)
    p.add_run(label).bold=True
    p.add_run(text)

p=doc.add_paragraph()
p.paragraph_format.page_break_before=True
p.paragraph_format.line_spacing=Pt(14)
p.paragraph_format.space_after=Pt(6)
r=p.add_run('Общие пояснения к метрикам оценки');r.bold=True;r.font.size=Pt(12)

def metric_note(label,text):
    p=doc.add_paragraph()
    p.paragraph_format.line_spacing=Pt(12)
    p.paragraph_format.space_after=Pt(5)
    p.add_run(label).bold=True
    p.add_run(text)
    return p

metric_note('Общий принцип. ', 'Для каждого запроса ранжированный список сравнивается с эталонными метками релевантности. Метрика сначала вычисляется для отдельного запроса, затем усредняется по Q запросам с равным весом каждого. Во всех формулах ниже большее значение соответствует лучшему результату; диапазон — от 0 до 1.')
metric_note('Retrieval (поиск). ', 'В обеих задачах основная метрика — nDCG@10: она оценивает порядок релевантных документов в первых 10 результатах поиска по корпусу. Размер корпуса, число запросов и особенности обработки выдачи остаются в таблице. Дополнительные показатели Recall@k, MRR@k и MAP@k раскрывают полноту поиска, позицию первого релевантного результата и качество ранжирования всех релевантных результатов.')
metric_note('Reranking (переранжирование). ', 'Метрики вычисляются внутри заданного списка кандидатов. Для MIRACLReranking основная метрика — nDCG@10, для RuBQReranking — MAP@1000. Тип задачи сам по себе не определяет метрику. Статья ruMTEB 2024 года описывает MAP@10 для reranking; этот протокол отличается от рассмотренных реализаций. При сравнении результатов необходимо сохранять одну ревизию задачи и одинаковое k.')
metric_note('Обозначения. ', 'q — запрос; i — позиция в выдаче, начиная с 1; k — глубина отсечения; Q — число оцениваемых запросов; r(q,i) ∈ {0,1} — метка документа на позиции i. Rel(q) — множество эталонных релевантных документов; R(q) = |Rel(q)| > 0. Top-k(q) — первые k результатов. Если список короче k, за его концом принимается r(q,i) = 0.')

# Compact, editable native Word math. Linear fractions keep the page readable at 10 pt.
def mr(text):
    r=OxmlElement('m:r')
    rp=OxmlElement('w:rPr');sz=OxmlElement('w:sz');sz.set(qn('w:val'),'20');rp.append(sz);r.append(rp)
    txt=OxmlElement('m:t');txt.text=text;r.append(txt)
    return r
def summation(lower,upper,body):
    n=OxmlElement('m:nary');pr=OxmlElement('m:naryPr')
    ch=OxmlElement('m:chr');ch.set(qn('m:val'),'∑');pr.append(ch)
    loc=OxmlElement('m:limLoc');loc.set(qn('m:val'),'subSup');pr.append(loc);n.append(pr)
    for tag,txt in [('sub',lower),('sup',upper),('e',body)]:
        el=OxmlElement('m:'+tag);el.append(mr(txt));n.append(el)
    return n
def mathline(parts):
    p=doc.add_paragraph();p.paragraph_format.line_spacing=Pt(26);p.paragraph_format.line_spacing_rule=WD_LINE_SPACING.AT_LEAST;p.paragraph_format.space_after=Pt(1)
    m=OxmlElement('m:oMath')
    for part in parts:m.append(mr(part) if isinstance(part,str) else part)
    p._p.append(m)
    return p
metric_note('nDCG@10. ', 'Релевантные документы на высоких позициях получают больший вес: вклад позиции i равен 1/log₂(i+1). IDCG@10(q) — значение DCG@10 при идеальном порядке выдачи; деление на него нормирует оценку запроса.')
mathline(['(1)  DCG@10(q) = ',summation('i=1','10','r(q,i)/log₂(i+1)'),';   nDCG@10 = (1/Q) ',summation('q=1','Q','DCG@10(q)/IDCG@10(q)'),'.'])
metric_note('MAP@k. ', 'P(q,i) — точность среди первых i результатов. AP@k суммирует точность на позициях релевантных документов до k и делит сумму на R(q). MAP@k — среднее AP@k по запросам. Ниже используется нормировка на полное R(q), как в рассматриваемой реализации map_cut.')
mathline(['(2)  P(q,i) = (1/i) ',summation('j=1','i','r(q,j)'),';   AP@k(q) = (1/R(q)) ',summation('i=1','k','P(q,i)·r(q,i)'),';   MAP@k = (1/Q) ',summation('q=1','Q','AP@k(q)'),'.'])
metric_note('Recall@k. ', 'Доля эталонных релевантных документов, попавших в первые k результатов, усреднённая по запросам.')
mathline(['(3)  Recall@k = (1/Q) ',summation('q=1','Q','|Top-k(q) ∩ Rel(q)| / R(q)'),'.'])
metric_note('MRR@k. ', 'Учитывает только позицию первого релевантного документа. Если он находится на позиции t(q) ≤ k, RR@k(q) = 1/t(q); если в первых k результатах релевантных документов нет, RR@k(q) = 0.')
mathline(['(4)  MRR@k = (1/Q) ',summation('q=1','Q','RR@k(q)'),'.'])
metric_note('Оценка сходства. ', 'Для моделей эмбеддингов cos(u,v) = (u·v)/(‖u‖‖v‖) определяет порядок документов. Это функция ранжирования, а не итоговая метрика качества по эталонной разметке; её диапазон — от −1 до 1.')

p=doc.add_paragraph()
p.paragraph_format.space_before=Pt(6)
p.paragraph_format.space_after=Pt(4)
p.paragraph_format.line_spacing=Pt(14)
p.paragraph_format.keep_with_next=True
r=p.add_run('Список использованных источников');r.bold=True;r.font.size=Pt(12)

# Bibliographic descriptions follow GOST R 7.0.100–2018; numbering follows first citation.
sources=[
    ('MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages / X. Zhang, N. Thakur, O. Ogundepo [et al.]. — DOI 10.1162/tacl_a_00595. — Текст : электронный // Transactions of the Association for Computational Linguistics. — 2023. — Vol. 11. — P. 1114–1131. — URL: ', MIRACL),
    ('RuBQ 2.0 : спецификация формата записей (specification_v2.0.md). — Текст : электронный // GitHub : [сайт]. — URL: ', RUSPEC),
    ("The Russian-focused embedders' exploration: ruMTEB benchmark and Russian embedding model design / A. Snegirev, M. Tikhonova, A. Maksimova [et al.]. — Текст : электронный // arXiv. — 2024. — 22 Aug. — arXiv:2408.12503v1. — URL: ", RUMTEB),
]
for i,(description,url) in enumerate(sources,1):
    p=doc.add_paragraph()
    p.paragraph_format.left_indent=Mm(6)
    p.paragraph_format.first_line_indent=Mm(-6)
    p.paragraph_format.line_spacing=Pt(12)
    p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.keep_together=True
    p.add_run(f'{i}. {description}')
    hyperlink(p,url,url)
    p.add_run(' (дата обращения: 15.09.2026).')

out=ROOT/'output/ruMTEB_23_обоснованность.docx';doc.save(out)
assert len(doc.tables)==2 and len(t.rows)==5
print(out)
