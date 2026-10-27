"""Working atlas of directly comparable results. Final source audit still pending."""
import sys,json,textwrap
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from reportlab.platypus import SimpleDocTemplate,Paragraph,Image,PageBreak,Table,TableStyle,Spacer
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape
from corpus import ROOT
from narrow_review import MM
D=ROOT/'data/comparability';E=ROOT/'exports/comparability';E.mkdir(exist_ok=True)
P=json.loads((D/'protocols.json').read_text());R=json.loads((D/'records.json').read_text());PP={p['id']:p for p in P}
C={'static':('#487b9e','Граф / размеры'), 'weights':('#8e69a4','Только веса'), 'forward':('#53996e','Прямой проход'), 'derivatives':('#c58b38','Производные'), 'learned_static':('#a74e69','Обученный оценщик: граф / текст'), 'learned_dynamic':('#685caa','Обученный оценщик: proxy / кривые')}
SHORT={'M01':'Число параметров','M03':'FLOPs','M11':'NASWOT / Activation Distance','M18':'AZ-NAS','M25':'LPZero','M36':'GRAF + RF','M37':'ZCP + RF','M38':'GRAF + ZCP + RF','M39':'GRAF + ZCP + XGB','M46':'LM','M47':'LM / 3-shot','M51':'CoRA-Rank','M52':'CoRA-Refine','M30':'SWAP-reg','M32':'Dextr','M34':'WRCor voting','M69':'One-hot + RF'}

def label(r):
 name=SHORT.get(r['method_id'],r['name'])
 if r['method_id'] in ['M46','M47','M34']:name=r['variant']
 return r['method_id']+' '+name

def chart(name,ids,metric='spearman_rho'):
 fig,axes=plt.subplots(1,len(ids),figsize=(20,10),squeeze=False)
 for ax,pid in zip(axes[0],ids):
  rr=sorted([r for r in R if r['protocol']==pid and metric in r['metrics']],key=lambda r:r['metrics'][metric])
  for y,r in enumerate(rr):
   v=r['metrics'][metric];color=C[r['category']][0]
   ax.scatter(v,y,s=85,color=color,zorder=3)
   if r.get('sd',{}).get(metric):ax.errorbar(v,y,xerr=r['sd'][metric],color=color,capsize=3,lw=1.1)
   ax.annotate(f'{v:.3f}',(v,y),xytext=(7,0),textcoords='offset points',fontsize=10,va='center')
  ax.set_yticks(range(len(rr)),[label(r) for r in rr],fontsize=10)
  for tick,r in zip(ax.get_yticklabels(),rr):tick.set_color(C[r['category']][0])
  ax.set_title(PP[pid]['title'],fontsize=13,pad=14);ax.set_xlim(-.25,1.12)
  ax.axvline(0,color='#bbb',lw=.8);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Spearman ρ' if metric=='spearman_rho' else 'Kendall τ',fontsize=12)
  ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
 fig.legend(handles=[Line2D([],[],marker='o',color='none',markerfacecolor=c,label=l,markersize=8) for c,l in C.values()],loc='lower center',ncol=3,fontsize=11,frameon=False)
 fig.tight_layout(rect=[0,.09,1,.98]);fig.savefig(E/(name+'.png'),dpi=160);fig.savefig(E/(name+'.pdf'));plt.close(fig)
 return name

for font,f in [('CV','DejaVuSans.ttf'),('CV-B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(font,'/usr/share/fonts/truetype/dejavu/'+f))
pdfmetrics.registerFontFamily('CV',normal='CV',bold='CV-B',italic='CV',boldItalic='CV-B')
S={k:ParagraphStyle(k,fontName='CV-B' if k=='title' else 'CV',fontSize=s,leading=l,spaceAfter=10) for k,s,l in [('title',25,30),('body',12,17),('small',10,14),('cell',10,14)]}
def p(t,s='body'):return Paragraph(t,S[s])
def table(rows,widths):
 t=Table([[p(c,'cell') for c in row] for row in rows],colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ee')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f2f5f7'),colors.white]),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
 return t
