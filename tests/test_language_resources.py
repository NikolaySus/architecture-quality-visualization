"""Small synthetic sources exercise the same import/build/query entry points as real data."""

import json
import io
import os
from pathlib import Path
import sqlite3
import zipfile

import pytest
from streamlit.testing.v1 import AppTest

for optional_package in ["conllu", "penman", "gdown", "pyvis", "filelock"]:
    pytest.importorskip(optional_package, reason="Install the language-resources dependency group")

from research.language_resources import pipeline, queries
from research.language_resources.storage import CATALOG, MODULE, Workspace, extract_archive, inventory, safe_target
from research.language_resources.warehouse import lexical_key, rebuild


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_sources(root):
    directories = {source: root / source for source in CATALOG}
    for directory in directories.values():
        directory.mkdir(parents=True)
    write(directories["ud"] / "ru_syntagrus-ud-test.conllu", """# newdoc id = document-1
# sent_id = test-1
# text = Они видят язык.
1-2	Онивидят	_	_	_	_	_	_	_	_
1	Они	они	PRON	_	Number=Plur	2	nsubj	2:nsubj	_
2	видят	видеть	VERB	_	Tense=Pres	0	root	0:root	_
3	язык	язык	NOUN	_	Case=Acc	2	obj	2:obj	_
3.1	язык	язык	NOUN	_	_	_	_	2:obj	_

""")
    with sqlite3.connect(directories["ruwordnet"] / "ruwordnet-2021.db") as connection:
        connection.executescript("""
          CREATE TABLE synset(id TEXT PRIMARY KEY,title TEXT,definition TEXT,part_of_speech TEXT);
          CREATE TABLE sense(id TEXT PRIMARY KEY,name TEXT,lemma TEXT,synset_id TEXT REFERENCES synset(id));
          CREATE TABLE hypernym_relation(hyponym_id TEXT REFERENCES synset(id),hypernym_id TEXT REFERENCES synset(id));
          INSERT INTO synset VALUES('organ','язык как орган','орган','N');
          INSERT INTO synset VALUES('language','язык как система','система','N');
          INSERT INTO sense VALUES('sense-1','язык','язык','organ');
          INSERT INTO sense VALUES('sense-2','язык','язык','language');
          INSERT INTO hypernym_relation VALUES('organ','language');
        """)
    write(directories["framebank"] / "framebank_dict_cx.txt",
          "ConstrIndex\tConstr\tConstrName\tKeyLexemes\n1\tS V\tязык действует\tязык\n")
    write(directories["framebank"] / "framebank_dict_cx_items.txt",
          "ConstrIndex\tPlace\tRole\tSemClass\n1\t1\tAgent\t\n")
    write(directories["framebank"] / "framebank_anno_ex_items.txt",
          "ConstrIndex\tExIndex\tItemExIndex\tRole\tWordDep\n1\t10\t101\tAgent\tязык\n")
    write(directories["framebank"] / "framebank_anno_ex_circ.txt",
          "ConstrIndex\tExIndex\tPlaceC\tPhrase\n1\t10\t1\t\n")
    write(directories["framebank"] / "exampleindex.csv", "ExIndex\tExample\n10\tЯзык действует.\n")
    write(directories["semontocor"] / "example.svg", """<svg xmlns="http://www.w3.org/2000/svg">
      <g class="graph"><text>Язык действует.</text>
        <g class="cluster" id="cluster1"><title>cluster_1</title><text>ЯЗЫК</text></g>
        <g class="node"><title>a</title><text>Language #1</text></g>
        <g class="node"><title>b</title><text>Act #2</text></g>
        <g class="edge" id="edge1"><title>b-&gt;a</title><text>hasAgent</text></g>
      </g></svg>""")
    english = {"id": "1", "locale": "en-US", "utt": "the boy sees himself", "annot_utt": "the boy sees himself",
               "raw_amr": "(s / see-01 :ARG0 (b / boy :consist-of (p / person)) :ARG1 b)"}
    russian = {"id": "1", "locale": "ru-RU", "utt": "мальчик видит себя", "annot_utt": "мальчик видит себя"}
    for name, row in [("massive_amr.jsonl", english), ("en-US.jsonl", english), ("ru-RU.jsonl", russian)]:
        write(directories["amr"] / name, json.dumps(row, ensure_ascii=False) + "\n")
    return directories


@pytest.fixture
def built(tmp_path):
    workspace = Workspace(tmp_path / "work")
    sources = make_sources(tmp_path / "inputs")
    for source, directory in sources.items():
        pipeline.import_local(workspace, source, directory, complete=True)
    before = {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG}
    generation = rebuild(workspace)
    return workspace, sources, before, generation


