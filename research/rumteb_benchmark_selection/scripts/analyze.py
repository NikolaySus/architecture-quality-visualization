"""Audit the retained September 2026 snapshots without network access."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'ai-sage/Giga-Embeddings-instruct-10B-A1.8B-0826'


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def audit():
    provenance = load('data/provenance.json')
    for filename, expected in provenance['files'].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected['sha256'], filename

    workbook = openpyxl.load_workbook(ROOT / 'inputs/MTEB_rus_v1_1_23_benchmarks.xlsx', data_only=True)
    overview = [list(row) for row in workbook.worksheets[0].iter_rows(min_row=6, max_row=28, values_only=True)]
    assert len(overview) == 23 and len(workbook.sheetnames) == 3
    assert len({row[1] for row in overview}) == 23
    selected = load('data/selected_benchmarks.json')
    selected_names = [row['name'] for row in selected]
    retained = [row[1] for row in overview if row[2] in {'Retrieval', 'Reranking'} and row[7].startswith('Частично')]
    assert set(retained) == set(selected_names), retained

    queries = [json.loads(line) for line in (ROOT / 'evidence/rubq_queries.jsonl').read_text(encoding='utf-8').splitlines()]
    qrels = [json.loads(line) for line in (ROOT / 'evidence/rubq_qrels.jsonl').read_text(encoding='utf-8').splitlines()]
    query_ids = {row['_id'] for row in queries}
    counts = Counter(row['query-id'] for row in qrels)
    assert len(queries) == len(query_ids) == 1692
    assert len(qrels) == 2845 and set(counts) == query_ids
    assert {row['score'] for row in qrels} == {1}
    assert len({(row['query-id'], row['corpus-id']) for row in qrels}) == len(qrels)
    assert (min(counts.values()), max(counts.values())) == (1, 7)

    test = load('evidence/RuBQ_2.0_test.json')
    dev = load('evidence/RuBQ_2.0_dev.json')
    assert (len(dev), len(test)) == (580, 2330)
    reranking = []
    for row in test:
        paragraphs = row['paragraphs_uids']
        positive = set(paragraphs['with_answer'])
        related = set(paragraphs['all_related'])
        assert positive <= related, row['uid']
        if positive and len(related - positive) >= 9:
            reranking.append((len(related), len(positive)))
    assert len(reranking) == 1551
    assert sum(n for n, _ in reranking) == 37447
    assert sum(n for _, n in reranking) == 2602
    assert min(n for n, _ in reranking) == 10 and max(n for n, _ in reranking) == 29

    expected = {
        'MIRACLRetrievalHardNegatives.v2': ('ndcg_at_10', 0.76200, 1000, 219114, 2833),
        'MIRACLReranking': ('ndcg_at_10', 0.68174, 1247, 124700, 2436),
        'RuBQRetrieval': ('ndcg_at_10', 0.81004, 1692, 56826, 2845),
        'RuBQReranking': ('map_at_1000', 0.80881, 1551, 37447, 2602),
    }
    benchmarks = {}
    for name, (metric, score, nqueries, ndocuments, npositive) in expected.items():
        split = 'dev' if name.startswith('MIRACL') else 'test'
        stats = load(f'evidence/{name}.json')[split]
        if name.startswith('MIRACL'):
            stats = stats['hf_subset_descriptive_stats']['ru']
        assert (stats['num_queries'], stats['num_documents'], stats['relevant_docs_statistics']['num_relevant_docs']) == (nqueries, ndocuments, npositive)
        snapshot = load(f'evidence/{name}_scores.json')
        assert snapshot['task']['mainScore'] == metric
        row = next(row for row in snapshot['rows'] if row['model']['name'] == MODEL)
        subset = 'ru' if name.startswith('MIRACL') else 'default'
        assert row['subsetScores'][subset][split] == score
        benchmarks[name] = dict(split=split, subset=subset, metric=metric, model=MODEL,
                                score=score, queries=nqueries, document_records=ndocuments,
                                positive_pairs=npositive, mean_positive_per_query=npositive / nqueries)

    result = dict(snapshot_date=provenance['snapshot_date'], input_hashes='pass',
                  workbook_sheets={sheet.title: list(sheet.values) for sheet in workbook},
                  overview_rows=overview, selection=selected_names, benchmarks=benchmarks,
                  rubq_retrieval=dict(queries=len(queries), qrels=len(qrels), score_values=[1],
                                     min_positive=1, max_positive=7),
                  rubq_reranking=dict(queries=len(reranking), pairs=37447, positive=2602,
                                     negative=34845, min_candidates=10, max_candidates=29,
                                     mean_candidates=37447 / 1551),
                  scope='Historical evidence audit, not a fresh model evaluation or leaderboard update.')
    output = ROOT / 'output/analysis.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'23 tasks, 4 selected; snapshots and RuBQ counts verified: {output}')
    return result


if __name__ == '__main__':
    audit()