story=[]
def page(title,body,name=None,ids=[]):
 if story:story.append(PageBreak())
 story.extend([p(title,'title'),p(body)])
 if name:story.append(Image(str(E/(name+'.png')),width=385*mm,height=192.5*mm))
 if ids:
  pp=list({PP[i]['paper_id']:PP[i] for i in ids}.values())
  story.append(p('Источники: '+'; '.join('<link color="#286080" href="'+q['url']+'">'+q['paper_id']+' · '+escape(q['locator'])+'</link>' for q in pp)+'.','small'))

page('Какие методы перспективны: проверяемая основа отбора',
 'Рабочая версия от 26.10.2026. Сопоставляются корреляции предсказаний с качеством архитектур внутри общего эксперимента. Разные задачи и наборы архитектур не объединены в один рейтинг. Проверка источников ещё продолжается: текущие результаты не являются окончательным отбором по всем 56 методам.')
story.append(table([
 ['Условия применения','Кандидаты для дальнейшего отбора','Основание и ограничение'],
 ['BERT-подобные модели; доступны тексты','LPZero; SWAP-Score; Attention Confidence','LPZero лидирует в G1; SWAP - в G4. Это разные протоколы. В G2 лидирует NASWOT среди пока допущенных строк; ZeroLM нельзя присвоить конкретному варианту alpha.'],
 ['CNN; без обучения оценщика по историческим качествам','CoRA-Rank; AZ-NAS','Прямой live-протокол NAS-Bench-201. CoRA-Rank лидирует по ρ и τ; преимущество не универсально для ViT. Требуются вычисления на новой сети.'],
 ['CNN; доступны короткие кривые anchors','CoRA-Refine','Повышает корреляции в том же протоколе. Дополнительные 1000 anchors × 30 эпох не скрыты под обозначением zero-cost.'],
 ['Есть H пар архитектура-качество','GRAF + RF; GRAF + ZCP + RF','Первый использует только граф новой сети. Второй даёт более высокие средние в рассмотренных задачах, но требует proxy-признаков. SD не доказывает значимость разницы.'],
 ['einspace; можно обучать LM-оценщик','ModernBERT-large + augmentation','Лучшие ρ и τ в рассмотренной таблице; прямое сопоставление с RF, XGB и 3-shot LM. Не означает преимущество на NLP-архитектурах.']
 ],[85,95,205]))
story.extend([Spacer(1,15),p('Что обозначает цвет','title'),p('Цвет кодирует способ получения оценки, а не качество метода. Потребность в исторических качествах отделена от вычислений на новой архитектуре. Синтетические и реальные входы уточняются при окончательном аудите вариантов.'),table([['Род метода','Что требуется']]+[[f'<font color="{c}">● {l}</font>',desc] for (c,l),desc in zip(C.values(),['Описание графа, размеры или счётчики операций.','Значения весов; входной batch не нужен.','Forward оцениваемой сети; реальные или синтетические входы зависят от варианта.','Вычисление производных оцениваемой сети; требования к данным зависят от варианта.','Предварительная подготовка по H; для новой архитектуры - её описание. Готовый LM может быть частью оценщика.','Подготовка по H/кривым и вычисление proxy для нового кандидата.'])],[110,275])])
ids=['old_G1','old_G2','old_G4'];name=chart('nlp_protocols',ids)
page('NLP: три независимых эксперимента', 'Столбцы имеют собственные списки методов. Нельзя заключить, что SWAP лучше LPZero, сравнив их числа из разных столбцов. G2 пока содержит только ранее проверенные строки; полная таблица статьи проходит дополнительный аудит.',name,ids)
ids=['cora_nb201_0','cora_nb201_1','cora_nb201_2'];name=chart('cora_nb201',ids)
page('CNN: единый протокол на 15 625 архитектурах', 'CoRA-Rank и CoRA-Refine лидируют в этой группе. Refine использует дополнительный бюджет anchors. Fisher и Plain исключены из live-панели: в статье эти строки заимствованы. Результат является свидетельством одной работы, а не независимой репликацией.',name,ids)
ids=['wrcor_nb201_full'];name=chart('wrcor_full',ids)
page('WRCor: полный бенчмарк меняет впечатление от voting', 'Здесь колонка real, то есть полный NAS-Bench-201 / CIFAR-10. SJW: ρ = 0.799, тогда как на подвыборке 1000 архитектур сообщалось 0.851. WRCor: 0.812. Нельзя переносить победу на подвыборке на полный набор или сравнивать эти числа с панелью CoRA без учёта протокола.',name,ids)
ids=[q['id'] for q in P if q['id'].startswith('cora_vit_')]
# Compact facets as numerical matrix with categorical colour of rows.
fig,ax=plt.subplots(figsize=(20,10));mids=['M51','M18','M01','M09']
for y,mid in enumerate(mids):
 for x,pid in enumerate(ids):
  r=next(r for r in R if r['protocol']==pid and r['method_id']==mid);v=r['metrics']['spearman_rho']
  ax.scatter(x,y,s=1900,color=C[r['category']][0],alpha=.8);ax.text(x,y,f'{v:.3f}',ha='center',va='center',color='white',fontsize=13,weight='bold')