def test_all_adapters_and_provenance(built):
    workspace, _, before, generation = built
    assert all(source["available"] for source in generation["sources"].values())
    with queries.connect(workspace.database()) as connection:
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        assert connection.execute("SELECT count(*) FROM entity WHERE kind='synset'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM entity WHERE kind='sense'").fetchone()[0] == 2
        language = connection.execute("SELECT label,attributes FROM entity WHERE kind='synset' AND local_id='language'").fetchone()
        assert language[0] == "язык как система"
        assert json.loads(language[1])["raw"]["definition"] == "система"
        empty = connection.execute("SELECT attributes FROM entity WHERE local_id='test-1/3.1'").fetchone()
        assert empty and json.loads(empty[0])["raw"]["id"] == [3, ".", 1]
        assert connection.execute("SELECT count(*) FROM fact_relation WHERE predicate='ud-enhanced:obj'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM fact_relation WHERE predicate='semontocor:hasAgent'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM fact_relation WHERE predicate='amr:ARG1'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM fact_relation WHERE predicate='amr:consist-of'").fetchone()[0] == 2
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE predicate='amr:consist'").fetchone()
        shared = connection.execute("SELECT id FROM entity WHERE source IS NULL AND label='язык'").fetchall()
        assert len(shared) == 1
        assert connection.execute("SELECT count(DISTINCT source) FROM fact_relation WHERE object_id=?",
                                  (shared[0][0],)).fetchone()[0] == 4
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE rule='' OR file='' OR record='' LIMIT 1").fetchone()
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM entity")
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before
    assert lexical_key("  ЕЛЬ\t ЁЛКА ") == "ель ёлка"


def test_word_occurrences_use_smallest_fragments_and_slot_offsets(tmp_path):
    sources = make_sources(tmp_path / "inputs")
    write(sources["semontocor"] / "example.svg", """<svg xmlns="http://www.w3.org/2000/svg">
      <g class="graph"><text>Они видят язык.</text>
        <g class="cluster"><title>wide</title><text>[Видят] язык</text>
          <g class="cluster"><title>small</title><text>ЯЗЫК</text></g>
        </g>
      </g></svg>""")
    write(sources["semontocor"] / "repeat.svg", """<svg xmlns="http://www.w3.org/2000/svg">
      <g class="graph"><text>Язык язык.</text>
        <g class="cluster"><title>ambiguous</title><text>язык</text></g>
      </g></svg>""")
    annotation = '[item: «язык»] и [item: язык]'
    russian = {"id": "1", "utt": "«язык» и язык", "annot_utt": annotation}
    write(sources["amr"] / "ru-RU.jsonl", json.dumps(russian, ensure_ascii=False) + "\n")
    workspace = Workspace(tmp_path / "work")
    for source, directory in sources.items():
        pipeline.import_local(workspace, source, directory, complete=True)
    before = {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG}
    first = rebuild(workspace)
    with queries.connect(workspace.database()) as connection:
        parents = connection.execute("""
          SELECT w.label,p.kind,p.label,w.id,w.attributes,p.attributes
          FROM entity w JOIN fact_relation f ON f.object_id=w.id AND f.predicate='text:contains_word'
          JOIN entity p ON p.id=f.subject_id
          WHERE w.source='semontocor' AND w.local_id LIKE 'example.svg/word/%'
        """).fetchall()
        assert {(r[0], r[1], r[2]) for r in parents} == {
            ("Они", "sentence", "Они видят язык."),
            ("видят", "surface_fragment", "[Видят] язык"),
            ("язык", "surface_fragment", "ЯЗЫК")}
        assert len(parents) == 3
        stable_ids = {row[3] for row in parents}
        assert all(json.loads(row[4])["lemma_status"] == "ud_form" for row in parents)
        assert connection.execute("""
          SELECT count(*) FROM entity w JOIN fact_relation f ON f.object_id=w.id
          JOIN entity p ON p.id=f.subject_id
          WHERE w.local_id LIKE 'repeat.svg/word/%' AND f.predicate='text:contains_word' AND p.kind='sentence'
        """).fetchone()[0] == 2
        slots = connection.execute("""
          SELECT w.id,w.attributes,p.attributes FROM entity w
          JOIN fact_relation f ON f.object_id=w.id AND f.predicate='text:contains_word'
          JOIN entity p ON p.id=f.subject_id
          WHERE w.source='amr' AND w.label='язык'
          ORDER BY json_extract(w.attributes,'$.position')
        """).fetchall()
        assert len(slots) == 2 and slots[0][0] != slots[1][0]
        assert [json.loads(row[2])["raw"]["annotation_start"] for row in slots] == [0, annotation.rfind('[')]
        for word_id, attributes, _ in slots:
            span = json.loads(attributes)
            assert russian["utt"][span["start"]:span["end"]] == "язык"
            evidence = queries.entity_card(workspace.database(), word_id)["evidence"]
            assert {item["source"] for item in evidence} == {"amr", "ud"}
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    repeated = rebuild(workspace, force=True)
    assert repeated["counts"] == first["counts"]
    with queries.connect(workspace.database()) as connection:
        assert {row[0] for row in connection.execute(
            "SELECT id FROM entity WHERE source='semontocor' AND local_id LIKE 'example.svg/word/%'")} == stable_ids
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before


