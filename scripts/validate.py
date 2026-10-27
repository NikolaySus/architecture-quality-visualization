"""Validate schema and cross references without requiring pytest."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import jsonschema
from corpus import load, ROOT
papers=load('papers'); methods=load('methods'); observations=load('observations')
for name,records in [('papers',papers),('methods',methods),('observations',observations)]:
    jsonschema.validate(records,json.loads((ROOT/'schema'/f'{name}.schema.json').read_text()))
    ids=[r['id'] for r in records]
    if len(set(ids))!=len(ids): raise ValueError(f'Duplicate {name} IDs')
pp={p['id'] for p in papers}; mm={m['id'] for m in methods}
for m in methods:
    assert m['origin_paper_id'] is None or m['origin_paper_id'] in pp
    assert set(m['evaluation_paper_ids'])<=pp
for o in observations:
    assert o['evaluation_paper_id'] in pp
    assert o['evidence']['source_paper_id']==o['evaluation_paper_id']
    assert (o['method_id'] in mm and not o['method_candidates']) or (o['method_id'] is None and len(o['method_candidates'])>0 and set(o['method_candidates'])<=mm)
print(f'Validated: {len(papers)} papers, {len(methods)} methods, {len(observations)} observations')
