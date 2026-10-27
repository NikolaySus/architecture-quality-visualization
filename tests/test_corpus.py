import json
import xml.etree.ElementTree as ET
from collections import Counter
import pytest
import jsonschema
from corpus import load, eligible, metric, ROOT, access
from charts import chart, export, map_chart, interactive_svg
import matplotlib.pyplot as plt


def test_import_counts_references_and_schema():
    papers=load('papers'); methods=load('methods'); obs=load('observations')
    assert [len(papers),len(methods),len(obs)]==[50,72,68]
    for records in [papers,methods,obs]: assert len({r['id'] for r in records})==len(records)
    pp={p['id'] for p in papers}; mm={m['id'] for m in methods}
    for m in methods:
        assert m['origin_paper_id'] in pp or m['id']=='M72'
        assert set(m['evaluation_paper_ids'])<=pp
    for o in obs:
        assert o['evaluation_paper_id'] in pp
        assert o['method_id'] in mm or (o['method_id'] is None and o['method_candidates']==['M26','M27'])
        assert o['evidence']['source_paper_id']==o['evaluation_paper_id']
    jsonschema.validate(obs,json.loads((ROOT/'schema/observations.schema.json').read_text()))
    assert Counter(o['block'] for o in obs)==dict(G1=15,G2=8,G3=5,G4=11,G5=12,G6=6,G7=5,G8=6)


def test_values_sign_and_unknown_costs():
    obs=load('observations')
    for o in obs:
        assert o['candidate_query_cost'] is None
        for m in o['metrics']:
            assert m['value']==m['raw_metric_value']
            assert m['oriented_metric_value'] is None
    syn=next(o for o in obs if o['block']=='G2' and o['method_id']=='M04')
    assert metric(syn,'spearman_rho')['value']==-.470
    assert access(syn,{m['id']:m for m in load('methods')})=='unknown'
    unresolved=[o for o in obs if o['method_candidates']]
    assert len(unresolved)==1
    assert unresolved[0]['method_variant_id']=='zerolm_reported_unspecified'
    assert len([o for o in obs if eligible(o,'A') is None])==0
    assert len([o for o in obs if eligible(o,'A',provisional=True) is None])==2
    assert len([o for o in obs if eligible(o,'E','kendall_tau') is None])==12
    assert not [o for o in obs if o['domain']=='text_embedding']
    assert all(o['domain']=='relevant' for o in obs if o['block'] in ['G5','G6','G7'])


def test_budget_sd_variants():
    obs=load('observations')
    assert len({o['method_variant_id'] for o in obs if o['block']=='G6' and o['method_id']=='M46'})==4
    g5=[o for o in obs if o['block']=='G5']
    assert {o['n_train_predictor'] for o in g5}=={32,128,1024}
    assert all(o['metrics'][0]['uncertainty_type']=='SD' and o['n_repeats']==50 for o in g5)
    assert all(o['dataset']=='unresolved' for o in obs if o['block']=='G7')
    c=next(c for c in load('context') if c['id']=='C02')
    assert c['derived_value']==pytest.approx(c['value']/c['n_architectures'])


def test_protocol_barrier_and_svg_semantics():
    obs=load('observations')
    with pytest.raises(ValueError): chart(obs,name='spearman_rho')
    fig,records=map_chart(load('methods'))
    svg=interactive_svg(fig,records)
    assert 'stroke-dasharray' in svg
    assert '0 подтверждённых работ' in svg
    assert 'point_M36' in svg
    assert '?observation=M36' in svg
    assert 'target="_blank"' in svg
    assert any(el.tag.endswith('}title') for el in ET.fromstring(svg).iter())
    assert len(records)==69
    plt.close(fig)


def test_zoom_counts_only_visible_observations():
    oo=[o for o in load('observations') if o['block']=='G2']
    fig,visible=chart(oo,'A',provisional=True,zoom=1)
    assert len(visible)==2
    assert all(o['costs'][0]['value']<=1 for o in visible)
    plt.close(fig)


def test_audit_partition_and_no_unknown_in_comparisons():
    from corpus import comparison_methods, exclusion_reason
    from charts import family_overview_chart
    audit=load('access_audit')
    assert len(audit)==35
    assert Counter(a['status'] for a in audit)=={'resolved':32,'excluded':3}
    methods=comparison_methods()
    assert len(methods)==69
    assert all(m['data_access_at_use']!='unknown' for m in methods)
    assert {m['id'] for m in load('methods')} - {m['id'] for m in methods}=={'M28','M40','M72'}
    assert all(a['url'] and a['locator'] and a['source_version'] for a in audit)
    fig,families=family_overview_chart(load('methods'))
    assert len(families)==5
    assert sum(len(f['method_ids']) for f in families)==69
    assert all(f['data_access_category']!='unknown' for f in families)
    plt.close(fig)
    mm={m['id']:m for m in load('methods')}
    for o in load('observations'):
        if eligible(o,'B') is None: assert access(o,mm)!='unknown'
        if o['block'] in ['G3','G7','G8'] or o['method_candidates']: assert exclusion_reason(o)
    # Evidence from original ViT must not silently classify NLP DSS.
    assert all(exclusion_reason(o) for o in load('observations') if o['method_id']=='M19')
    assert mm['M54']['data_access_at_use']=='none'
    assert mm['M35']['visual_class']=='relevant'