def test_ud_word_index_keeps_ambiguity_and_yo_distinction():
    from research.language_resources.text import WordIndex, word_matches
    index = WordIndex()
    index.observe("стали", "стать", "VERB", "ud.conllu", "1")
    index.observe("Стали", "сталь", "NOUN", "ud.conllu", "2")
    index.observe("стали", "стать", "VERB", "ud.conllu", "3")
    assert index.lookup("стали") is None
    index.observe("все", "весь", "DET", "ud.conllu", "4")
    index.observe("всё", "всё", "PRON", "ud.conllu", "5")
    assert index.lookup("ВСЕ")[0] == "весь"
    assert index.lookup("ВСЁ")[0] == "всё"
    assert index.lookup("неизвестно") is None
    assert [match.group() for match in word_matches("Все\u0308-таки, всё!")] == ["Все\u0308-таки", "всё"]


@pytest.mark.parametrize("typo_first", [True, False])
def test_ud_word_index_excludes_typos_regardless_of_order(typo_first):
    from research.language_resources.text import WordIndex
    index = WordIndex()
    observations = [("из", "typo", True), ("и", "clean", False)]
    if not typo_first:
        observations.reverse()
    for lemma, record, typo in observations:
        index.observe("И", lemma, "CCONJ", "ud.conllu", record, typo=typo)
    assert index.lookup("и") == ("и", "CCONJ", "ud.conllu", "clean")
    assert index.reason("И") == "unique_lemma"
    index.observe("опичатка", "опечатка", "NOUN", "ud.conllu", "3", typo=True)
    assert index.lookup("опичатка") is None
    assert index.reason("опичатка") == "typo_only"
    index.observe("стали", "стать", "VERB", "ud.conllu", "4")
    index.observe("стали", "сталь", "NOUN", "ud.conllu", "5")
    assert index.lookup("стали") is None
    assert index.reason("стали") == "ambiguous_form"
    assert index.reason("неизвестно") == "absent_form"
    assert index.summary() == {"clean_observations": 3, "excluded_typo_observations": 2,
                               "unique_forms": 1, "ambiguous_forms": 1, "typo_only_forms": 1}


