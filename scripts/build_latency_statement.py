"""Build the independent one-page latency prediction problem statement."""
import os
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/latency_problem_statement_v0_1.pdf'
font_dir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
for name, filename in [('Latency', 'times.ttf'), ('LatencyBold', 'timesbd.ttf'),
                       ('LatencyItalic', 'timesi.ttf'), ('LatencyBoldItalic', 'timesbi.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
pdfmetrics.registerFontFamily('Latency', normal='Latency', bold='LatencyBold',
                              italic='LatencyItalic', boldItalic='LatencyBoldItalic')
body = ParagraphStyle('body', fontName='Latency', fontSize=11.5, leading=15,
                      textColor=colors.HexColor('#233247'), spaceAfter=5)
heading = ParagraphStyle('heading', parent=body, fontName='LatencyBold', fontSize=12,
                         leading=16, spaceBefore=6, spaceAfter=4, keepWithNext=True)
title = ParagraphStyle('title', parent=heading, fontSize=17, leading=21, spaceAfter=5)
meta = ParagraphStyle('meta', parent=body, fontSize=9, leading=12,
                      textColor=colors.HexColor('#63758a'), spaceAfter=10)
equation = ParagraphStyle('equation', parent=body, fontName='LatencyItalic', alignment=TA_CENTER,
                          fontSize=12, leading=18, spaceBefore=3, spaceAfter=6)
story = []


def p(text, style=body):
    if style is body:
        parts = re.split(r'(<[^>]+>)', text)
        for index in range(0, len(parts), 2):
            parts[index] = re.sub(r'(?<!\w)(Mean|[MWGELBTFPSxτξ])(?!\w)',
                                  r'<i>\1</i>', parts[index])
        text = ''.join(parts)
    story.append(Paragraph(text, style))


p('Предсказание времени обработки запроса', title)
p('Математическая постановка · рабочая версия 0.1 · 03.11.2026', meta)

p('1. Исходные объекты', heading)
p('<b>M = (G, W)</b> - фиксированная модель текстовых эмбеддингов: W - её параметры; '
  'G - описание вычислений, включая токенизацию, pooling и нормализацию. '
  'Необходимые для исполнения вспомогательные данные входят в описание M.')
p('<b>x</b> - конкретный входной запрос: текст с уже заданными prompts и параметрами '
  'обработки. Если запрос содержит несколько текстов, их состав и порядок фиксируются. '
  'Правила усечения, padding и формирования вычислительных пакетов задаются явно.')
p('<b>E</b> - полная спецификация среды и режима исполнения: оборудование и память, '
  'программный стек и реализация операций, численная точность и квантование, '
  'параллелизм, пакетирование, кэширование и состояние прогрева. E также задаёт '
  'допустимую фоновую нагрузку и условия повторных измерений.')
p('<b>L</b> и <b>B</b> - формальное представление языка и спецификация бенчмарка из '
  'постановки оценки качества. Они являются необязательными источниками сведений о '
  'запросе; их использование и связь с оператором качества не требуются.')

p('2. Измеряемая величина', heading)
p('В базовом режиме модель загружена и прогрета, запрос обрабатывается без очереди. '
  'Измеряется время от наличия входного текста в памяти процесса до доступности '
  'итоговых эмбеддингов в памяти, указанной в E. В интервал входят подготовка входа, '
  'вычисления и необходимые передачи данных; завершение асинхронных операций '
  'учитывается. Иные границы измерения фиксируются как другой режим E.')
p('T(M, x, E) = Mean[τ(M, x, E, ξ)].', equation)
p('<b>τ</b> - длительность одного исполнения в секундах; <b>ξ</b> описывает вариации '
  'состояния среды, допускаемые E. <b>Mean</b> обозначает математическое ожидание '
  'по этим вариациям. T является средней задержкой обработки одного запроса '
  'при заданных условиях.')

p('3. Искомый оператор и ограничения', heading)
p('T<sub>F</sub>(M, x, E, L, B) = F<sub>T</sub>(W, G, x, E, L, B).', equation)
p('Требуется построить оператор F<sub>T</sub>, оценивающий T без выполнения '
  'измеряемого запроса x на модели M. Оператор может использовать любое достаточное '
  'подмножество входов и независимо анализировать структуру и параметры модели, '
  'формы тензоров, запрос и характеристики среды.')
p('Правила F<sub>T</sub> фиксированы; обучение и калибровка по измеренным временам '
  'оцениваемой модели не выполняются. Допускается заранее заданное профилирование '
  'среды и примитивных операций, общее для разных моделей. Если используются '
  'пробы самой модели, их входы и протокол определяются фиксированным правилом '
  'по M и E, независимо от x, L и B.')

p('4. Проверка решения', heading)
p('На проверочной коллекции S сочетаний модели, запроса и среды измеряется '
  'эталонная средняя задержка и оценивается ошибка T<sub>F</sub> в секундах '
  'и относительно T. Число повторов, разброс измерений, область применимости и '
  'допустимая ошибка фиксируются отдельно. Затраты на подготовку среды, анализ '
  'модели и получение прогноза учитываются раздельно.')

OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm,
                  rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=20 * mm,
                  title='Предсказание времени обработки запроса', author='').build(story)
pdf = PdfReader(OUT)
assert len(pdf.pages) == 1, f'Expected one page, got {len(pdf.pages)}'
print(OUT)
print('Pages:', len(pdf.pages))
