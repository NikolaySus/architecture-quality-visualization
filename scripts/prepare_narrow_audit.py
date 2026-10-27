"""Materialize the editorial audit for the frozen O1-O3 cohort.

Assignments below are reviewed assertions, not keyword inference. Source documents
are retained in tmp/source_audit and tmp/narrow_sources; hashes are embedded.
"""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import ROOT, load, comparison_methods

TAX = load('visualization_taxonomies')
SCOPE = [i for g in TAX['operation_groups'][:3] for i in g['ids']]
METHODS = {m['id']: m for m in comparison_methods()}
PAPERS = {p['id']: p for p in load('papers')}

# G = graph/configuration/size; W = weight values directly in the score;
# A = activations directly in the score; D = derivatives directly in the score.
# Merely computing activations to obtain a gradient does not add A.
SIGNALS = {
 'G': [1,2,3,36,41,42,43,44,45,46,47,48,49,54,69],
 'W': [26,27,70],
 'A': [11,14,22,24,25,29,68],
 'D': [7,9,10,15,17],
 'WD': [4,5,6,12,19,20,21,23,71],
 'AD': [8,13,32,33,35],
 'GA': [30],
 'GAD': [18],
 'WAD': [31,34],
 'GWAD': [16,37,38,39,50,51,52,67],
}
SETUP = {
 'fixed': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18,19,20,21,22,23,29,32,33,34,35,68,70,71],
 'distribution': [16,27,30,51],
 'search': [15,25],
 'calibration': [26],
 'fit': [31,36,37,38,39,41,42,43,44,45,46,48,49,50,67,69],
 'curves': [52,54],
 'prompt': [47],
}
# M24 is a fixed attention statistic.
SETUP['fixed'].append(24)
REP = {'architecture_pretrain':[44,45], 'finetuned_lm':[46], 'frozen_lm':[47,49], 'trained_lm':[48]}

# Reviewed source and locator for the added signal/operation/setup assertions.
EVIDENCE = [
 ([1,3,4,5,6,7,8,9,70,71], 'P01', '§3.2.1-3.2.3; pruning-score definitions; baselines',
  'Direct sizes, weight norms and saliency formulas; Fisher uses activation times its derivative.'),
 ([2], 'P26', '§3.1-3.2; Appendix A and Fig.10', 'Decoder parameter count excludes input embeddings and the final softmax projection.'),
 ([10,11,22,24,68], 'P27', '§3: Jacobian, hidden covariance and Transformer attention metrics',
  'Jacobian is derivative-based; covariance and attention confidence are forward-response statistics.'),
 ([12,16], 'P09', '§3.1-3.1.1; LogSynflow, linear regions, skip connections and population normalization',
  'FreeREA combines three sources and normalizes scores across candidates; no quality-label fitting.'),
 ([13], 'P06', '§3; Appendix A: NTK condition and linear regions', 'Combines derivative and activation signals.'),
 ([14], 'P07', '§3; Algorithm 1: Zen-Score', 'Gaussian inputs and forward perturbations; fixed score, no backward needed.'),
 ([15], 'P08', '§3: genetic programming and rank-correlation fitness', 'Formula discovery uses architecture quality labels.'),
 ([17], 'P10', '§3; zero-cost proxy definition', 'Per-sample parameter-gradient statistics.'),
 ([18], 'P11', '§3: expressivity, progressivity, trainability, complexity', 'Activations, Jacobian and FLOPs are combined.'),
 ([19,20,21], 'P30', '§3.2-3.4; Eqs. 4-7; all-ones input implementation', 'Both diversity and saliency use weights and their derivatives.'),
 ([23,25], 'P28', 'Appendix B, FlexiBERT proxy; Appendix D, head importance', 'Variant-specific signals; code determines head-tensor semantics.'),
 ([26,27], 'P29', '§III-C-D; Eqs. 3-10; Algorithm 1', 'Weight-only score; quality-calibrated and label-free alpha are separate variants.'),
 ([29,30], 'P32', '§III-B-C; §IV-C2', 'Activation patterns; regularization uses parameter count and sampled architecture sizes.'),
 ([31], 'P33', 'Appendix A-C: node-wise ZC collection and MABN predictor', 'Standalone MABN on node-wise ZC statistics; optional PINAT fusion is outside this row.'),
 ([32], 'P49', '§3.2.2, §3.3; author NASLib implementation', 'Feature SVD plus output curvature; derivatives along a synthetic input curve.'),
 ([33,34], 'P50', '§3.2-3.3.3', 'WRCor combines activation and gradient correlations; SJW/SPW add SynFlow.'),
 ([35], 'P36', '§3.2-3.3; Synthetic Loss Design', 'Activation geometry and gradient health on synthetic inputs and targets.'),
 ([36,37,38,39,69], 'P12', '§3-4; ZCP feature set and RF/XGB experiments', 'GRAF and one-hot are graph-only; full ZCP includes sizes, weights, activations and derivatives.'),
 ([41], 'P15', '§3: neural predictor and graph convolution', 'Architecture graph to supervised quality predictor.'),
 ([42], 'P16', '§3: binary relation predictor', 'Graph predictor trained on pairwise architecture performance relations.'),
 ([43], 'P17', '§3: path encoding and neural predictor ensemble', 'Structural encoding to supervised predictor ensemble.'),
 ([44], 'P18', '§3.3 and performance-prediction evaluation', 'Architecture pretraining uses computational attributes; downstream head uses qualities.'),
 ([45], 'P19', '§3-4: variational graph autoencoder and downstream NAS', 'Unsupervised architecture representation, followed by a supervised prediction head.'),
 ([46,47], 'P14', '§3.2: language-model surrogates; Appendix E prompts', 'Fine-tuning and few-shot prompting are different ways to use historical qualities.'),
 ([48], 'P34', '§4-5.2; Appendix H', 'Text of architecture in ONNX format feeds a quality-trained language model.'),
 ([49], 'P35', '§3.1-3.3', 'Frozen code-LM embeddings, PCA and supervised ranking head; no candidate execution.'),
 ([50], 'P37', '§3 ProxyFit; §4.1 proxy set', 'Offline quality supervision and active acquisition; full ZCP includes candidate execution.'),
 ([51,52], 'P38', '§3.2-3.3; five-proxy bank, consensus gate and anchor residual', 'Rank uses label-free population agreement; Refine fits residuals from anchor validation curves.'),
 ([54], 'P21', '§2.4 Eq.7; §3.3 footnote 2', 'Historical curves train the predictor; a new candidate supplies configuration and epoch only.'),
 ([67], 'P47', '§4.2 Tables 1-3; Tables 6-7', 'Quality-trained RF uses all ZCP, optionally with GRAF; robustness variant also needs attacks.'),
]

