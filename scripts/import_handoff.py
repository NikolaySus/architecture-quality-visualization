"""Reproducible, lossless import of the supplied handoff v0.2 tables."""
import json, re, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'architecture_quality_visualization_handoff.md'
s = source.read_text()
def save(name, data):
    (ROOT/'data'/f'{name}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def rows(text):
    return [[c.strip() for c in l.strip('|').split('|')] for l in text.splitlines() if l.startswith('| ') and not l.startswith('|---')]
def section(start, end):
    return s.split(start,1)[1].split(end,1)[0]
papers=[]
for row in rows(section('### 8.2.', '### 8.3.')):
    if not re.fullmatch(r'P\d+', row[0]): continue
    pid,link,byline,status=row
    title,url=re.search(r'\[(.*?)\]\((.*?)\)',link).groups()
    papers.append(dict(id=pid,title=title,canonical_url=url,authors=None,first_author_display=byline.split(';')[0],bibliography_raw=byline,verification_level=status[0],verification_basis='handoff v0.2; not independently reproduced',role=status[3:],source_notes=link,visual_class=None,accessed_at=None))
methods=[]
for row in rows(section('### 8.3.', '### 8.4.')):
    if not re.fullmatch(r'M\d+',row[0]): continue
    mid,mechanism,inputs,cls=row
    refs=list(dict.fromkeys(re.findall(r'P\d\d',mechanism)))
    evals=list(dict.fromkeys(refs+re.findall(r'P\d\d',cls)))
    n=int(mid[1:])
    family=('Статические признаки' if n in [1,2,3] else 'Scaling laws' if 59<=n<=62 else 'Общие / предсказанные веса' if 63<=n<=65 else 'Transferability' if n==66 else 'Learning curves / hybrid' if 52<=n<=58 else 'Surrogate models' if n in [31,67,69] or 36<=n<=50 else 'Zero-cost proxies')
    # Only explicitly supported access requirements; unresolved variants stay unknown.
    no={1,2,3,4,12,14,26,27,36,41,42,43,44,45,46,47,48,49,69,70}
    unlabeled={9,10,11,22,24,29,30,32,33,68}
    labeled={5,6,7,8,17,56,66}
    access='none' if n in no else 'unlabeled' if n in unlabeled else 'labeled_or_objective' if n in labeled else 'unknown'
    methods.append(dict(id=mid,name=mechanism.split(';')[0],mechanism=mechanism,origin_paper_id=None if n==72 else refs[0],evaluation_paper_ids=evals,visual_class={'N':'nlp_transformer','R':'relevant','?':None}[cls[0]],application_evidence=cls,family_tags=[family],priority=re.search(r'P[012](?!\d)',cls).group(),data_access_at_use=access,requirements_raw=inputs,setup_data_requirements=inputs,history_labels_required=True if n in list(range(36,51))+[15,25,26,31,52,53,54,58,59,60,61,62,67,69] else None,synthetic_inputs_required=True if n in [4,12,14] else None,scope_relation='adjacent' if n in [65,66] else 'conditional' if n in [59,60,61,62] else 'direct',input_source='synthetic' if n in [4,12,14] else 'unknown',weights_state='unknown',gradient_requirement=None,candidate_training_budget=None,proxy_discovery_required=True if n in [15,25] else None))
# Source class is about the source's own experiments, not later evaluations.
for p in papers:
    n=int(p['id'][1:])
    p['visual_class']=None if n==36 else 'nlp_transformer' if n in [26,27,28,29,31,32,39,40,41,42,43,44] else 'relevant'
    years=re.findall(r'20\d\d',p['bibliography_raw'])
    p['year_publication']=int(years[0]) if years else None
    p['year_preprint']=None
    arxiv=re.search(r'arxiv.org/(?:abs|html)/(\d{4}\.\d{4,5})(v\d+)?',p['canonical_url'])
    p['arxiv_id']=arxiv.group(1) if arxiv else None
    p['arxiv_version']=arxiv.group(2) if arxiv else None
    p['publication_status']='preprint' if 'preprint' in p['bibliography_raw'] else 'as stated in bibliography_raw'
    p['doi']=None; p['pdf_url']=None; p['code_url']=None; p['data_url']=None
    p['authors_missing_reason']='not_extracted'
byid={m['id']:m for m in methods}
configs=[
('G1','P28','lpzero2024_flexibert_t2','ACL_official_PDF','Table 2, printed p.8596 / PDF p.5','https://aclanthology.org/2024.findings-emnlp.502.pdf','FlexiBERT','GLUE','OpenWebText',500),
('G2','P29','zerolm2025_flexibert_wikitext_t1','arxiv_v1','Table I; IV-A','https://arxiv.org/html/2503.18646v1','FlexiBERT','GLUE','WikiText-103',500),
('G3','P28','lpzero2024_gpt2_t3','ACL_official_PDF','Table 3, printed p.8597 / PDF p.6','https://aclanthology.org/2024.findings-emnlp.502.pdf','GPT-2','WikiText-103','WikiText-103',200),
('G4','P32','swap2026_flexibert_t1','arxiv_v1','Table I; IV-B','https://arxiv.org/html/2605.07378v1','FlexiBERT','GLUE weighted','OpenWebText',500),
('G5','P12','graf2024_nb101_c10_t6','arxiv_v2','Appendix F, Table 6','https://arxiv.org/html/2404.16551v2','NAS-Bench-101','CIFAR-10',None,None),
('G6','P14','qin2025_cifar10_t1','arxiv_v1','Table 1; Data paragraph','https://arxiv.org/html/2504.12971v1','einspace','CIFAR-10',None,None),
('G7','P35','cole2026_nb201_base_t1','arxiv_v1','4.1.1-4.1.2, Table 1','https://arxiv.org/html/2605.15649v1','NAS-Bench-201','unresolved',None,None)]
observations=[]; groups=[]
def metric(name,value,sd=None):
    return dict(name=name,raw_metric_value=float(value),value=float(value),oriented_metric_value=None,sign_transform='none',reported_sign_convention='as reported',uncertainty=sd,uncertainty_type='SD' if sd is not None else None,extraction_status='reported')
for gi,(gid,pid,group,version,locator,url,space,dataset,proxy,n_eval) in enumerate(configs):
    block=section(f'#### {gid}.',f'#### G{gi+2}.')
    groups.append(dict(id=group,block=gid,paper_id=pid,source_version=version,url=url,locator=locator,search_space=space,target_eval_dataset=dataset,proxy_input_dataset=proxy,notes=block.split('\n|')[0].strip()+'\n'+block[block.rfind('\n|')+1:].split('\n',1)[-1].strip()))
    for row in rows(block):
        if not row[0].startswith('M'): continue
        mid=row[0].split(':')[0]; name=row[1] if gid not in ['G3','G5','G7'] else (row[0].split(':',1)[-1].strip() if gid=='G5' else byid[mid]['name'])
        budgets=[32,128,1024] if gid=='G5' else [int(row[1])] if gid=='G7' else [None]
        for bi,budget in enumerate(budgets):
            mets=[]; costs=[]
            if gid in ['G1','G2']: mets=[metric('kendall_tau',row[2]),metric('spearman_rho',row[3])]
            if gid=='G3': mets=[metric('kendall_tau',row[1]),metric('spearman_rho',row[2])]
            if gid=='G4': mets=[metric('spearman_rho',row[2])]
            if gid=='G5':
                val,sd=map(float,row[bi+1].split(' ± ')); mets=[metric('kendall_tau',val,sd)]
            if gid=='G6': mets=[metric('spearman_rho',row[2]),metric('kendall_tau',row[3])]
            if gid=='G7': mets=[metric('kendall_tau',row[2])]
            if gid=='G2' and row[4]!='null':
                costs=[dict(quantity='reported_time',value=float(row[4]),unit='s',scope='reported_average_unresolved',hardware=None,accounting_completeness='provisional',batch_size=128,sequence_length=256,setup_included=None,label_generation_included=None)]
            oid=f'{gid}_{len(observations)+1:03}'
            observations.append(dict(id=oid,block=gid,method_id=None if '/' in mid else mid,method_candidates=['M26','M27'] if '/' in mid else [],method_variant_id='zerolm_reported_unspecified' if '/' in mid else f'{mid}_{gid}_{name}',variant_label=name,evaluation_paper_id=pid,comparison_group_id=group,domain='nlp_transformer' if gi<4 else 'relevant',dataset=dataset,search_space=space,proxy_input_dataset=proxy,target_direction='min' if gid=='G3' else 'max',target_metric='perplexity' if gid=='G3' else 'validation_accuracy' if gid=='G5' else 'reported_quality',n_eval=n_eval,n_train_predictor=budget,n_repeats=50 if gid=='G5' else 100 if gid=='G7' else None,aggregation_scope='mean, 10 folds x 10 seeds' if gid=='G7' else 'mean over runs' if gid=='G5' else 'reported',training_recipe=None,architecture_ids_hash=None,split_overlap_status='unknown',ground_truth_kind='measured',predictor_split='6 train / 1 validation / 1 test NAS runs' if gid=='G6' else None,metrics=mets,costs=costs,candidate_query_cost=None,plot_readiness='cost_metric_provisional' if costs else 'budget_metric' if budget else 'metric_only',missing_reason='cost scope and hardware unresolved' if costs else 'not_extracted',sign_status='unresolved_perplexity_orientation' if gid=='G3' else 'reported',evidence=dict(source_paper_id=pid,source_version=version,url=url,locator=locator,original_row_label=' | '.join(row),reported_or_derived='reported',extraction_route='handoff v0.2',verified_at=None)))
# G8 summary results never enter single-task comparison groups.
for mid,pid,space,dataset,metric_name,value,budget in [('M50','P37','NAS-Bench-201','CIFAR-10','top100_recall',0.523,200),('M50','P37','NAS-Bench-201','CIFAR-100','top100_recall',0.658,200)]+[('M52','P38',space,'multiple / unresolved','spearman_rho',v,None) for space,v in [('NB201',.946),('NB101',.715),('TNB101',.786),('NATS-SSS',.894)]]:
    p=next(p for p in papers if p['id']==pid)
    observations.append(dict(id=f'G8_{len(observations)+1:03}',block='G8',method_id=mid,method_candidates=[],method_variant_id=f'{mid}_abstract_summary',variant_label=byid[mid]['name'],evaluation_paper_id=pid,comparison_group_id=f'{pid}_abstract_{space}_{dataset}',domain='relevant',dataset=dataset,search_space=space,proxy_input_dataset=None,n_train_predictor=None,search_evaluations=budget,n_repeats=None,aggregation_scope='abstract summary; full protocol pending',metrics=[metric(metric_name,value)],costs=[],candidate_query_cost=None,plot_readiness='metric_only',missing_reason='full_protocol_pending',sign_status='reported',evidence=dict(source_paper_id=pid,source_version='handoff abstract record; version not pinned',url=p['canonical_url'],locator='abstract',original_row_label=f'{space}; {dataset}; {value}',reported_or_derived='reported',extraction_route='handoff v0.2')))
context=[
 dict(id='C01',method_id='M25',value=10,unit='GPU-hours',scope='proxy_discovery',hardware='A6000/H800; timing device not separated',n_discovery=50,source_paper_id='P28',locator='4.1, p.8597',notes='Excludes unknown label generation cost; split overlap unknown'),
 dict(id='C02',method_id='M36',value=6.1,unit='s',scope='feature_extraction_batch',hardware='Ryzen 7 3800X',n_architectures=10000,n_repeats=10,source_paper_id='P12',locator='Appendix E, Table 4',derived_value=.00061,derivation='6.1 / 10000',derived_scope='feature_extraction_amortized',notes='Not RF query time or single-call latency'),
 dict(id='C03',method_id='M40',value=7.5,unit='min',scope='predictor_training_median',source_paper_id='P13',locator='v1 Appendix A.5',approximate=True),
 dict(id='C04',method_id='M40',value=1,unit='min',scope='transfer_maximum',source_paper_id='P13',locator='v1 Appendix A.5',approximate=True),
 dict(id='C05',method_id='M52',value=.01,unit='fraction',scope='refinement_unresolved_denominator',source_paper_id='P38',locator='abstract',approximate=True,notes='Denominator and anchor budget unresolved; not query time')]
for c in context:
    c['url']=next(p['canonical_url'] for p in papers if p['id']==c['source_paper_id']); c['missing_reason']='not_extracted'; c['reported_or_derived']='reported with explicit derived field' if 'derived_value' in c else 'reported'
for o in observations:
    for mid in ([o['method_id']] if o['method_id'] else o['method_candidates']):
        if o['evaluation_paper_id'] not in byid[mid]['evaluation_paper_ids']:
            byid[mid]['evaluation_paper_ids'].append(o['evaluation_paper_id'])
save('papers',papers); save('methods',methods); save('observations',observations); save('groups',groups); save('context',context)
save('manifest',dict(version='0.2-import.1',source=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),literature_cutoff='2026-09-29',counts=dict(papers=len(papers),methods=len(methods),observations=len(observations)),authors_status='Full author lists not extracted; original display names retained'))
print(len(papers),len(methods),len(observations))