def test_clean_lemmas_homonym_keys_and_multiword_components(tmp_path):
    sources = make_sources(tmp_path / "inputs")
    ud_file = sources["ud"] / "ru_syntagrus-ud-test.conllu"
    write(ud_file, ud_file.read_text(encoding="utf-8") + """# sent_id = lexical-rules
# text = И и рядом рядом опичатка
1	И	и	CCONJ	_	_	0	root	_	_
2	и	из	ADP	_	Typo=Yes	1	dep	_	_
3	рядом	рядом	ADV	_	_	1	dep	_	_
4	рядом	ряд	NOUN	_	_	1	dep	_	_
5	опичатка	опечатка	NOUN	_	Typo=Yes	1	dep	_	_

""")
    svg = sources["semontocor"] / "example.svg"
    write(svg, svg.read_text(encoding="utf-8").replace("Язык действует.", "И рядом опичатка неизвестно язык."))
    write(sources["framebank"] / "framebank_dict_cx.txt",
          "ConstrIndex\tConstr\tConstrName\tKeyLexemes\n"
          "1\tS V\tязык действует\tязык\n"
          "2\tхватать1\tхватать1\tхватать1\n"
          "3\tхватать2\tхватать2\tхватать2,хватить2\n"
          "4\tphrase\tphrase\tсеверо-западный язык,Abrev,напасть (сущ.)\n")
    phrase = "  СЕВЕРО-ЗАПАДНЫЙ\t ЯЗЫК ЯЗЫК  "
    with sqlite3.connect(sources["ruwordnet"] / "ruwordnet-2021.db") as connection:
        connection.execute("INSERT INTO sense VALUES('phrase','название',?,'language')", (phrase,))
    workspace = Workspace(tmp_path / "work")
    for source, directory in sources.items():
        pipeline.import_local(workspace, source, directory, complete=True)
    before = {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG}
    generation = rebuild(workspace)
    with queries.connect(workspace.database()) as connection:
        words = {row["label"]: json.loads(row["attributes"]) for row in connection.execute(
            "SELECT label,attributes FROM entity WHERE source='semontocor' AND kind='word_occurrence'")}
        assert {key: value["lemma_reason"] for key, value in words.items()} == {
            "И": "unique_lemma", "рядом": "ambiguous_form", "опичатка": "typo_only",
            "неизвестно": "absent_form", "язык": "unique_lemma"}
        edge = connection.execute("""
          SELECT f.* FROM fact_relation f JOIN entity e ON e.id=f.subject_id
          WHERE e.source='semontocor' AND e.label='И' AND f.predicate='lexical:lemma_match'
        """).fetchone()
        assert json.loads(edge["attributes"])["ud_record"] == "lexical-rules/token/1"
        assert edge["rule"] == "unambiguous-clean-ud-form-v2"
        # Typo filtering affects the lookup dictionary, while native annotations remain inspectable.
        native = connection.execute("SELECT attributes FROM entity WHERE local_id='lexical-rules/2'").fetchone()
        assert json.loads(native[0])["raw"]["feats"]["Typo"] == "Yes"
        assert connection.execute("""
          SELECT l.label FROM entity t JOIN fact_relation f ON f.subject_id=t.id
          JOIN entity l ON l.id=f.object_id
          WHERE t.local_id='lexical-rules/2' AND f.predicate='lexical:lemma_match'
        """).fetchone()[0] == "из"
        keys = connection.execute("""
          SELECT e.id,e.local_id,l.label,f.attributes FROM fact_relation f
          JOIN entity e ON e.id=f.subject_id JOIN entity l ON l.id=f.object_id
          WHERE e.source='framebank' AND e.local_id IN ('2','3') AND f.predicate='lexical:lemma_match'
        """).fetchall()
        assert len({row["id"] for row in keys}) == 2
        assert {(row["local_id"], row["label"], json.loads(row["attributes"])["homonym_index"])
                for row in keys} == {("2", "хватать", 1), ("3", "хватать", 2), ("3", "хватить", 2)}
        assert not connection.execute("SELECT 1 FROM entity WHERE source IS NULL AND label='хватать2'").fetchone()
        components = connection.execute("""
          SELECT f.*,l.label FROM fact_relation f JOIN entity e ON e.id=f.subject_id
          JOIN entity l ON l.id=f.object_id
          WHERE f.source='ruwordnet' AND e.label='северо-западный язык язык'
            AND f.predicate='lexical:has_component'
          ORDER BY json_extract(f.attributes,'$.position')
        """).fetchall()
        assert [row["label"] for row in components] == ["северо-западный", "язык", "язык"]
        for position, row in enumerate(components):
            attributes = json.loads(row["attributes"])
            assert attributes["position"] == position
            assert attributes["lemma"] == phrase
            assert phrase[attributes["start"]:attributes["end"]] == attributes["component"]
            assert row["rule"] == "published-lemma-components-v1"
            assert row["record"] == "sense:phrase"
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        stable_edges = {row["id"] for row in components}
    diagnostics = generation["diagnostics"]
    assert diagnostics["ud_word_index"]["excluded_typo_observations"] == 2
    framebank = diagnostics["sources"]["framebank"]
    assert framebank["counts"]["framebank_indexed_keys_linked"] == 3
    assert framebank["counts"]["framebank_keys_skipped"] == 2
    assert {item["key"] for item in framebank["skipped_keys"]} == {"Abrev", "напасть (сущ.)"}
    assert all(item["reason"] == "unsupported_key_format" and item["file"] and item["record"]
               for item in framebank["skipped_keys"])
    assert rebuild(workspace)["skipped"]
    repeated = rebuild(workspace, force=True)
    assert repeated["counts"] == generation["counts"]
    assert repeated["diagnostics"] == diagnostics
    with queries.connect(workspace.database()) as connection:
        assert all(connection.execute("SELECT 1 FROM fact_relation WHERE id=?", (edge,)).fetchone()
                   for edge in stable_edges)
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before


@pytest.mark.parametrize("text,expected", [
    ("слово (контекст)", [(7, 15)]),
    ("а (б (в))", [(3, 8), (6, 7)]),
    ("а (б) (б)", [(3, 4), (7, 8)]),
    ("а (б", []),
    ("а ) б", []),
])
def test_balanced_parenthetical_spans(text, expected):
    from research.language_resources.text import parenthetical_spans
    assert parenthetical_spans(text) == expected


