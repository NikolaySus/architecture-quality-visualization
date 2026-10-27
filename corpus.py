"""Data access, explicit plot eligibility and portable exports."""
import csv, io, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(name):
    records=json.loads((ROOT/'data'/f'{name}.json').read_text())
    if name=='methods' and (ROOT/'data/access_audit.json').exists():
        audit={r['method_id']:r for r in load('access_audit')}
        for m in records:
            m['analysis_status']='included'
            if m['id'] in audit:
                a=audit[m['id']]; m['access_review']=a
                m['analysis_status']='excluded' if a['status']=='excluded' else 'included'
                if a['status']=='resolved':
                    m['data_access_at_use']=a['data_access_at_use']
                    m['requirements_raw']='Применение: '+a['use_requirements']+' Подготовка: '+a['setup_requirements']
                    m['setup_data_requirements']=a['setup_requirements']
                    m['mechanism'] += ' | Уточнённый вариант: '+a['variant_scope']+' | '+a['paper_id']+', '+a['locator']
                if m['id']=='M35':
                    m['visual_class']='relevant';m['application_evidence']='R; CV-протокол проверен по P36, §4'
    return records

def metric(o, name):
    return next((m for m in o['metrics'] if m['name']==name), None)

def access(o, methods):
    # SynFlow's NLP implementation is unresolved; do not inherit origin's data-free claim.
    if o['block']=='G1' and o['method_id'] in ['M04','M20','M21']: return 'unlabeled'
    if o['method_id']=='M04': return 'unknown'
    if o['method_candidates']: return 'unknown'
    if o['method_id'] in ['M20','M21']: return 'unknown'
    return methods[o['method_id']]['data_access_at_use']

def comparison_methods():
    return [m for m in load('methods') if m.get('analysis_status')=='included']

def exclusion_reason(o, plot='metric'):
    methods={m['id']:m for m in load('methods')}
    if o['method_id'] and methods[o['method_id']].get('analysis_status')=='excluded':
        return 'Метод исключён: '+methods[o['method_id']]['access_review']['reason']
    if o['method_candidates']: return 'Не закреплён вариант ZeroLM'
    if o['block']=='G7': return 'Не установлен target dataset Table 1'
    if o['block']=='G3': return 'Не установлена ориентация корреляции относительно perplexity'
    if o['block']=='G8': return 'Summary/search observations; не единый протокол корреляции'
    if o['method_id'] in ['M15','M23','M25'] and o['block']!='G1':
        return 'Входы проверены для FlexiBERT реализации P28; перенос на эту адаптацию не подтверждён'
    if o['block']!='G1' and o['method_id'] in ['M04','M19','M20','M21'] and o['domain']=='nlp_transformer':
        return 'Не завершена проверка входов NLP-адаптации; требования origin не наследуются'
    if plot=='B' and access(o,methods)=='unknown': return 'Не установлены входы конкретного варианта'
    return None

def eligible(o, plot, name='spearman_rho', provisional=False):
    reason=exclusion_reason(o,plot)
    if reason: return reason
    if metric(o,name) is None: return 'нет выбранной метрики'
    if plot=='A':
        if not o['costs']: return 'нет измерения времени'
        c=o['costs'][0]
        if not provisional and (c['hardware'] is None or c['scope']!='candidate_query' or c['accounting_completeness']!='verified'):
            return 'не установлены аппаратура / полный scope затрат'
    if plot=='E' and o.get('n_train_predictor') is None: return 'нет бюджета обучающих меток'
    if plot=='C': return 'нет совместимой пары setup / candidate query'
    return None

def flatten(observations):
    result=[]
    for o in observations:
        row={k:v for k,v in o.items() if k not in ['metrics','costs','evidence']}
        for m in o['metrics']:
            row[m['name']]=m['raw_metric_value']; row[m['name']+'_SD']=m['uncertainty']
        for k,v in o['evidence'].items(): row['evidence_'+k]=v
        row['costs_json']=json.dumps(o['costs'],ensure_ascii=False)
        result.append({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    return result

def csv_bytes(observations):
    rows=flatten(observations)
    out=io.StringIO(); fields=list(dict.fromkeys(k for r in rows for k in r))
    if fields:
        writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return out.getvalue().encode('utf-8-sig')
