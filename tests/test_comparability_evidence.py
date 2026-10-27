import json
from pathlib import Path
from collections import Counter
D=Path('data/comparability')
def data(name):return json.loads((D/(name+'.json')).read_text())

def test_contexts_do_not_pool_datasets_or_budgets():
 p={p['id']:p for p in data('protocols')};r=data('records')
 assert len(p)==31
 assert len(r)==235
 assert all(x['protocol'] in p and x['source_row'] for x in r)
 keys=[(x['protocol'],x['method_id'],x['variant']) for x in r]
 assert len(keys)==len(set(keys))
 for pid in p:
  budgets={x['H'] for x in r if x['protocol']==pid and 'H' in x}
  assert len(budgets)<=1

def test_wrcor_uses_full_benchmark_column():
 r=[r for r in data('records') if r['protocol']=='wrcor_nb201_full']
 s={r['variant']:r['metrics']['spearman_rho'] for r in r}
 assert s['SJW (Ours)']==.799 and s['WRCor (Ours)']==.812
 assert .851 not in s.values()

def test_live_cora_does_not_inherit_sourced_baselines_or_wrong_swap_variant():
 r=[r for r in data('records') if r['protocol'].startswith('cora_nb201_')]
 assert not {'M08','M71','M29'}&{r['method_id'] for r in r}
 assert len([x for x in r if x['method_id']=='M30'])==3
 assert all(x['category']=='derivatives' for x in r if x['method_id']=='M32')

def test_negative_and_inconvenient_results_are_preserved():
 r=data('records')
 q=next(x for x in r if x['method_id']=='M47' and x['variant'].startswith('Llama'))
 assert q['metrics']['spearman_rho']==-.087
 vit=[x for x in r if x['protocol'].startswith('cora_vit_')]
 assert len(vit)==28
 assert any(x['method_id']=='M51' and x['metrics']['spearman_rho']==.002 for x in vit)

def test_scope_audit_distinguishes_pending_from_weak():
 c=data('coverage')
 assert len(c)==56
 assert Counter(x['status'] for x in c)=={'numeric_cohort':41,'auxiliary_only':4,'excluded':11}


def test_nlp_target_is_not_proxy_input_and_sign_is_not_absolute():
 p={p['id']:p for p in data('protocols')};r=data('records')
 assert 'GLUE' in p['old_G2']['target'] and p['old_G2']['proxy_input']=='WikiText-103'
 q=next(x for x in r if x['protocol']=='old_G2' and x['method_id']=='M25')
 assert q['metrics']['spearman_rho']==.187
 g=[x for x in r if x['protocol']=='gpt2_wikitext']
 assert all(x['metrics'][k]==-x['raw_metrics'][k] for x in g for k in x['metrics'])
 assert next(x for x in g if x['method_id']=='M06')['metrics']['spearman_rho']<0

def test_auxiliary_does_not_enter_shortlist():
 p={p['id']:p for p in data('protocols')}
 for s in data('shortlist'):
  assert all(p[x]['tier']!='auxiliary' for x in s['protocols'])
  assert not set(s['method_ids']) & {'M44','M45','M48','M68'}
 assert all(x['review'] for x in data('coverage') if x['status']=='excluded')

def test_source_snapshots_have_real_cells_and_hashes():
 import hashlib
 for f in D.glob('P*_*.json'):
  d=json.loads(f.read_text())
  if 'source_sha256' not in d:continue
  assert d['rows'] and len(d['source_sha256'])==64
  assert hashlib.sha256(Path(d['source']).read_bytes()).hexdigest()==d['source_sha256']
