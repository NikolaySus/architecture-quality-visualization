"""Build the short, iterative mathematical problem statement."""
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
OUT = ROOT / "output/pdf/problem_statement_v0_1.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
for name, filename in [("Statement", "times.ttf"), ("StatementBold", "timesbd.ttf"),
                       ("StatementItalic", "timesi.ttf"), ("StatementBoldItalic", "timesbi.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
pdfmetrics.registerFontFamily("Statement", normal="Statement", bold="StatementBold",
                              italic="StatementItalic", boldItalic="StatementBoldItalic")

body = ParagraphStyle("body", fontName="Statement", fontSize=11.5, leading=15,
                      textColor=colors.HexColor("#233247"), spaceAfter=5)
heading = ParagraphStyle("heading", parent=body, fontName="StatementBold", fontSize=12,
                         leading=16, spaceBefore=6, spaceAfter=4)
title = ParagraphStyle("title", parent=heading, fontSize=17, leading=21, spaceAfter=5)
meta = ParagraphStyle("meta", parent=body, fontSize=9, leading=12,
                      textColor=colors.HexColor("#63758a"), spaceAfter=10)
equation = ParagraphStyle("equation", parent=body, fontName="StatementItalic", alignment=TA_CENTER,
                          fontSize=12, leading=18, spaceBefore=3, spaceAfter=6)
story = []


def p(text, style=body):
    if style is body:
        # Style notation in text nodes while preserving ReportLab markup.
        parts = re.split(r"(<[^>]+>)", text)
        for index in range(0, len(parts), 2):
            parts[index] = re.sub(r"(?<!\w)(Eval|[MWGLBFPZAHQSΠ])(?!\w)",
                                  r"<i>\1</i>", parts[index])
        text = "".join(parts)
    story.append(Paragraph(text, style))


p("Оценка качества модели текстовых эмбеддингов", title)
p("Математическая постановка · рабочая версия 0.1 · 03.11.2026", meta)

p("1. Исходные объекты", heading)
p("<b>M = (G, W)</b> - фиксированная обученная модель текстовых эмбеддингов. "
  "W обозначает её параметры; G - полное описание вычислений от текста до итогового "
  "вектора, включая токенизацию, pooling и нормализацию, если они применяются. "
  "Вспомогательные данные, необходимые для исполнения, считаются частью описания M.")
p("<b>L</b> - формальное представление целевого языка, которое может объединять "
  "несколько лингвистических ресурсов и связи между ними. Его структура и способ "
  "связывания с моделью и бенчмарком являются частью искомого решения.")
p("<b>B</b> - полная математическая спецификация конкретного бенчмарка: конечные "
  "данные и эталонные ответы, правила подготовки входов (включая prompts), способ "
  "сравнения эмбеддингов, метрика и порядок агрегации. Рассматриваются совместимые "
  "сочетания модели, языка и бенчмарка.")

p("2. Истинное качество и искомая оценка", heading)
p("Q(M, B) = Eval(M, B); &nbsp;&nbsp; Q<sub>F</sub>(M, L, B) = F(W, G, L, B).", equation)
p("<b>Eval</b> - заданная бенчмарком процедура измерения качества. Требуется построить "
  "оператор <b>F</b>, оценивающий ту же вещественную метрику без выполнения целевой "
  "оценки модели на B. F может анализировать данные и разметку B, представление L, "
  "веса W, граф G и связи между этими объектами.")

p("3. Ограничения на метод", heading)
p("Правила F фиксированы и не обучаются, не калибруются и не адаптируются по "
  "измеренным качествам для конкретной оцениваемой модели или бенчмарка. "
  "Построение метода допускает анализ всех его аргументов.")
p("Если используются прямые проходы или внутренние отклики модели, их входы "
  "задаются фиксированным набором либо заранее определённым правилом:")
p("P = Π(W, G); &nbsp;&nbsp; Z = A(M, P); &nbsp;&nbsp; "
  "Q<sub>F</sub> = H(W, G, Z, L, B).", equation)
p("<b>Π</b> - правило построения проб, независимое от L и B; <b>A</b> - фиксированная "
  "процедура получения откликов Z; <b>H</b> - правило итоговой оценки. Выбор входов "
  "и режима проб не зависит от целевой задачи. В варианте без запусков модели "
  "P и Z не используются. Конкретные Π, A и H являются частью решения.")

p("4. Проверка решения", heading)
p("Eval разрешено выполнять для независимого измерения ошибки метода. "
  "На заранее описанной проверочной коллекции S оцениваются расхождение "
  "Q<sub>F</sub> и Q, а при необходимости - согласованность ранжирования моделей. "
  "Состав S, допустимая ошибка и область применимости уточняются отдельно; "
  "универсальная гарантия для всех моделей и задач не предполагается.")
p("Практическая цель - сократить стоимость получения оценки относительно Eval. "
  "Сравнение учитывает подготовку модели и бенчмарка, построение проб и возможность "
  "повторного использования промежуточных результатов.")


SimpleDocTemplate(str(OUT), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm,
                  rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=20 * mm,
                  title="Оценка качества модели текстовых эмбеддингов",
                  author="").build(story)
pdf = PdfReader(OUT)
assert len(pdf.pages) == 1, f"Expected one page, got {len(pdf.pages)}"
print(OUT)
print(f"Pages: {len(pdf.pages)}")