NOTES = {
 'M02':'Параметры decoder-блоков; input embeddings и финальная softmax projection исключены (Appendix A, Fig.10).',
 'M03':'FLOPs вычисляются по графу и форме входа. Профилировщик может использовать dummy forward; это не сигнал отклика и не время оценки.',
 'M05':'Исходная loss-based формула: W0 + X + targets. В G1 Electra-реализация использует сумму hidden states, поэтому U.',
 'M06':'Исходная loss-based формула с производными второго порядка. В G1 Electra использует сумму hidden states, поэтому U.',
 'M07':'Исходная норма градиента loss: X + targets. Electra-реализация G1 не использует targets, поэтому U.',
 'M08':'Fisher: квадрат произведения активации и её градиента; поэтому A+D, а не только D.',
 'M15':'Только Electra/FlexiBERT: градиент суммы hidden states; GPT-2 с loss сюда не переносится.',
 'M12':'Исходный LogSynFlow: синтетический вход. В Electra-реализации G1 передаются реальные тексты, поэтому U.',
 'M16':'LogSynFlow + linear regions + skip count; нормализация по популяции архитектур без H.',
 'M18':'FLOPs + forward-признаки + Jacobian; Gaussian input.',
 'M19':'Исходный ViT, вход из единиц; NLP-реализация является другим вариантом.',
 'M20':'Nuclear norms применяются и к весам, и к их градиентам. Только исходный ViT.',
 'M21':'Weight × gradient; исходный ViT. В численном G1 используется NLP-вариант с реальными текстами.',
 'M23':'Electra/FlexiBERT: weight × gradient суммы hidden states.',
 'M25':'FlexiBERT: head и activation получаются forward hooks. GPT-2 weight/gradient formula - другой вариант.',
 'M26':'Alpha калибруется по H; веса кандидата могут быть случайными либо готовыми.',
 'M27':'Alpha по согласованности компонент и размера на выборке архитектур, без H; W0 или Wp.',
 'M30':'SWAP плюс prior числа параметров; настройки распределения размеров по выборке G.',
 'M31':'MABN по node-wise ZCP; optional PINAT fusion не входит в эту строку. Fisher добавляет A.',
 'M32':'Реальный пример для feature SVD; синтетическая кривая для curvature. Код использует autograd первого и второго порядка.',
 'M33':'Авторский NB101/NB201: корреляции активаций и градиентов cross-entropy с targets из dataloader. Исправление U → T.',
 'M34':'SJW/SPW включают WRCor с cross-entropy/targets: исправление U → T. SynFlow добавляет синтетику; baseline с SNIP не включён.',
 'M35':'Синтетические targets не означают реальные размеченные примеры.',
 'M37':'Полный ZCP-вектор содержит в том числе params/FLOPs; G относится и к этому варианту без GRAF.',
 'M44':'Предобучение представления на архитектурах; H нужен для prediction head.',
 'M45':'Unsupervised graph representation; H нужен для prediction head.',
 'M46':'Предобученный LM дообучается на H. Его forward не является forward оцениваемой архитектуры.',
 'M47':'Готовый LM и исторические пары в prompt; fit весов на этих парах не требуется.',
 'M48':'Обученный LM по ONNX-тексту архитектуры; внешний pretrained checkpoint не объявляется обязательным.',
 'M49':'Готовый замороженный LM; PCA не требует quality labels, supervised ranker требует H.',
 'M50':'Offline H и активное получение качеств; полный ZCP-вектор включает все четыре источника.',
 'M51':'Target-free gate по согласованности proxy на наборе архитектур; fixed rank consensus.',
 'M52':'Validation-кривые обученных anchors относятся к подготовке; новая архитектура оценивается по статическим proxy.',
 'M54':'Вход x,t; частичная кривая новой архитектуры не требуется.',
 'M67':'Все ZCP; добавление GRAF не меняет профиль источников. Атаки - дополнительные операции robustness-варианта.',
 'M70':'Сумма layer-wise L2-норм весов в авторской реализации; forward не нужен.',
}