def test_ruwordnet_text_mentions_keep_fields_context_and_native_senses(tmp_path, monkeypatch):
    sources = make_sources(tmp_path / "inputs")
    ud_file = sources["ud"] / "ru_syntagrus-ud-test.conllu"
    write(ud_file, ud_file.read_text(encoding="utf-8") + """# sent_id = dictionary-mentions
1	метелка	метелка	NOUN	_	_	0	root	_	_
2	соцветие	соцветие	NOUN	_	_	1	dep	_	_
3	сплав	сплав	NOUN	_	_	1	dep	_	_
4	ртути	ртуть	NOUN	_	_	1	dep	_	_
5	амальгама	амальгама	NOUN	_	_	1	dep	_	_

""")
    title = "МЕТЕЛКА (  СОЦВЕТИЕ (ЯЗЫК)  )"
    definition = "Язык (язык) (язык) (((ЯЗЫК)))"
    with sqlite3.connect(sources["ruwordnet"] / "ruwordnet-2021.db") as connection:
        connection.executemany("INSERT INTO synset VALUES(?,?,?,?)", [
            ("botanical", title, definition, "Adj"),
            ("chemical", "АМАЛЬГАМА (СПЛАВ РТУТИ)", "", "Adj"),
            ("broken", "Язык (соцветие", None, "N"), ("empty", "  ", "", "N")])
        connection.executemany("INSERT INTO sense VALUES(?,?,?,?)", [
            ("botanical-sense", "метелочный", "метелочный", "botanical"),
            ("chemical-sense", "амальгамный", "амальгамный", "chemical"),
            ("other-sense", "амальгама", "амальгама", "language")])
    workspace = Workspace(tmp_path / "work")
    for source, directory in sources.items():
        pipeline.import_local(workspace, source, directory, complete=True)
    before = {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG}
    generation = rebuild(workspace)
    with queries.connect(workspace.database()) as connection:
        words = connection.execute("""
          SELECT w.id,w.label,w.attributes,p.id AS parent_id,p.label AS parent_label,p.attributes AS parent_attributes
          FROM entity w JOIN fact_relation f ON f.object_id=w.id AND f.predicate='text:contains_word'
          JOIN entity p ON p.id=f.subject_id
          WHERE w.source='ruwordnet' AND w.local_id LIKE 'synset:botanical/title/word/%'
          ORDER BY json_extract(w.attributes,'$.position')
        """).fetchall()
        assert [row["label"] for row in words] == ["МЕТЕЛКА", "СОЦВЕТИЕ", "ЯЗЫК"]
        assert [json.loads(row["parent_attributes"])["role"] for row in words] == [
            "source_field", "parenthetical", "parenthetical"]
        assert words[1]["parent_label"] == "  СОЦВЕТИЕ (ЯЗЫК)  "
        assert words[2]["parent_label"] == "ЯЗЫК"
        assert connection.execute("""
          SELECT 1 FROM fact_relation WHERE subject_id=? AND object_id=? AND predicate='text:contains_fragment'
        """, (words[1]["parent_id"], words[2]["parent_id"])).fetchone()
        for row in words:
            attrs = json.loads(row["attributes"])
            assert "sentence_id" not in attrs
            assert attrs["source_field"] == "title" and attrs["source_record"] == "synset:botanical"
            assert title[attrs["start"]:attrs["end"]] == row["label"]
            assert attrs["lemma_reason"] == "unique_lemma"
            evidence = queries.entity_card(workspace.database(), row["id"])["evidence"]
            assert {item["source"] for item in evidence} == {"ruwordnet", "ud"}
        repeated = connection.execute("""
          SELECT w.id,p.id,p.label FROM entity w JOIN fact_relation f ON f.object_id=w.id
          JOIN entity p ON p.id=f.subject_id
          WHERE w.local_id LIKE 'synset:botanical/definition/word/%' AND f.predicate='text:contains_word'
          ORDER BY json_extract(w.attributes,'$.position')
        """).fetchall()
        assert len(repeated) == 4 and len({row[0] for row in repeated}) == 4
        assert len({row[1] for row in repeated}) == 4
        assert repeated[-1][2] == "ЯЗЫК"
        assert not connection.execute("SELECT 1 FROM entity WHERE local_id LIKE 'synset:empty/%'").fetchone()
        assert not connection.execute("SELECT 1 FROM entity WHERE local_id LIKE 'synset:broken/title/parenthetical/%'").fetchone()
        assert connection.execute("""
          SELECT l.label FROM entity w JOIN fact_relation f ON f.subject_id=w.id
          JOIN entity l ON l.id=f.object_id
          WHERE w.local_id LIKE 'synset:chemical/title/word/%' AND w.label='РТУТИ'
            AND f.predicate='lexical:lemma_match'
        """).fetchone()[0] == "ртуть"
        assert connection.execute("""
          SELECT s.local_id FROM entity e JOIN fact_relation f ON f.subject_id=e.id
          JOIN entity s ON s.id=f.object_id
          WHERE e.local_id='other-sense' AND f.predicate='ruwordnet:sense_of'
        """).fetchone()[0] == "language"
        assert not connection.execute("""
          SELECT 1 FROM fact_relation f JOIN entity e ON e.id=f.subject_id
          WHERE e.kind='synset' AND f.predicate='lexical:lemma_match'
        """).fetchone()
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        stable = {row[0] for row in connection.execute(
            "SELECT id FROM entity WHERE source='ruwordnet' AND kind IN ('surface_fragment','word_occurrence')")}
    counts = generation["diagnostics"]["sources"]["ruwordnet"]["counts"]
    assert counts["ruwordnet_title_fields"] == 5 and counts["ruwordnet_definition_fields"] == 3
    assert counts["ruwordnet_parenthetical_fragments"] == 8
    assert counts["ruwordnet_unmatched_parentheses"] == 1
    assert rebuild(workspace)["skipped"]
    repeated_generation = rebuild(workspace, force=True)
    assert repeated_generation["counts"] == generation["counts"]
    with queries.connect(workspace.database()) as connection:
        assert {row[0] for row in connection.execute(
            "SELECT id FROM entity WHERE source='ruwordnet' AND kind IN ('surface_fragment','word_occurrence')")} == stable
    monkeypatch.setenv("LANGUAGE_RESOURCES_HOME", str(workspace.root))
    app = AppTest.from_file(str(MODULE / "app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Карточка объекта").run()
    app.text_input[0].set_value(words[2]["id"]).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Граф").run()
    assert not app.exception
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before


def test_rebuild_skip_force_update_and_failed_publish(built):
    workspace, sources, _, first = built
    assert rebuild(workspace)["skipped"]
    forced = rebuild(workspace, force=True)
    assert forced["id"] != first["id"]
    assert forced["counts"] == first["counts"]
    file = sources["ud"] / "ru_syntagrus-ud-test.conllu"
    write(file, "# sent_id = replacement\n1\tдерево\tдерево\tNOUN\t_\t_\t0\troot\t_\t_\n\n")
    pipeline.import_local(workspace, "ud", sources["ud"])
    assert pipeline.status(workspace)["stale"]
    second = rebuild(workspace)
    assert second["signature"] != first["signature"]
    with queries.connect(workspace.database()) as connection:
        assert not connection.execute("SELECT 1 FROM entity WHERE local_id='test-1/3.1'").fetchone()
    write(file, "# sent_id = broken\n1\tX\tx\tNOUN\t_\t_\t9\tobj\t_\t_\n\n")
    pipeline.import_local(workspace, "ud", sources["ud"])
    with pytest.raises(KeyError):
        rebuild(workspace)
    assert workspace.generation()["id"] == second["id"]
    assert workspace.database().exists()
    assert pipeline.status(workspace)["last_build"]["status"] == "error"


def test_corrupt_snapshot_and_download_failure_preserve_state(built, monkeypatch):
    workspace, _, _, generation = built
    def fail(*args):
        raise OSError("interrupted transfer")
    monkeypatch.setattr(pipeline, "download_source", fail)
    active = workspace.active()
    outcome = pipeline.download(workspace, ["ud"])
    assert outcome["ud"]["status"] == "error"
    assert workspace.active() == active
    assert workspace.generation()["id"] == generation["id"]
    snapshot_file = next((workspace.snapshot("ud")[0] / "payload").rglob("*.conllu"))
    snapshot_file.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="changed on disk"):
        rebuild(workspace)
    assert workspace.generation()["id"] == generation["id"]


