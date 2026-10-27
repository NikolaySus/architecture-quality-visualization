"""Scientific invariants for alternate report partitions and visual evidence."""
import json
from collections import Counter
import pytest
from corpus import ROOT,load,exclusion_reason,access
from variant_charts import METHODS,MM,OP,OPS,OBS,AK,operation_groups,method_cells

def test_operational_partition_and_boundary_cases():
    ids=[i for g in OPS for i in g['ids']]
    assert Counter(ids)==Counter(m['id'] for m in METHODS)
    assert len(ids)==69
    assert OP['M54']==OP['M31']==OP['M52']=='O3'
    assert OP['M51']=='O2'
    assert OP['M58']=='O4'
    assert OP['M65']=='O5'
    assert all(m['data_access_at_use'] in AK for m in METHODS)
    assert Counter(m['data_access_at_use'] for m in METHODS)==dict(none=30,unlabeled=18,labeled_or_objective=21)
    cells=method_cells(operation_groups())
    assert sum(c['count'] for c in cells)==69
    assert Counter(i for c in cells for i in c['method_ids'])==Counter(ids)

def test_report_visual_evidence_not_duplicated_or_pooled():
    for mid in ['01_mechanisms','02_constraints','03_family_atlas']:
        manifest=json.loads((ROOT/'exports/variants'/f'{mid}_manifest.json').read_text())
        assert Counter(manifest['method_ids'])==Counter(list(MM))
        assert len(manifest['figures'])==4
        records=[]
        for fig in manifest['figures'][1:]:records+=json.loads((ROOT/'exports/variants'/f'{fig}.json').read_text())
        assert Counter(r['id'] for r in records)==Counter(o['id'] for o in OBS)
        raw={o['id']:o for o in load('observations')}
        for r in records:assert r==raw[r['id']]
        assert not ({r['method_id'] for r in records}&{'M28','M40','M72'})
        assert not any(exclusion_reason(r) for r in records)
        assert len(records)==43

def test_variant_access_and_uncertainty_retained():
    observations=[o for o in OBS if o['block']=='G1']
    assert next(m for m in METHODS if m['id']=='M04')['data_access_at_use']=='none'
    assert access(next(o for o in observations if o['method_id']=='M04'),MM)=='unlabeled'
    assert len({o['method_variant_id'] for o in OBS if o['block']=='G6' and o['method_id']=='M46'})==4
    assert all(o['metrics'][0]['uncertainty_type']=='SD' and o['n_repeats']==50 for o in OBS if o['block']=='G5')

def test_report_text_and_rejected_design_gate():
    from pypdf import PdfReader
    review=load('visualization_design_review')
    decisions={x['id']:x for x in review['decisions']}
    for mid in ['01_mechanisms','02_constraints','03_family_atlas']:
        manifest=json.loads((ROOT/'exports/variants'/f'{mid}_manifest.json').read_text())
        assert all(decisions[f]['decision']=='selected' for f in manifest['figures'])
        pdf=PdfReader(ROOT/manifest['pdf'])
        assert all(len(p.extract_text())>130 for p in pdf.pages)
        text='\n'.join(p.extract_text() for p in pdf.pages)
        assert '43 наблюдения' in text
        assert 'C_setup' in text
        assert 'Методы, не поддающиеся анализу' in pdf.pages[-1].extract_text()
        assert len(manifest['method_ids'])==69