def main():
 sources={}
 old={r['paper_id']:r for r in load('source_audit/downloads')}
 fresh={}
 for filename in ['downloads.json','requests_downloads.json','extra_downloads.json','landing_downloads.json']:
  p=ROOT/'tmp/narrow_sources'/filename
  if p.exists():
   for r in json.loads(p.read_text()):
    if r['status']=='downloaded':fresh[r['id']]=r
 for ids,pid,locator,note in EVIDENCE:
  record=old.get(pid,{})
  url=fresh.get(pid,{}).get('url') or record.get('resolved_url') or PAPERS[pid]['canonical_url']
  sha=fresh.get(pid,{}).get('sha256') or record.get('sha256')
  sources[pid]={'paper_id':pid,'url':url,'locator':locator,'basis':note,'sha256':sha,
                'review_type':'primary_source_review' if sha else 'inherited_handoff_definition'}
 for pid in ['P15','P16','P17']:
  sources[pid]['review_type']='primary_landing_page_review'
  sources[pid]['locator']='Abstract / primary publication page; architecture encoding and supervised predictor'
 extras={
 'LPZ_EZNAS':('eznas.py','lpzero/predictor/measures/eznas.py','compute_eznas: ElectraModel branch'),
 'LPZ_HEAD':('lpzero_operators_zc_inputs.py','lpzero/operators/zc_inputs.py','compute_head and compute_activation: ElectraModel branches'),
 'LPZ_L2':('l2_norm.py','lpzero/predictor/measures/l2_norm.py','get_l2_norm_array'),
 }
 for key,(local,remote,locator) in extras.items():
  p=ROOT/'tmp/narrow_sources'/local
  sources[key]=dict(paper_id='P28',url='https://github.com/pprp/LPZero/blob/876432761a2ff67a77194018ebc88bdc42869974/'+remote,
                    locator=locator,basis='Author implementation; frozen commit.',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),review_type='author_code_review')
 for name in ['snip','grasp','grad_norm','fisher','synflow']:
  p=ROOT/'tmp/narrow_sources'/('lpz_'+name+'.py')
  sources['LPZ_'+name.upper()]=dict(paper_id='P28',url='https://github.com/pprp/LPZero/blob/876432761a2ff67a77194018ebc88bdc42869974/lpzero/predictor/measures/'+name+'.py',
    locator='ElectraModel branch; backward from hidden-state sum; synflow.py also defines compute_logsynflow_per_weight',basis='G1 input-access correction; applies to Electra/FlexiBERT only.',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),review_type='author_code_review')
 for key,local,remote,locator in [
  ('WRCOR_CODE','wrcor.py','foresight/pruners/measures/act_grad_cor_weighted.py','compute_act_grad_cor_weighted, lines 65-67: loss_fn(outputs, targets)'),
  ('WRCOR_LOADER','foresight_pruners_predictive.py','foresight/pruners/predictive.py','find_measures_arrays: F.cross_entropy, get_some_data, calc_measure'),
  ('WRCOR_RUNNER','nasbench201_pred.py','nasbench201_pred.py','lines 54, 83-87: real dataloader; default cross_entropy')]:
  p=ROOT/'tmp/narrow_sources'/local
  sources[key]=dict(paper_id='P50',url='https://github.com/kunjing96/ZSNAS-WRCor/blob/270ce7aecedc56538aba635754a7009c9223be15/'+remote,
    locator=locator,basis='Supersedes U classification: author protocol uses real examples and their targets.',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),review_type='author_code_review')
 p=ROOT/'tmp/narrow_sources/dextr_length.py'
 sources['DEXTR_CODE']=dict(paper_id='P49',url='https://github.com/rohanasthana/Dextr/blob/55bcd4333840dd7c67f62696e5394f92978b8960/NASLib/naslib/predictors/pruners/measures/dextr_utils/no_free_lunch_architectures/length.py',locator='get_extrinsic_curvature_opt, lines 59-97',basis='Two autograd derivatives along theta; no real targets.',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),review_type='author_code_review')
 lookup=lambda mapping: {f'M{n:02d}':key for key,nums in mapping.items() for n in nums}
 sig,setup,rep=map(lookup,[SIGNALS,SETUP,REP])
 evidence={f'M{n:02d}':pid for ids,pid,*_ in EVIDENCE for n in ids}
 rows=[]
 for mid in SCOPE:
  m=METHODS[mid];s=sig[mid];a='labeled_or_objective' if mid in ['M33','M34'] else m['data_access_at_use']
  synthetic=mid in ['M04','M12','M14','M16','M18','M19','M20','M21','M32','M34','M35','M51','M52'] or mid in ['M31','M37','M38','M39','M50','M67']
  operation='derivatives' if 'D' in s else 'forward' if 'A' in s else 'weights' if s=='W' else 'graph'
  use='synthetic' if a=='none' and synthetic else 'no_examples' if a=='none' else 'unlabeled' if a=='unlabeled' else 'objective'
  ev=[evidence[mid]]
  if mid=='M15':ev+=['LPZ_EZNAS']
  if mid=='M25':ev+=['LPZ_HEAD']
  if mid=='M70':ev+=['LPZ_L2']
  if mid=='M32':ev+=['DEXTR_CODE']
  if mid in ['M33','M34']:ev+=['WRCOR_CODE','WRCOR_LOADER','WRCOR_RUNNER']
  code={'M05':'SNIP','M06':'GRASP','M07':'GRAD_NORM','M08':'FISHER','M12':'SYNFLOW'}.get(mid)
  if code:ev+=['LPZ_'+code]
  rows.append(dict(method_id=mid,signal_profile=s,operation=operation,use_inputs=use,synthetic_component=synthetic,
                   setup=setup[mid],representation=rep.get(mid,'none'),evidence=ev,status='included',data_access_at_use=a,
                   access_correction='U → T; author loss/targets call chain' if mid in ['M33','M34'] else None,
                   variant_scope=m.get('access_review',{}).get('variant_scope','Определение метода в исходном корпусе'),
                   note=NOTES.get(mid,m['requirements_raw']),
                   source_access_audit=m.get('access_review')))
 assert set(sig)==set(setup)==set(SCOPE)
 payload=dict(version='1.0',scope_basis='Frozen IDs of O1-O3 in 01_mechanisms.pdf',scope_ids=SCOPE,
              excluded_scope_ids=['M28','M40','M72'],reviewed_on='2026-10-13',
              signal_rule='Only quantities entering the score/features directly; candidate activations and weights used solely to obtain derivatives do not add A/W. G includes sizes inside a full ZCP bank. Estimator-internal tensors are not candidate signals.',
              observation_access_overrides=[dict(block='G1',method_id=mid,data_access='unlabeled',source=source,
                reason='Electra/FlexiBERT uses real texts and backward from hidden states, without task targets.') for mid,source in [('M05','LPZ_SNIP'),('M06','LPZ_GRASP'),('M07','LPZ_GRAD_NORM'),('M08','LPZ_FISHER'),('M12','LPZ_SYNFLOW')]],
              sources=sources,methods=rows)
 (ROOT/'data/narrow_method_audit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(len(rows),'methods;',len(sources),'source records')

if __name__=='__main__':main()
