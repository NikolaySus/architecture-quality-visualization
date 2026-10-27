"""Build three source-audited O1-O3 PDFs and the classification comparison."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from xml.sax.saxutils import escape
from collections import Counter
import matplotlib.pyplot as plt
from PIL import Image as PILImage
from reportlab.platypus import Image,KeepTogether,Spacer,CondPageBreak,TableStyle
from reportlab.lib.units import mm
from pypdf import PdfReader
from corpus import ROOT,load,exclusion_reason
from charts import export
from narrow_review import *
from variant_charts import e_budget_panels,e_lines,e_matrix,g6_dots,g6_table
from scripts.build_report_variants import Report,numerical_tables

OUT=ROOT/'output/pdf/narrow';EX=ROOT/'exports/narrow'
PAPERS={p['id']:p for p in load('papers')}

class NarrowReport(Report):
 def figure(self,name,height=123):
  p=EX/(name+'.png');im=PILImage.open(p);w,h=im.size;s=min(267*mm/w,height*mm/h)
  self.story.append(Image(str(p),width=w*s,height=h*s,hAlign='LEFT'));self.figures.append(name)

def savefig(name,result):
 fig,records=result
 for fmt in ['png','svg','pdf']:(EX/(name+'.'+fmt)).write_bytes(export(fig,fmt))
 (EX/(name+'.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 plt.close(fig)

def link(url,label):return '<link href="'+escape(url)+'" color="#286080">'+escape(label)+'</link>'

def cover(r,c):
 r.text('Предсказание качества<br/>нейросетевой архитектуры','title')
 r.heading(c['title']);r.text(c['question'])
 r.table(['Границы обзора','Численные свидетельства','Основание'],[[f'{len(METHODS)} методов: O1 = 3, O2 = 34, O3 = 19',f'{len(OBS)} наблюдения; {len({o["method_id"] for o in OBS})} ID методов','Узкая версия 01_mechanisms.pdf; состав по исходным ID']],[90,82,95])
 r.text('Рассматриваются статические дескрипторы, фиксированные proxy-оценки и предикторы качества. O1-O3 фиксируют состав обзора; новые категории описывают различия внутри этого состава. Исследование источников уточняет признаки, но не добавляет новые измерения.')
 r.text('<b>Единица анализа.</b> Метод в указанном варианте. Компонент, составной метод и обученный предиктор могут иметь разные строки. Числа в точках показывают число каталожных записей, а не число независимых идей или экспериментов.')
 r.text('<b>Две стадии.</b> Применение включает получение всех признаков новой архитектуры; подготовка включает поиск формулы, калибровку и обучение оценщика. Forward готового LM-предиктора не является forward оцениваемой сети.')
 r.text('<b>Входы.</b> N - без реальных примеров; U - реальные X без targets; T - реальные X и objective, включая self-supervised targets. H - исторические качества архитектур. Синтетические targets относятся к N, если реальные X не используются.')
 r.text('<b>Стоимость.</b> Сопоставимых измерений полного времени нет. C_setup + N_candidates × C_query - схема учёта, не рассчитанная кривая. Число проходов и H не переводятся в секунды; FLOPs модели не равны цене вычисления proxy.','small')
 r.text('13 методов O4-O6 оставлены за границами темы. M28, M40 и M72 вынесены в конечный список не поддающихся анализу; это отдельная причина отсутствия. Статуса «не уточнено» в сравниваемых категориях нет.','small')
 r.text('<b>Обозначения в таблицах.</b> G - граф/размеры, W - значения весов, A - активации, D - производные; W0 - случайные веса, Wp - готовые веса. P01 и подобные коды обозначают публикации. P1-P7 без ведущего нуля обозначают подготовку:','small')
 r.text('; '.join(SCODE[k]+' - '+v.replace('\n',' ') for k,v in SETUPS.items())+'.','small')

def map_and_catalog(r,c):
 r.page();r.heading('D · '+c['title'])
 r.text('Каждая занятая пара категорий - одна точка; метод входит ровно в одну точку этой карты. Близость точек не означает близость численных качеств.','small')
 r.figure(c['id']+'_map',128)
 if c['prefix']=='S':
  r.text('G - граф, конфигурация или размеры; W - значения весов; A - активации; D - производные. Код содержит все источники, непосредственно входящие в score/вектор признаков. Промежуточные величины для вычисления производных не добавляются автоматически.','small')
 elif c['prefix']=='R':
  r.text('Для смешанного входа приоритет: реальные X + objective, затем реальные X без targets, затем только синтетика, затем отсутствие примеров. Синтетические компоненты смешанных методов раскрыты в таблицах и матрице. Производные могут быть по весам, входам или параметру входной кривой.','small')
 else:
  r.text('P1-P7 - способы подготовки. «По H» включает пары архитектура-качество; P6 использует кривые других конфигураций/anchors. P2 означает настройку по выборке архитектур без наблюдённых качеств.','small')
 r.page();r.heading('Расшифровка точек · полные названия методов')
 r.text('Таблицы следуют порядку точек карты. Сигнал, входы и подготовка относятся к каталожному варианту; численные панели ниже отдельно учитывают реализации экспериментов. Источники расшифрованы в разделе проверки.','small')
 for cell in cells(c):
  title=cell['id']+' · '+c['ylabels'][cell['y']].replace('\n',' ')+' × '+c['xlabels'][cell['x']].replace('\n',' ')
  start=len(r.story)
  r.story.append(CondPageBreak(48*mm));r.text(title,'h')
  rr=[]
  for mid in cell['method_ids']:
   m=MM[mid];a=ROWS[mid]
   detail=a['note']
   refs=', '.join(a['evidence']) if mid not in ['M33','M34'] else 'P50; WRCOR_CODE и цепочка вызовов'
   rr.append([mid,m['name'],a['signal_profile']+'; '+ACODE[m['data_access_at_use']],SCODE[a['setup']],detail,refs])
   r.catalog_ids.append(mid)
  r.table([cell['id']+' · ID','Полное название','Сигнал; входы','Подготовка','Определение / граница варианта','Источники'],rr,[20,66,24,24,103,30])
  # Keep the final two methods together on a continued catalog page.
  if len(rr)>2:r.story[-1].setStyle(TableStyle([('NOSPLIT',(0,-2),(-1,-1))]))
  r.story.append(Spacer(1,4*mm))
  if len(rr)<=3:r.story[start:]=[KeepTogether(r.story[start:])]
 r.text('Коды подготовки: '+ '; '.join(SCODE[k]+' - '+v.replace('\n',' ') for k,v in SETUPS.items())+'.','small')

def matrix_and_findings(r,c):
 r.page();r.heading('Состав признаков · проверка выбранных осей')
 r.text('Альтернативная матрица группирует методы по совпадающим признакам. Коды F относятся только к этой матрице; они не совпадают с кодами точек основной карты.','small')
 r.figure(c['id']+'_matrix',121)
 r.text(c['matrix_reason'],'small')
 r.text('Для GRAF/ZCP учитывается полный набор признаков; для LPZero/EZNAS - проверенная FlexiBERT-реализация. Отсутствие отметки означает отсутствие требования в указанном определении, а не доказательство нулевой стоимости.','small')
 r.page();r.heading('Что даёт новая детализация')
 r.text(c['conclusion'])
 metrics=design_metrics(c)
 r.table(['Карта','Матрица','Редакционное решение'],[[f'{metrics["map_points"]} точек; {metrics["singletons"]} одиночных групп; крупнейшая - {metrics["largest_group"]}',f'{metrics["matrix_profiles"]} профилей по {metrics["matrix_features"]} признакам','Основная 2D-карта + дополнительная матрица; составные признаки не теряются']],[84,65,118])
 if c['prefix']=='S':
  r.text('Изолировать «комбинированные методы» в одну непрозрачную категорию не стоит: G+A, W+D и G+W+A+D требуют разных исходных величин. Поэтому комбинации записаны явно. Различать внутри каждой из них отдельные нормы и функции агрегации на общей оси уже избыточно.')
  examples=[['M08 · Fisher','A+D','Активация умножается на производную; промежуточный forward и прямой вклад A различаются.'],['M25 · LPZero','A','Для выбранной FlexiBERT-реализации head - выход forward hook.'],['M31 · ParZC','O3; W+A+D','MABN учится по качествам; optional PINAT fusion не включён.'],['M37 · ZCP + RF','G+W+A+D','Даже без GRAF в полном ZCP есть размеры/сложность.']]
 elif c['prefix']=='R':
  r.text('N полезно разделить по фактическим действиям. Напротив, выделять каждый тип входной синтетики в отдельную ось не нужно: единицы, Gaussian input и синтетические targets лучше описать в строке метода.')
  examples=[['M26/M27 · ZeroLM','Веса; N','При применении не требуется входной batch; различается подготовка alpha.'],['M14 · Zen-Score','Forward; N','Синтетические входы, без реальных данных.'],['M32 · Dextr','Производные; U','Реальный пример для SVD и синтетическая кривая для дифференцирования.'],['M54 · LC-Net','Граф/конфигурация; N','Не нужна кривая нового кандидата; кривые других конфигураций нужны заранее.']]
 else:
  r.text('Редкие группы P4 и P7 сохранены: калибровка коэффициента и prompt меняют способ использования H, хотя каждая сейчас содержит один метод. Это содержательные границы, а не дробление по названию алгоритма.')
  examples=[['M15/M25','P3 · поиск формулы','H используется при открытии формулы; затем применяется найденное выражение.'],['M26 против M27','P4 против P2','Наблюдённые качества против согласования компонент без quality labels.'],['M47','P7 · prompt','Исторические пары входят в контекст готового LM.'],['M52/M54','P6 · кривые','Исторические кривые/anchors готовятся заранее, новая сеть не дообучается для score.']]
 r.table(['Пример','Различие','Почему оно важно'],examples,[65,64,138])
 r.text('Разбиение не является рейтингом качества. Одиночная группа сохраняется, если отличается обязательное действие или источник знаний. Более тонкая детализация оправдана только при появлении нового вопроса, а не ради увеличения числа категорий.','small')
 r.page();r.heading('Подготовка и применение · независимые признаки')
 counts=Counter(a['setup'] for a in ROWS.values())
 r.table(['Код','Способ подготовки','Число методов'],[[SCODE[k],v.replace('\n',' '),counts[k]] for k,v in SETUPS.items()],[25,197,45])
 r.text('P1 не означает отсутствие авторского эмпирического выбора формулы; означает, что описанное применение не требует её повторного fit по H. P2 включает настройку alpha/size prior, нормализацию популяции или consensus gate без исторических качеств.','small')
 r.table(['Метод','Дополнительная стадия представления','Источники'],[[mid+' · '+MM[mid]['name'],REP[a['representation']],', '.join(a['evidence'])] for mid,a in ROWS.items() if a['representation']!='none'],[109,118,40])
 r.text('Предобучение CATE/arch2vec не устраняет H для выбранного prediction head. Готовый LM относится к оценщику, а не к весам оцениваемой архитектуры. Для ONNX-Net отмечен обученный LM; обязательность внешнего предобученного checkpoint не утверждается.','small')
 r.text('<b>Исправление базовой классификации.</b> M33 WRCor и M34 WRCor voting переведены U → T: в авторском NB101/NB201 коде используются cross-entropy и targets из dataloader. Обоснование: WRCOR_CODE → WRCOR_LOADER → WRCOR_RUNNER. Численных записей этих методов в основном сравнении нет.','small')

def numeric(r,c):
 r.page();r.heading('B / F · Корреляции в независимых NLP-протоколах')
 labels={'S':'Буквы после ρ показывают состав сигнала G/W/A/D. Строки сгруппированы по профилю.',
         'R':'Буквы после ρ показывают входы конкретной реализации: N/U/T. Строки сгруппированы по операциям.',
         'P':'Коды после ρ показывают подготовку P1-P7. Строки сгруппированы по способу подготовки.'}
 r.text(labels[c['prefix']],'small');r.figure(c['id']+'_BF',118)
 r.text('25 наблюдений. Пустая позиция - отсутствие допущенного измерения. Протоколы не образуют общего рейтинга. В G1 M04-M08, M12, M20/M21 используют реальные тексты и backward от hidden states: U. Исходные CV-категории N/T сюда не переносятся; ссылки LPZ_* приведены в проверке.','small');r.source(['G1','G2','G4'])
 r.page();r.heading('E · Бюджет исторических качеств')
 r.text('G5 · NAS-Bench-101 / CIFAR-10; RF одного типа, четыре набора признаков и три бюджета.','small');r.figure(c['id']+'_E',113)
 emphasis={'S':'GRAF/one-hot используют только G; ZCP и GRAF+ZCP требуют G+W+A+D. Более богатый сигнал здесь сравнивается при одинаковом типе предиктора.',
           'R':'GRAF/one-hot не требуют реальных примеров при применении. Полный ZCP требует T при получении признаков нового кандидата, даже если benchmark предоставляет кэш.',
           'P':'Все четыре метода относятся к P5. H меняет бюджет обучения оценщика; дополнительного предобучения представления в этих строках нет.'}
 r.text(emphasis[c['prefix']],'small')
 r.text('12 наблюдений; Kendall τ: среднее ± SD по 50 запускам. SD не является доверительным интервалом. H - число архитектур с известным качеством, не число примеров и не секунды. Разность средних не доказывает статистическую значимость.','small');r.source(['G5'])
 r.page();r.heading('G6 · Признаки и языковые модели как предикторы')
 r.text('Отдельный CV-протокол CIFAR-10. Языковая модель предсказывает качество архитектур; это не делает оцениваемые архитектуры NLP-моделями.','small');r.figure(c['id']+'_G6',111)
 emphasis={'S':'M38/M39 используют G+W+A+D; варианты M46 получают строковую архитектурную кодировку G. Внутренние активации самого LM не добавляют A к сигналу кандидата.',
           'R':'M38/M39 требуют полного ZCP-вектора с T; M46 требует архитектурную строку N. Стоимость готового LM-предиктора не равна нулю и не измерена сопоставимо.',
           'P':'Все строки используют обучение по H (P5). M46 дополнительно начинает с готового LM; четыре backbone/augmentation варианта сохранены отдельно.'}
 r.text(emphasis[c['prefix']],'small')
 r.text('6 наблюдений; около 9k пар, 6 train / 1 validation / 1 test NAS runs. Spearman ρ и Kendall τ не усредняются и не соединяются линией. Для этих строк не извлечён разброс; небольшие различия не объявляются значимыми.','small');r.source(['G6'])

def sources(r):
 r.page();r.heading('Проверка классификаций · источники и границы')
 r.text('Новые признаки представлены отдельным аудитом. Ссылки ниже подтверждают определения; классификация по этим определениям - редакционная интерпретация. Численные значения исходного корпуса не заменены результатами других версий статей.','small')
 for key,s in AUDIT['sources'].items():
  ids=[mid for mid,a in ROWS.items() if key in a['evidence']]
  label=('Первоисточник / авторский код' if s['review_type']!='inherited_handoff_definition' else 'Определение из handoff; ссылка на первоисточник')
  text='<b>'+escape(key+' · '+', '.join(ids))+'</b><br/>'+escape(s['locator'])+' · '+link(s['url'],label)
  r.story.append(KeepTogether([r.p(text,'small'),Spacer(1,1.5*mm)]))
 r.text('Предшествующий audit сохранён в data/narrow_method_audit.json → source_access_audit как история. Поле data_access_at_use нового аудита имеет приоритет: M33/M34 исправлены U → T. Для G1 M05-M08 и M12 отдельные observation_access_overrides исправляют метки применения на U; численные значения не изменены. Хеши локальных источников и кода включены в аудит.','small')
 r.page();r.heading('Библиография узкого обзора')
 groups={g['block']:g for g in load('groups')}
 used={m['origin_paper_id'] for m in METHODS}|{s['paper_id'] for s in AUDIT['sources'].values()}|{groups[o['block']]['paper_id'] for o in OBS}
 for pid in sorted(used):
  p=PAPERS[pid];r.story.append(KeepTogether([r.p(escape(pid+' · '+p['title'])+'<br/>'+link(p['canonical_url'],'Публикация'),'small'),Spacer(1,2*mm)]))

def archive(r):
 r.page();r.heading('Архив · неподтверждённые наблюдения и времена')
 r.text('Эти записи не включены в основные графики; при исключении только timing корреляция сохранена. Метод может иметь проверенный каталожный вариант и неподтверждённую численную адаптацию.','small')
 rr=[]
 for o in load('observations'):
  if o['method_id'] not in MM and not o['method_candidates']:continue
  why=exclusion_reason(o)
  if why or o['costs']:
   val='; '.join(m['name']+'='+str(m['value']) for m in o['metrics'])
   if o['costs']:val+='; reported time='+str(o['costs'][0]['value'])+' s'
   rr.append([o['id'],o['method_id'] or 'M26/M27',val,why or 'Исключён только timing: полный scope и аппаратура не установлены.'])
 r.table(['Наблюдение','Метод','Исходное значение','Причина'],rr,[26,23,81,137])
 r.page();r.heading('Методы, не поддающиеся анализу в текущем корпусе')
 r.text('Все 56 методов выбранного состава получили категории. Дополнительных исключений после уточнения осей нет. Ниже сохранены три ранее исключённые записи, относящиеся к близкой тематике; в состав 56 они не входят.')
 for a in load('access_audit'):
  if a['status']=='excluded':
   m=next(m for m in load('methods') if m['id']==a['method_id'])
   r.heading(m['id']+' · '+m['name']);r.text(escape(a['reason']));r.text(link(a['url'],'Источник / попытка проверки')+' · '+escape(a['locator']),'small')
 r.text('O4-O6 (13 методов) исключены только по границам темы и не относятся к этому списку.','small')

def manifest(r,c):
 payload=dict(config=c,pdf=str(r.path.relative_to(ROOT)),pages=len(PdfReader(r.path).pages),method_ids=r.catalog_ids,
              observation_ids=[o['id'] for o in OBS],observation_access={o['id']:access(o,MM) for o in OBS},figures=r.figures,design_metrics=design_metrics(c),
              excluded_method_ids=['M28','M40','M72'],pdf_sha256=hashlib.sha256(r.path.read_bytes()).hexdigest(),
              inputs_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*.json')})
 (EX/(c['id']+'_manifest.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(r.path.name,payload['pages'],'pages',flush=True)

def comparison():
 r=NarrowReport(OUT/'00_classification_comparison.pdf','Сравнение узких классификаций','O1-O3 · выбор осей')
 r.text('Три ракурса одного набора','title');r.heading('Какой обзор выбрать')
 r.text(f'Общий состав: {len(METHODS)} методов, {len(OBS)} наблюдения. Рекомендуемый основной документ - 01_signal_mechanisms.pdf; два других отвечают на вопросы о применении и подготовке.')
 rows=[]
 for c in CONFIGS:
  d=design_metrics(c);rows.append([c['title'],c['question'],f'{d["map_points"]} точек / {d["singletons"]} одиночных',f'{d["matrix_profiles"]} профилей × {d["matrix_features"]} признаков'])
 r.table(['Обзор','Вопрос','2D-карта','Матрица'],rows,[65,105,49,48])
 r.text('По сравнению с исходными O1-O3, источники сигнала раскрывают внутреннюю неоднородность O2 и O3. Практическая карта уточняет N; карта подготовки отделяет поиск формулы, калибровку, обучение и prompt. Во всех вариантах подробные таблицы остаются в основном тексте сразу после карты.')
 r.text('Критерий остановки: новое подразделение должно менять обязательное действие, используемый сигнал или источник знаний. Название нормы, тип регрессора или частная архитектура сами по себе не создают новую ось. Число методов в подгруппе - диагностический признак, а не запрет на содержательную одиночную категорию.')
 r.text('3D не выбран: для этих вопросов две категориальные оси и отдельная матрица сохраняют информацию без перспективного перекрытия. Время не используется как третья ось из-за отсутствия совместимых измерений.','small')
 for c in CONFIGS:
  r.page();r.heading(c['title']+' · 2D-карта');r.figure(c['id']+'_map',129)
  d=design_metrics(c);r.text(f'Заполнено {d["map_points"]} из {d["map_cells"]} ячеек. Крупнейшая группа: {d["largest_group"]}; одиночных: {d["singletons"]}. '+c['conclusion'],'small')
  r.page();r.heading(c['title']+' · матрица');r.figure(c['id']+'_matrix',126);r.text(c['matrix_reason'],'small')
 r.page();r.heading('Почему эти подразделения сохранены')
 r.table(['Подразделение','Решение','Основание'],[
  ['N → без примеров / синтетика','Сохранить','Меняется необходимость исполнения сети; N не означает отсутствие forward/backward.'],
  ['Сигнал → G / W / A / D и сочетания','Сохранить','Полный состав предотвращает произвольный выбор главного компонента.'],
  ['Поиск формулы / калибровка / predictor fit / prompt','Сохранить','Разные способы использования исторического качества и разные переносимые артефакты.'],
  ['CATE/arch2vec/готовые LM','Матрица и таблица стадий','Предобучение пересекается с обучением quality head; одна ось скрыла бы это.'],
  ['Нормы, функции агрегации, RF против XGB','В расшифровках и численных панелях','Не добавляют нового источника сигнала или режима доступа.'],
  ['Тип производной и синтетического входа','В строках методов','Для данной обзорной задачи это уточнение реализации; Dextr отдельно пояснён.'],
  ['Общий рейтинг корреляций','Не строить','Протоколы G1/G2/G4/G5/G6 независимы.'],
 ],[90,52,125])
 r.text('Проверяемость: 56 записей нового аудита, исходные ID и значения сохранены; 6 проб основных классификаций экспортированы в PNG/SVG/PDF и JSON. Каждая карта - точное разбиение состава, каждая матрица - точное разбиение по наборам признаков.','small')
 r.build();print(r.path.name,len(PdfReader(r.path).pages),'pages',flush=True)

def main():
 OUT.mkdir(parents=True,exist_ok=True);EX.mkdir(parents=True,exist_ok=True)
 decisions=[dict(id=c['id'],metrics=design_metrics(c),selected='2D map with exact combination groups',complement='binary feature matrix',reason=c['matrix_reason']) for c in CONFIGS]
 (ROOT/'data/narrow_design_review.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2)+'\n')
 for c,ef,gf in zip(CONFIGS,[e_budget_panels,e_matrix,e_lines],[g6_dots,g6_table,g6_dots]):
  for suffix,fn in [('map',lambda:grouped_map(c)),('matrix',lambda:feature_matrix(c)),('BF',lambda:numeric_bf(c)),('E',ef),('G6',gf)]:
   savefig(c['id']+'_'+suffix,fn())
  r=NarrowReport(OUT/(c['id']+'.pdf'),c['title'],'O1-O3 · '+c['prefix'])
  cover(r,c);map_and_catalog(r,c);matrix_and_findings(r,c);numeric(r,c);sources(r);numerical_tables(r,OBS,MM,access);archive(r);r.build();manifest(r,c)
 comparison()

if __name__=='__main__':main()
