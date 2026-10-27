from scripts import build_evaluation_order as eo


def test_transitive_comparisons_can_complete_order(monkeypatch):
    monkeypatch.setattr(eo,'ATOMS',{'x':{'a':3,'b':2},'y':{'b':7,'c':1}})
    assert eo.relation(['x','y'])==('total',['a','b','c'])


def test_shared_anchor_does_not_order_branches(monkeypatch):
    monkeypatch.setattr(eo,'ATOMS',{'x':{'a':3,'b':2},'y':{'a':7,'c':1}})
    assert eo.relation(['x','y'])[0]=='partial'


def test_cycle_and_ties_are_not_strict_total_orders(monkeypatch):
    monkeypatch.setattr(eo,'ATOMS',{'x':{'a':3,'b':2},'y':{'b':3,'a':2},'z':{'a':1,'b':1}})
    assert eo.relation(['x','y'])[0]=='cycle'
    assert eo.relation(['z'])[0]=='partial'


def test_corpus_maximal_partition():
    groups=eo.solve()
    assert len(groups)==7
    merged=[g for g in groups if len(g)>1]
    assert sorted(len(g) for g in merged)==[2,3]
    assert {next(iter(g))[0] for g in merged}=={'G2','G5'}
    for group in groups:assert eo.relation(group)[0]=='total'