ax.set_yticks(range(4),[m+' '+SHORT.get(m,MM[m]['name']) for m in mids],fontsize=13)
ax.set_xticks(range(len(ids)),[PP[i]['title'].split(' / ',1)[1].replace(' (','\n(') for i in ids],fontsize=12)
ax.set(xlim=(-.7,len(ids)-.3),ylim=(3.7,-.7));ax.spines[:].set_visible(False);ax.tick_params(length=0,pad=15)
fig.tight_layout();fig.savefig(E/'vit_boundary.png',dpi=160);fig.savefig(E/'vit_boundary.pdf');plt.close(fig)
page('Граница переноса: ViT не повторяет CNN-рейтинг','Число в круге - Spearman ρ; цвет - род метода. Круги имеют одинаковый размер. На семи targets одного ViT-протокола победитель меняется. Это основание не объявлять CoRA универсальным лидером. Все четыре метода измерены на одних 200 AutoFormer-Tiny subnets.','vit_boundary',ids)
ids=['graf_NAS-Bench-101_CIFAR-10_'+str(h) for h in [32,128,1024]];name=chart('graf_budget',ids,'kendall_tau')
page('Исторические качества: выигрыши и цена признаков','Каждая панель фиксирует бюджет H. GRAF + ZCP + RF имеет наибольшее среднее, но GRAF + RF обходится без запуска новой сети. Отрезки - SD по 50 повторам; это не доверительные интервалы и не тест значимости.',name,ids)
ids=['old_G6'];name=chart('einspace_surrogates',ids)
page('Обученные оценщики: сравнение на одном test set','CIFAR-10 / einspace, 6 train / 1 validation / 1 test NAS runs. Объединены Table 1 и Table 7: авторы явно указывают общий evaluation set. Добавлены 3-shot LM и исходные ZCP; сильный готовый LM без дообучения здесь не заменяет обученный оценщик.',name,ids)
page('Как читать доказательства и что ещё проверяется','В текущем реестре 27 отдельных контекстов и 181 запись метод × контекст, охвачены 38 из 56 ID. Методы без готовой группы сравнения не объявляются слабыми. Полный отбор будет завершён после проверки оставшихся источников и вариантов.')
coverage=json.loads((D/'coverage.json').read_text())
story.append(table([['ID и полное название','Состояние проверки']]+[[escape(c['method_id']+' · '+c['name']),'Первоисточники: '+', '.join(c['source_ids'])+'. Не включён в текущие выводы; проверка сопоставимого эксперимента продолжается.'] for c in coverage if c['status']=='source_review_pending'],[165,220]))
story.append(p('Критерии конечного отбора: общая экспериментальная основа; точный вариант метода; связь с реальным качеством; согласованность по задачам; требования при применении и подготовке; отсутствие вывода о значимости без подходящего теста. Расхождение Spearman и Kendall само по себе не делает методы несравнимыми.','small'))
def footer(c,d):
 c.setFont('CV',9);c.setFillColor(colors.HexColor('#617381'));c.drawString(15*mm,10*mm,'РАБОЧАЯ ВЕРСИЯ · аудит сравнимости O1-O3 · 26.10.2026');c.drawRightString(405*mm,10*mm,str(d.page))
out=ROOT/'output/pdf/narrow/05_promising_methods_working.pdf'
SimpleDocTemplate(str(out),pagesize=landscape(A3),leftMargin=15*mm,rightMargin=15*mm,topMargin=13*mm,bottomMargin=18*mm,title='Перспективные методы: рабочий атлас доказательств').build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
