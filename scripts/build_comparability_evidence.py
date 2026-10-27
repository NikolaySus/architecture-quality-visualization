"""Source-local comparison cohorts; never infer comparability from shared baselines."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from narrow_review import MM,ROWS,OBS,access
from corpus import ROOT,load
D=ROOT/'data/comparability';D.mkdir(exist_ok=True)
protocols=[];records=[];decisions=[]

def snapshot(paper,folder='source_audit'):
 p=ROOT/f'tmp/comparability/{paper}_{folder}_tables.json'
 x=json.loads(p.read_text());return x

def table(paper,tid,folder='source_audit'):
 x=snapshot(paper,folder);t=next(t for t in x['tables'] if t['id']==tid)
 # Persist extracted source cells, not just generated scores.
 p=D/f'{paper}_{tid}.json';p.write_text(json.dumps({'source':x['source'],'source_sha256':x['sha256'],**t},ensure_ascii=False,indent=2)+'\n')
 return t['rows']

def protocol(pid,title,paper,url,locator,target,sample,notes,tier='direct'):
 p=dict(id=pid,title=title,paper_id=paper,url=url,locator=locator,target=target,sample=sample,notes=notes,tier=tier)
 protocols.append(p);return pid

def add(pid,mid,variant,values,source_row,category=None,**kw):
 assert mid in MM
 records.append(dict(protocol=pid,method_id=mid,variant=variant,name=MM[mid]['name'],metrics=values,source_row=source_row,category=category or kind(mid),**kw))

def kind(mid):
 r=ROWS[mid]
 if r['setup'] in ['fit','curves','prompt']:
  return 'learned_static' if r['operation'] in ['graph','weights'] else 'learned_dynamic'
 return {'graph':'static','weights':'weights','forward':'forward','derivatives':'derivatives'}[r['operation']]

# Existing independently audited source observations, kept separate from new extraction.
GG={g['block']:g for g in load('groups')}
for block in ['G1','G2','G4','G6']:
 g=GG[block]
 pid=protocol('old_'+block,g['search_space']+' / '+g['target_eval_dataset'],g['paper_id'],g['url'],g['locator'],g['target_eval_dataset'],500 if block in ['G1','G2','G4'] else '6 train / 1 val / 1 test NAS runs',g['notes'],'direct')
 for o in OBS:
  if o['block']!=block:continue
  add(pid,o['method_id'],o['variant_label'],{m['name']:m['value'] for m in o['metrics']},o['id'],access_at_use=access(o,MM),origin='existing_audited_observation')

# Explicit targets and proxy inputs; the two are different experimental axes.
for q in protocols:
 if q['id'] in ['old_G1','old_G2','old_G4']:
  q['proxy_input']=GG[q['id'][4:]]['proxy_input_dataset']
  q['target']='weighted downstream GLUE score' if q['id']=='old_G4' else 'mean downstream GLUE score'
  q['title'] += ' / inputs: '+q['proxy_input']
 if q['id']=='old_G6':
  q['url']='https://proceedings.mlr.press/v293/qin25a.html'
  q['target']='CIFAR-10 ground-truth accuracy; held-out NAS run'

# CoRA Table 2: live shared protocol; sourced Fisher/Plain kept out of strict cohort.
MAP={'#Params':'M01','FLOPs':'M03','GradNorm':'M07','Grasp':'M06','Snip':'M05','Synflow':'M04','NASWOT':'M11','TE-NAS':'M13','ZenNAS':'M14','ZiCo':'M17','AZ-NAS':'M18','Fisher':'M08','Plain':'M71','SWAP':'M30','Dextr':'M32','CoRA-Rank (Stage 1)':'M51','CoRA-Refine (Stage 2)':'M52'}
rows=table('P38','S4.T2')
for i,dataset in enumerate(['CIFAR-10','CIFAR-100','ImageNet16-120']):
 pid=protocol('cora_nb201_'+str(i),'NAS-Bench-201 / '+dataset,'P38','https://arxiv.org/html/2609.11884v1#S4.T2','Table 2; §4; Appendix A',dataset+' test accuracy @200 epochs',15625,'Общий live-протокол L40S. Fisher/Plain взяты из внешнего источника и здесь исключены. Refine использует 1000 anchors × 30 эпох; это дополнительный бюджет. Dextr обозначен в статье F, но проверенный код использует производные. SWAP здесь означает SWAP-reg (M30).')
 for row in rows[2:]:
  if row[0] not in MAP or row[0] in ['Fisher','Plain']:continue
  add(pid,MAP[row[0]],row[0],{'kendall_tau':float(row[3+3*i]),'spearman_rho':float(row[4+3*i])},row,runtime_ms=float(row[2]) if row[2].replace('.','',1).isdigit() else None,origin='primary_table_live')
decisions += [dict(paper='P38',table='Table 2',rows=['Fisher','Plain'],decision='exclude_from_live_cohort',reason='Precomputed NAS-Bench-Suite-Zero source; no identical live rerun.'),dict(paper='P38',table='Tables 3/14',decision='do_not_pool',reason='Mixed sources, different sample sizes (3000/4096), and absolute rho; individual live cohorts require separate review.')]
# A negative transfer check prevents a CNN winner becoming a universal recommendation.
rows=table('P38','S4.T10')
for row in rows[2:9]:
 pid=protocol('cora_vit_'+str(len(protocols)),'ViT-Bench-101 / '+row[0],'P38','https://arxiv.org/html/2609.11884v1#S4.T10','Table 10; §4.3',row[0]+' true accuracy',200,'AutoFormer-Tiny subnets; отдельный target. Только O1-O3 исходного корпуса. L-SWAG и LIBRA вне заданного состава.')
 for col,mid in [(1,'M51'),(3,'M18'),(4,'M01'),(5,'M09')]:add(pid,mid,'ViT-Bench-101',{'spearman_rho':float(row[col])},row,origin='primary_table')

# WRCor: full benchmark column, not favourable 1000-subset estimate.
rows=table('P50','S4.T2')
pid=protocol('wrcor_nb201_full','NAS-Bench-201 / CIFAR-10','P50','https://arxiv.org/html/2507.08841v2#S4.T2','Table 2, real column; §4.1.3','CIFAR-10 test accuracy',15625,'Полная колонка real. Не смешивать с est. по 1000 архитектурам: SJW меняется с 0.851 до 0.799. Сопоставление внутри таблицы авторов; Params/FLOPs/ZiCo представлены только для full space. Требования WRCor уточнены по авторскому коду.','author_comparison')
wm={'PNorm':'M70','PGNorm':'M07','SNIP':'M05','GraSP':'M06','SynFlow':'M04','Fisher':'M08','JacCor':'M09','Zen':'M14','NASWOT':'M11','ZiCo':'M17','Params':'M01','FLOPs':'M03','WRCor (Ours)':'M33','SPW (Ours)':'M34','SJW (Ours)':'M34'}
for row in rows[1:]:
 if row[0] in wm:add(pid,wm[row[0]],row[0],{'spearman_rho':float(row[2])},row,origin='primary_table')

# RF feature comparison across tasks and budgets: independently ranked per cell.
import re
for tid,space,datasets in [('A6.T6','NAS-Bench-101',['CIFAR-10']),('A6.T7','NAS-Bench-201',['CIFAR-10','CIFAR-100','ImageNet16-120'])]:
 rows=table('P12',tid)
 for di,dataset in enumerate(datasets):
  for hi,H in enumerate([32,128,1024]):
   pid=protocol('graf_'+space+'_'+dataset+'_'+str(H),space+' / '+dataset+' / H='+str(H),'P12','https://arxiv.org/html/2404.16551v2#'+tid,'Appendix F, '+tid,dataset+' validation accuracy',f'H={H}; 50 independent runs','Один RF; одинаковый бюджет H. Среднее Kendall τ и SD, не CI. Только четыре исходных варианта без дополнительных OH/PE/FP. Числа других H не образуют единый рейтинг.')
   for row in rows[2:]:
    if row[0] not in ['OH','GRAF','ZCP','ZCP + GRAF']:continue
    value,sd=map(float,re.findall(r'\d+\.\d+',row[1+di*3+hi]))
    mid={'OH':'M69','GRAF':'M36','ZCP':'M37','ZCP + GRAF':'M38'}[row[0]]
    add(pid,mid,row[0],{'kendall_tau':value},row,sd={'kendall_tau':sd},H=H,origin='primary_table')

# Additional Qin Table 1 variants and Table 7 evaluated on the same test architectures.
pid='old_G6'
for label,mid,rho,tau,se in [('RoBERTa-large','M46',.679,.523,None),('Llama3.2 1B','M46',.722,.588,None),('Llama3.2 1B Instruct','M46',.726,.593,None),('Llama3.2 3B','M46',.682,.552,None),('Llama3.2 3B Instruct / 3-shot','M47',-.087,-.067,[.030,.023]),('Qwen2.5 7B Instruct / 3-shot','M47',.319,.235,[.014,.012]),('Qwen2.5 14B Instruct / 3-shot','M47',.356,.256,[.018,.014])]:
 add(pid,mid,label,{'spearman_rho':rho,'kendall_tau':tau},'P14 Table 1 / PDF p.7',se=se,origin='primary_pdf')
for mid,label,rho,tau in [('M07','grad_norm',.040,.036),('M05','snip',.094,.078),('M06','grasp',-.072,-.053),('M08','fisher',-.037,-.020),('M09','jacob_cov',.381,.243),('M71','plain',-.189,-.126),('M04','synflow',.465,.362)]:
 add(pid,mid,label,{'spearman_rho':rho,'kendall_tau':tau},'P14 Table 7 / PDF p.18',origin='primary_pdf')
next(p for p in protocols if p['id']==pid)['locator']='Table 1 + Appendix Table 7 (same CIFAR-10 evaluation set)'

# Extend the actual within-paper NLP comparisons; no pooling of copied columns.
rows=table('P29','S3.T1')
mp={'#params':'M01','Synflow [ 17 ]':'M04','Fisher [ 15 ]':'M08','Gradnorm [ 7 ]':'M07','SNIP [ 16 ]':'M05','Jacobian cosine [ 40 ]':'M10','GraSP [ 41 ]':'M06','Synaptic Saliency [ 17 ]':'M21','LPZero [ 10 ]':'M25','DSS [ 8 ]':'M19','Synaptic Diversity [ 8 ]':'M20','Softmax Confidence [ 18 ]':'M24','Head importance [ 18 ]':'M23','LogSynflow [ 42 ]':'M12','EZNAS [ 9 ]':'M15','Attention Confidence [ 18 ]':'M22','Activation Distance [ 6 ]':'M11'}
records[:]=[r for r in records if r['protocol']!='old_G2']
for row in rows[2:]:
 if row[0] not in mp:continue
 mid=mp[row[0]];category='static' if mid=='M01' else 'forward' if row[10]=='forward' else 'derivatives'
 add('old_G2',mid,'WikiText-103 implementation: '+row[0],{'kendall_tau':float(row[3]),'spearman_rho':float(row[4])},row,category=category,origin='primary_table',requirements_basis='P29 Table I Requirement Comparison; source-reported operation, no inheritance from G1')
p=next(p for p in protocols if p['id']=='old_G2');p['notes']='Полная колонка WikiText-103 для идентифицируемых O1-O3; 17 методов. Ours исключён: не указан вариант alpha. Требования приведены по таблице P29; LPZero здесь обозначен авторами как backward, поэтому классификация G1 не переносится. Перепечатанная колонка OpenWebText не используется (есть расхождения с P28).'
# Full P32 table, keeping original source labels and variant distinction.
rows=table('P32','S4.T1','narrow_sources')
headers=next(r for r in rows if len(r)==12 and 'Synaptic Diversity' in r)
values=next(r for r in rows if len(r)==12 and r[0]=='Spearman Coefficient')
extra={'Synaptic Diversity':'M20','Synaptic Saliency':'M21','Attention Importance':'M23','DSS-Indicator':'M19'}
for h,mid in extra.items():
 i=headers.index(h);add('old_G4',mid,h,{'spearman_rho':float(values[i])},values,origin='primary_table')
# GPT-2: orient correlation with PPL by a declared monotonic reversal, never abs().
rows=table('P29','S4.T2')
pid=protocol('gpt2_wikitext','GPT-2 / WikiText-103','P29','https://arxiv.org/html/2503.18646v1#S4.T2','Table II; §IV-C','-perplexity on WikiText-103 (higher is better)',200,'Исходный эталон PPL: меньше лучше. На графике -ρ и -τ, не |ρ|. Ours исключён: alpha не закреплён. Опечатка Synaptic Synaptic и Head confidence не присваиваются ID. Числа Table II имеют приоритет над отличающимися числами в тексте. Требования адаптаций - по описанию P29, а не оригинальному CV-методу.','author_comparison')
gm={'GraSP':'M06','EZNAS':'M15','Gradnorm':'M07','SNIP':'M05','Fisher':'M08','Jacobian Cosine':'M10','Synflow':'M04','#params':'M01','Activation distance':'M11','Attention confidence':'M22','LogSynflow':'M12','DSS':'M19','Synaptic Diversity':'M20','#Decoder.Params':'M02','Head Importance':'M23','LPZero':'M25'}
for row in rows[1:]:
 if row[0] not in gm:continue
 mid=gm[row[0]];cat='static' if mid in ['M01','M02'] else 'forward' if mid in ['M11','M22'] else 'derivatives'
 add(pid,mid,'GPT-2: '+row[0],{'spearman_rho':-float(row[1]),'kendall_tau':-float(row[2])},row,category=cat,raw_metrics={'spearman_rho':float(row[1]),'kendall_tau':float(row[2])},sign_transform='negate_due_to_PPL_target',origin='primary_table')
# BRP-NAS comparison shares the GRAF study's datasets/budgets and explicit framework.
rows=table('P12','A12.T28');row=next(r for r in rows if r[0]=='None (BRP-NAS)')
for di,ds in [(0,'CIFAR-10'),(1,'ImageNet16-120')]:
 for hi,H in enumerate([32,128,1024]):
  pid=f'graf_NAS-Bench-201_{ds}_{H}';v,sd=map(float,re.findall(r'\d+\.\d+',row[1+di*3+hi]))
  add(pid,'M42','BRP-NAS / no added features',{'kendall_tau':v},row,sd={'kendall_tau':sd},H=H,origin='primary_table')
  next(p for p in protocols if p['id']==pid)['locator']+=' + Appendix L, Table 28'
  next(p for p in protocols if p['id']==pid)['notes']+=' BRP-NAS без дополнительных признаков включён из Table 28: та же задача, H, 50 seeds; §4.5 явно сопоставляет RF и BRP. Тождество конкретных split IDs отдельно не заявляется.'
# ONNX-Net comparisons are author-reported, not claimed as an independently rerun benchmark.
pid=protocol('onnx_darts','NAS-Bench-301 / DARTS / H=100','P34','https://arxiv.org/pdf/2510.04938v2','Table 2 / PDF p.5','accuracy, NAS-Bench-301 / DARTS, as reported',100,'Таблица авторов, H=100. Происхождение эталонных качеств, test split и перенос baseline-результатов не прослежены достаточно для строгого общего эксперимента; вспомогательная таблица авторов. GNN/FLAN/RLM вне фиксированных идентифицированных вариантов O1-O3.','auxiliary')
for mid,var,tau in [('M44','CATE',.425),('M45','Arch2Vec',.333),('M48','ONNX-Net',.546)]:add(pid,mid,var,{'kendall_tau':tau},'P34 Table 2 / PDF p.5',H=100,origin='primary_pdf')
pid=protocol('onnx_einspace','einspace / CIFAR-10 / ONNX comparison','P34','https://arxiv.org/pdf/2510.04938v2','Appendix C, Table 8 / PDF p.14','CIFAR-10 accuracy','mirroring P14 settings','Авторы прямо заявляют mirroring Qin settings. RF/XGB/Qin повторяют опубликованные числа, не независимая репликация. Для проверяемости оставлено отдельной вспомогательной таблицей; не добавлять как новое свидетельство превосходства M46.','auxiliary')
for mid,var,tau in [('M38','RF, ZCP + GRAF',.514),('M39','XGB, ZCP + GRAF',.449),('M46','ModernBERT-large (Qin)',.612),('M48','ONNX-Net',.513)]:add(pid,mid,var,{'kendall_tau':tau},'P34 Appendix C Table 8 / PDF p.14',origin='primary_pdf')
# RNN figure: retain reported values without inventing a sign convention.
pid=protocol('rnn_reported','NAS-Bench-NLP / Penn Treebank / RNN','P27','https://aclanthology.org/2023.acl-long.142.pdf','Figure 1 / PDF p.6, printed p.2527','test loss; source-reported correlation convention',8795,'Числа воспроизведены с Fig.1. Знак корреляции в подписи и направление шкал требуют отдельного уточнения; не применяем abs или инверсию и не используем эту группу для основного отбора. Только сравнение как опубликовано.','auxiliary')
for mid,var,rho,tau in [('M11','Activation Distance',.232,.223),('M21','Synaptic Saliency',.091,.122),('M09','Jacobian Covariance',.016,.003),('M10','Jacobian Cosine',.074,.264),('M68','Hidden Covariance / layer 1',.405,.372),('M68','Hidden Covariance / layer 2',.416,.314),('M68','Hidden Covariance / layer 3',.333,.247)]:
 add(pid,mid,var,{'spearman_rho':rho,'kendall_tau':tau},'P27 Figure 1 / PDF p.6',orientation='reported_only',origin='primary_pdf_figure')
# Explicit decisions after primary-source review: excluded means incomparable here, not inferior.
EXCLUDED={
'M16':('P09 §3, Tables 1-4','В таблицах корреляций сравниваются компоненты, в том числе LogSynFlow; FreeREA как агрегат оценивается через результат эволюционного поиска. Нельзя присвоить корреляцию компонента всему алгоритму.'),
'M26':('P29 §III-D, Table I/II, Figures 7-9','В строке Ours не закреплён способ выбора alpha: калибровка по качествам или эвристика. Нельзя приписать одно число M26 или M27 и скрыть различие подготовки.'),
'M27':('P29 §III-D, Table I/II, Figures 7-9','Строка Ours не отделяет эвристический alpha от калиброванного; тот же результат нельзя дублировать для двух вариантов.'),
'M31':('P33 Table 1/2/5; Appendix A.3','NB101/201 используют PINAT fusion, а каталог фиксирует standalone MABN. Для ViT эталон получен AutoFormer-supernet. NDS использует standalone, но схема split/подбора в Appendix A неоднозначна. Нет достаточно надёжной общей группы для данного варианта.'),
'M35':('P36 §4.2-4.3, Table 1 / Fig.2','§4.2 называет final validation accuracy, §4.3 и Fig.2 - test accuracy; Table 1 не закрепляет эталон и одинаковую выборку baselines. Не смешивается с прозрачными live-группами. Перспективная data-free идея, но доказательство пока отдельно от основного отбора.'),
'M41':('P15 §4.4 / Fig.9; pp.13-14','τ=0.956 получено на 10 специально выбранных архитектурах, τ=0.649 - на другом validation-наборе. Нет общего correlation cohort с остальными методами; сравнение NAS search efficiency не заменяет его.'),
'M43':('P17 arXiv v3, §5-6 / Fig.5.1-6.1','Исследованы MAE предикторов и качество полного BO/NAS; компоненты/ансамбли меняются. Не найдено общего численного correlation cohort для итогового BANANAS и текущих кандидатов при совпадающем бюджете.'),
'M49':('P35 §4.1, Tables 1/3/4/5','В основных NB201-таблицах не закреплён целевой dataset; сравнение ONNX-to-text - замена кодирования внутри COLE, а не сравнение с полным ONNX-Net. Нельзя использовать как общий рейтинг этих алгоритмов.'),
'M50':('P37 Tables 7-9','P@100 измеряет попадание поиска в топ архитектур при бюджете B; это итог active search с acquisition, а не корреляция независимого оценщика. Общее сравнение с proxy-корреляциями некорректно.'),
'M54':('P21 §3.3 / Table 1','Оценка MSE и log-likelihood предсказания кривых на 16-fold CV гиперпараметров; отличается объект и метрика от ранжирования архитектур. Оставлен вне общего сравнения.'),
'M67':('P47 §4-5 / Figures 1-4; P12 §4.3','RF для clean/robust или совместной цели: меняются attack, epsilon и target. Каталожная строка объединяет варианты, а общий эксперимент с тем же target и конфигурацией не закреплён. Не приравнивать к M37 автоматически.'),

}
for mid,(loc,reason) in EXCLUDED.items():decisions.append(dict(method_id=mid,decision='excluded_from_general_comparison',locator=loc,reason=reason))

# Reader-facing protocol notes; retain raw observations separately.
next(p for p in protocols if p['id']=='old_G1')['notes']='500 FlexiBERT; proxy-input OpenWebText; эталон - средний downstream GLUE. Формула LPZero найдена с использованием качеств 50 архитектур; discovery и evaluation не считаются доказанно независимыми. Подготовка формулы требует H. Query time не сравнивается с discovery time.'
next(p for p in protocols if p['id']=='old_G4')['notes']='500 FlexiBERT; вход OpenWebText; случайная инициализация кандидатов. Используется взвешенная агрегация GLUE этой статьи. Не объединяется с обычным средним GLUE; Kendall τ не опубликован в использованной таблице.'
next(p for p in protocols if p['id']=='old_G6')['notes']='Официальная версия AutoML 2025: Table 1 и Table 7. Около 9k пар суммарно из восьми NAS runs: 6 train / 1 validation / 1 test. Корреляции вычислены на одном evaluation set. Для few-shot приведены средние трёх seeds и SE. Использование LM как оценщика не превращает CIFAR-10 в NLP-задачу.'

# Persist scoped review decisions; excluded does not mean inferior.
covered={r['method_id'] for r in records}
coverage=[]
for mid in MM:
 coverage.append(dict(method_id=mid,name=MM[mid]['name'],status=('numeric_cohort' if any(r['method_id']==mid and next(p for p in protocols if p['id']==r['protocol'])['tier']!='auxiliary' for r in records) else 'auxiliary_only' if mid in covered else 'excluded'),review=(EXCLUDED[mid][1] if mid in EXCLUDED else 'Есть отдельные сопоставимые контексты; выводы только внутри каждого из них.'),review_locator=(EXCLUDED[mid][0] if mid in EXCLUDED else ''),source_ids=ROWS[mid]['evidence'],protocols=sorted({r['protocol'] for r in records if r['method_id']==mid})))
for name,payload in [('protocols',protocols),('records',records),('decisions',decisions),('coverage',coverage)]:
 (D/(name+'.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(f'{len(protocols)} cohorts, {len(records)} method-context records, {len(covered)}/56 methods covered; {56-len(covered)} excluded after review')
