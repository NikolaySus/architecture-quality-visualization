"""Short sourced review of Russian formal language representations."""
import os
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/russian_language_representations_v0_1.pdf'
font_dir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
for name, filename in [('Review', 'times.ttf'), ('ReviewBold', 'timesbd.ttf'),
                       ('ReviewItalic', 'timesi.ttf'), ('ReviewBoldItalic', 'timesbi.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
pdfmetrics.registerFontFamily('Review', normal='Review', bold='ReviewBold',
                              italic='ReviewItalic', boldItalic='ReviewBoldItalic')
body = ParagraphStyle('body', fontName='Review', fontSize=11.5, leading=15,
                      textColor=colors.HexColor('#233247'), spaceAfter=5)
heading = ParagraphStyle('heading', parent=body, fontName='ReviewBold', fontSize=12,
                         leading=16, spaceBefore=7, spaceAfter=4, keepWithNext=True)
title = ParagraphStyle('title', parent=heading, fontSize=17, leading=21, spaceAfter=5)
meta = ParagraphStyle('meta', parent=body, fontSize=9, leading=12,
                      textColor=colors.HexColor('#63758a'), spaceAfter=10)
source = ParagraphStyle('source', parent=meta, spaceAfter=5)
story = []


def p(text, style=body):
    story.append(Paragraph(text, style))


def entry(title_text, description, application, limitation, links):
    p(title_text, heading)
    p(description + ' <b>Для исследования:</b> ' + application +
      ' <b>Ограничение:</b> ' + limitation)
    p('Источники: ' + '; '.join('<link href="' + url + '" color="#405e7c">' + label + '</link>'
                               for label, url in links) + '.', source)


p('Формальные представления русского языка', title)
p('Обзор для оценки качества моделей текстовых эмбеддингов · версия 0.1 · 03.11.2026', meta)
p('Кандидаты на компоненты <i>L</i> отобраны по наличию формальной структуры и конкретных '
  'русскоязычных данных или реализаций. Ни один из ресурсов сам по себе не задаёт оператор '
  'оценки качества по весам. Пункты «Для исследования» ниже являются предложениями по '
  'использованию ресурсов в нашей постановке, а не подтверждёнными результатами такого оператора.')

entry('1. Universal Dependencies / UD Russian-SynTagRus',
      'Уровень морфологии и синтаксиса: леммы, части речи, грамматические признаки и '
      'типизированные зависимости между словами. Доступны русские деревья в формате '
      'CoNLL-U; UD-версия SynTagRus получена преобразованием исходной разметки.',
      'описывать морфологическую и синтаксическую структуру текстов бенчмарка, '
      'длины зависимостей и способы выражения участников ситуации.',
      'синтаксическая зависимость не определяет семантическую роль и не задаёт '
      'эквивалентность смыслов; UD-экспорт не следует отождествлять со всеми слоями SynTagRus.',
      [('документация UD Russian-SynTagRus', 'https://universaldependencies.org/treebanks/ru_syntagrus/')])

entry('2. RuWordNet',
      'Лексическая семантика в виде синсетов и отношений между ними: род-вид, '
      'часть-целое, антонимия, причина и другие связи. Объединяет слова и устойчивые '
      'сочетания, различая их значения; на сайте указан доступ к XML-данным.',
      'строить описание лексических замен и отношений между значениями, '
      'учитывать многозначность и семантические классы слов бенчмарка.',
      'отнесение слова в контексте к синсету требует отдельной процедуры; близость '
      'в тезаурусе не равна релевантности для любой задачи.',
      [('описание и отношения RuWordNet', 'https://www.ruwordnet.ru/ru')])

entry('3. Russian FrameBank',
      'Словарь лексических конструкций и корпус примеров с разметкой фреймов, '
      'семантических ролей, валентностных схем и морфосинтаксического выражения '
      'аргументов. Предоставляется табличная offline-версия.',
      'связывать синтаксическую форму с тем, кто совершает действие, над чем '
      'оно совершается и какие участники опущены; описывать смену ролей и залога.',
      'фреймовая разметка не является полной логической семантикой предложения; '
      'авторы отмечают неполноту некоторых полей и данных offline-выпуска.',
      [('данные и документация FrameBank', 'https://github.com/olesar/framebank')])

entry('4. SemOntoCor / SemETAP / теория «Смысл - Текст»',
      'SemOntoCor связывает тексты с базовыми семантическими структурами (БСемС): '
      'онтологическими концептами и отношениями, абстрагирующимися от части '
      'лексико-синтаксических различий. SemETAP входит в ETAP-4, созданный в рамках '
      'теории «Смысл - Текст»; онтология и правила поддерживают семантический анализ.',
      'использовать как основу для связывания языковых уровней и описания '
      'предикатно-аргументной структуры; различать прямой смысл и выводимые следствия.',
      'для нового бенчмарка нужны разметка, покрытие словаря и согласование '
      'онтологических понятий; БСемС и расширенная структура со следствиями различаются.',
      [('Boguslavsky et al., Dialogue 2023', 'https://dialogue-conf.org/media/5885/boguslavskyimplusetal083.pdf'),
       ('проект SemOntoCor', 'https://rscf.ru/project/24-18-00988/')])

story.append(PageBreak())
p('Семантические графы и формальные грамматики', heading)

entry('5. AMR / русскоязычная часть MASSIVE-AMR',
      'AMR представляет смысл высказывания графом концептов и отношений. '
      'MASSIVE-AMR содержит более 84 тысяч соответствий «текст - граф» для '
      '1 685 информационных запросов на более чем 50 языках, включая русский.',
      'описывать отношения между сущностями и событиями, сопоставлять '
      'семантические структуры запросов и анализировать межъязыковые соответствия.',
      'данные сосредоточены на информационных запросах; многочисленные языковые '
      'версии не означают столько же независимых ситуаций. AMR не сохраняет всю '
      'морфосинтаксическую информацию русского языка.',
      [('Regan et al., *SEM 2024', 'https://aclanthology.org/2024.starsem-1.1/'),
       ('данные MASSIVE-AMR', 'https://github.com/amazon-science/MASSIVE-AMR')])

entry('6. HPSG + MRS / Russian Resource Grammar',
      'HPSG задаёт грамматические ограничения через типизированные структуры '
      'признаков. В Russian Resource Grammar синтаксические анализы связаны с '
      'Minimal Recursion Semantics (MRS). Доступен открытый прототип грамматики.',
      'получать явно заданные правила композиции и проверять допустимые '
      'сочетания форм, аргументов и семантических ограничений.',
      'на странице описанного preview-выпуска 2011 года указан небольшой '
      'словарь. Современное покрытие и работоспособность инструментов нужно '
      'проверять отдельно; наличие формализма не означает готовый разбор любых текстов.',
      [('Russian Resource Grammar: описание выпуска', 'https://www.amlap.org/~tania/rrg/')])

entry('7. ABBYY Compreno: семантическая иерархия и слоты',
      'Модель объединяет языконезависимые семантические классы, языковую лексику '
      'и семантические роли. Опубликованы сокращённая иерархия классов в CSV и '
      'упрощённый список слотов с русскими и английскими примерами.',
      'заимствовать типизацию концептов и отношений как дополнительную '
      'схему описания языка и сопоставлять её с ролями других ресурсов.',
      'открытые схемы не эквивалентны полной базе знаний и работающему '
      'парсеру Compreno; воспроизводимость разметки бенчмарка требует отдельного решения.',
      [('официальные материалы Compreno Semantics', 'https://github.com/compreno-semantics')])

p('Предлагаемое сочетание и граница применения', heading)
p('Для первого прототипа предлагается сочетание <b>UD + RuWordNet + FrameBank</b>: '
  'морфосинтаксис, лексические значения и роли участников. <b>SemOntoCor</b> представляет '
  'особый интерес для единого семантического слоя; <b>AMR</b> - для компактных графов и '
  'межъязыкового сопоставления. HPSG/MRS и Compreno могут дать дополнительные правила и типы. '
  'Это выбор направления разработки, а не установленное превосходство ресурсов.')
p('Связи между слоями необходимо задавать явно: фрагмент текста, лемма, значение, '
  'роль и концепт. Автоматическое взаимно-однозначное соответствие между ресурсами '
  'не предполагается. Их применение к <i>B</i> допустимо для описания бенчмарка; '
  'входы проб модели по-прежнему определяются только <i>W</i> и <i>G</i>. '
  'Способ связи этого представления с параметрами модели остаётся частью решения.')

OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm,
                  rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=20 * mm,
                  title='Формальные представления русского языка', author='').build(story)
pdf = PdfReader(OUT)
assert len(pdf.pages) == 2, f'Expected two pages, got {len(pdf.pages)}'
assert sum(len(page.get('/Annots', [])) for page in pdf.pages) == 9
print(OUT)
print('Pages:', len(pdf.pages))