def test_archive_traversal_and_manual_archive_import(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("../outside.txt", "x")
    with pytest.raises(ValueError, match="Unsafe archive"):
        extract_archive(bad, tmp_path / "extracted")
    assert not (tmp_path / "outside.txt").exists()
    sources = make_sources(tmp_path / "inputs")
    good = tmp_path / "ud.zip"
    with zipfile.ZipFile(good, "w") as archive:
        for file in sources["ud"].iterdir():
            archive.write(file, "export/" + file.name)
    workspace = Workspace(tmp_path / "work")
    pipeline.import_local(workspace, "ud", good)
    assert rebuild(workspace)["counts"]["entity"] > 0


def test_search_card_bounds_and_gui(built, monkeypatch):
    workspace, _, before, _ = built
    rows, more = queries.search(workspace.database(), "язык", page_size=1)
    assert rows and more
    assert queries.entity_card(workspace.database(), rows[0]["id"])["evidence"]
    assert queries.search(workspace.database(), '" OR *', source="shared")[0] == []
    graph = queries.neighborhood(workspace.database(), rows[0]["id"], depth=3, limit=2)
    assert len(graph["nodes"]) <= 2 and graph["truncated"]
    assert queries.neighborhood(workspace.database(), "missing")["nodes"] == []
    monkeypatch.setenv("LANGUAGE_RESOURCES_HOME", str(workspace.root))
    app = AppTest.from_file(str(MODULE / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(expander.label == "Диагностика обработки" for expander in app.expander)
    app.sidebar.radio[0].set_value("Поиск").run()
    app.text_input[0].set_value("язык").run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.sidebar.radio[0].value == "Граф"
    assert [widget.value for widget in app.number_input] == [200, 5000]
    app.number_input[0].set_value(1)
    app.number_input[1].set_value(1).run()
    assert not app.exception
    assert any("Узлов 1 ·" in caption.value for caption in app.caption)
    assert "Предел узлов равен 1, предел связей — 1" in app.info[0].value
    app.number_input[0].set_value(300)
    app.number_input[1].set_value(6000).run()
    assert not app.exception
    assert [widget.value for widget in app.number_input] == [300, 6000]
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before


def test_configurable_neighborhood_limits(tmp_path):
    database = tmp_path / "graph.sqlite"
    connection = sqlite3.connect(database)
    with connection:
        connection.executescript("""
          CREATE TABLE entity (id TEXT PRIMARY KEY, label TEXT, kind TEXT, source TEXT);
          CREATE TABLE fact_relation (id TEXT PRIMARY KEY, subject_id TEXT, object_id TEXT);
        """)
        connection.executemany("INSERT INTO entity VALUES (?, ?, 'node', 'test')",
                               [("root", "Root"), *[(f"node-{i}", f"Node {i}") for i in range(1300)]])
        connection.executemany("INSERT INTO fact_relation VALUES (?, 'root', ?)",
                               [(f"edge-{i}", f"node-{i % 1300}") for i in range(5200)])
    connection.close()

    graph = queries.neighborhood(database, "root", limit=2000, edge_limit=6000)
    assert len(graph["nodes"]) == 1301 and len(graph["edges"]) == 5200
    assert not graph["truncated"]
    exact = queries.neighborhood(database, "root", limit=1301, edge_limit=5200)
    assert not exact["truncated"]
    edge_limited = queries.neighborhood(database, "root", limit=2000)
    assert len(edge_limited["edges"]) == 5000 and edge_limited["truncated"]
    small = queries.neighborhood(database, "root", limit=3, edge_limit=1)
    assert len(small["nodes"]) == 2 and len(small["edges"]) == 1 and small["truncated"]
    node_limited = queries.neighborhood(database, "root", limit=2, edge_limit=6000)
    assert len(node_limited["nodes"]) == 2 and len(node_limited["edges"]) == 4
    assert node_limited["truncated"]
    for arguments in [{"limit": 0}, {"edge_limit": 0}]:
        with pytest.raises(ValueError, match="positive"):
            queries.neighborhood(database, "root", **arguments)


def test_empty_and_partial_gui(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "work")
    monkeypatch.setenv("LANGUAGE_RESOURCES_HOME", str(workspace.root))
    app = AppTest.from_file(str(MODULE / "app.py")).run()
    assert not app.exception
    for section in ["Поиск", "Карточка объекта", "Граф"]:
        app.sidebar.radio[0].set_value(section).run()
        assert not app.exception
    sources = make_sources(tmp_path / "inputs")
    pipeline.import_local(workspace, "semontocor", sources["semontocor"])
    generation = rebuild(workspace)
    assert sum(source["available"] for source in generation["sources"].values()) == 1
    assert not generation["sources"]["semontocor"]["complete"]
    with queries.connect(workspace.database()) as connection:
        reasons = {json.loads(row[0])["lemma_reason"] for row in connection.execute(
            "SELECT attributes FROM entity WHERE kind='word_occurrence'")}
        assert reasons == {"ud_unavailable"}


def test_localization_rules():
    from research.language_resources.adapters import localize_amr
    english = "weather in [place : London]"
    russian = "погода в [place : Москва]"
    localized, issues = localize_amr('(c / city :name (n / name :op1 "London"))', english, russian)
    assert not issues and '"Москва"' in localized
    assert localize_amr("(x / x)", english, "[definition_word : слово]")[0] is None
    assert localize_amr("(x / x)", english, "без слотов")[0] is None


def test_buffered_download_and_rejected_short_response(tmp_path, monkeypatch):
    from research.language_resources import downloads
    class Response(io.BytesIO):
        def __init__(self, expected):
            super().__init__(b"small source payload")
            self.headers = {"Content-Length": str(expected), "ETag": "fixture"}
    monkeypatch.setattr(downloads, "request", lambda *args: Response(20))
    path = tmp_path / "source"
    assert downloads.fetch_file("https://example.invalid/source", path)["etag"] == "fixture"
    assert path.read_bytes() == b"small source payload"
    monkeypatch.setattr(downloads, "request", lambda *args: Response(100))
    monkeypatch.setattr(downloads.time, "sleep", lambda delay: None)
    with pytest.raises(OSError, match="Incomplete"):
        downloads.fetch_file("https://example.invalid/source", path)


@pytest.mark.skipif(os.name != "nt", reason="Windows extended path spelling")
def test_windows_extended_paths_keep_containment_check(tmp_path, monkeypatch):
    original = Path.resolve
    def extended_child(path, *args, **kwargs):
        resolved = original(path, *args, **kwargs)
        return Path("\\\\?\\" + str(resolved)) if path.name == "child.svg" else resolved
    monkeypatch.setattr(Path, "resolve", extended_child)
    assert safe_target(tmp_path, "child.svg") == tmp_path / "child.svg"
    with pytest.raises(ValueError, match="Unsafe"):
        safe_target(tmp_path, "../child.svg")


def test_sync_and_framebank_component_import(tmp_path, monkeypatch):
    from research.language_resources.__main__ import main
    workspace = Workspace(tmp_path / "work")
    sources = make_sources(tmp_path / "inputs")
    examples = sources["framebank"] / "exampleindex.csv"
    example_text = examples.read_text(encoding="utf-8")
    examples.unlink()
    pipeline.import_local(workspace, "framebank", sources["framebank"], complete=True)
    assert not pipeline.status(workspace)["sources"][2]["complete"]
    replacement = tmp_path / "manual" / "exampleindex.csv"
    write(replacement, example_text)
    pipeline.import_local(workspace, "framebank", replacement, complete=True)
    assert pipeline.status(workspace)["sources"][2]["complete"]
    import shutil
    def acquire(source, stage, previous):
        shutil.copytree(sources[source], stage / "payload", dirs_exist_ok=True)
        return {"versions": {"fixture": "1"}, "components": [{"name": "graphs", "status": "available"}],
                "complete": True, "issues": []}
    monkeypatch.setattr(pipeline, "download_source", acquire)
    result = pipeline.sync(workspace, ["amr"])
    assert result["downloads"]["amr"]["status"] == "ok"
    assert not pipeline.status(workspace)["stale"]
    assert main(["--home", str(workspace.root), "status"]) == 0
    assert main(["--home", str(workspace.root), "rebuild"]) == 0


def test_writer_lock_and_readers_on_previous_generation(built):
    from filelock import Timeout
    workspace, _, _, generation = built
    old_database = workspace.database()
    with workspace.lock():
        with pytest.raises(Timeout):
            rebuild(workspace)
        with pytest.raises(Timeout):
            pipeline.download(workspace, ["ud"])
        assert queries.search(old_database, "язык")[0]
    with queries.connect(old_database) as reader:
        replacement = rebuild(workspace, force=True)
        assert replacement["id"] != generation["id"]
        assert reader.execute("SELECT count(*) FROM entity").fetchone()[0] == generation["counts"]["entity"]


def test_graph_html_has_offline_assets_and_escaped_labels():
    from bs4 import BeautifulSoup
    from research.language_resources.app import graph_html
    html = graph_html({"nodes": [{"id": "a", "label": "</script><script>unsafe()</script>",
                                  "source": "ud", "kind": "token"}], "edges": []})
    document = BeautifulSoup(html, "html.parser")
    assert not document.find_all("script", src=True)
    assert not document.find_all("link", href=True)
    assert "new vis.Network" in html
    assert "</script><script>unsafe()" not in html
    copy_script = document.find_all("script")[-1].string
    assert 'network.on("click"' in copy_script
    assert "event.nodes.length !== 1" in copy_script
    assert "navigator.clipboard.writeText(objectId)" in copy_script
    assert document.find(id="graph-copy-status")["role"] == "status"


def test_manual_completeness_confirmation_preserves_source_bytes(tmp_path):
    sources = make_sources(tmp_path / "inputs")
    workspace = Workspace(tmp_path / "work")
    first = pipeline.import_local(workspace, "semontocor", sources["semontocor"])
    before = inventory(workspace.snapshot("semontocor")[0] / "payload")
    confirmed = pipeline.import_local(workspace, "semontocor", sources["semontocor"], complete=True)
    assert confirmed["complete"] and confirmed["snapshot"] != first["snapshot"]
    assert inventory(workspace.snapshot("semontocor")[0] / "payload") == before
    repeated = pipeline.import_local(workspace, "semontocor", sources["semontocor"], complete=True)
    assert repeated["snapshot"] == confirmed["snapshot"]


@pytest.mark.parametrize("failed_file", ["build.json", "current.json"])
def test_publication_failure_preserves_active_database(built, monkeypatch, failed_file):
    from research.language_resources import warehouse
    workspace, _, _, generation = built
    original = warehouse.atomic_json
    def fail_status(path, value):
        if path.name == failed_file and value.get("status") != "error":
            raise OSError("publication write failed")
        return original(path, value)
    monkeypatch.setattr(warehouse, "atomic_json", fail_status)
    with pytest.raises(OSError, match="publication write failed"):
        rebuild(workspace, force=True)
    assert workspace.generation()["id"] == generation["id"]
    assert workspace.database().exists()
    assert queries.search(workspace.database(), "язык")[0]
