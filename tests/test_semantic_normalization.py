"""Semantic replacements preserve original assertions, context and repeatability."""

import json

import pytest

pytest.importorskip("conllu")
pytest.importorskip("penman")

from test_language_resources import make_sources, write
from research.language_resources import normalization, pipeline, queries
from research.language_resources.storage import CATALOG, Workspace, inventory
from research.language_resources.warehouse import input_signature, rebuild


@pytest.mark.parametrize("label,operator,roles", [
    (" АГЕНС ", "role", ["Agent"]),
    ("Agent", "role", ["Agent"]),
    ("время", "role", ["Time"]),
    ("агенс / каузатор", "any_of", ["Agent", "Causer"]),
    ("агенс - субъект ментального состояния", "all_of", ["Agent", "Cognizer"]),
])
def test_role_labels_and_logical_expressions(label, operator, roles):
    parsed = normalization.parse_role(label, normalization.load_rules())
    assert parsed == {"status": "mapped", "operator": operator, "roles": roles}


@pytest.mark.parametrize("label,status", [
    ("NULL", "missing"), ("- ", "missing"), ("неизвестная роль", "unknown_label"),
    ("агенс / каузатор - инструмент", "mixed_expression"),
])
def test_role_labels_requiring_review(label, status):
    assert normalization.parse_role(label, normalization.load_rules()) == {"status": status}


def semantic_sources(root):
    sources = make_sources(root)
    write(sources["semontocor"] / "example.svg", """<svg xmlns="http://www.w3.org/2000/svg">
      <g class="graph"><text>Они видят язык.</text>
        <g class="node"><title>event</title><text>Seeing #1</text></g>
        <g class="node"><title>agent</title><text>Human #2</text></g>
        <g class="node"><title>place</title><text>City #3</text></g>
        <g class="edge" id="a"><title>event-&gt;agent</title><text>hasAgent</text></g>
        <g class="edge" id="b"><title>agent-&gt;event</title><text>isAgentOf</text></g>
        <g class="edge" id="c"><title>event-&gt;place</title><text>hasLocation</text></g>
        <g class="edge" id="d"><title>place-&gt;event</title><text>isLocationOf</text></g>
        <g class="edge" id="e"><title>event-&gt;place</title><text>hasObject</text></g>
        <g class="edge" id="f"><title>event-&gt;place</title><text>from</text></g>
      </g></svg>""")
    roles = ["агенс", "АГЕНС ", "агенс / каузатор", "агенс - субъект ментального состояния",
             "NULL", "тема", "время", "неизвестная роль", "агенс / каузатор - инструмент"]
    write(sources["framebank"] / "framebank_dict_cx_items.txt",
          "ConstrIndex\tPlace\tRole\tSemClass\n" +
          "".join(f"1\t{position}\t{role}\t\n" for position, role in enumerate(roles, 1)))
    write(sources["framebank"] / "framebank_anno_ex_items.txt",
          "ConstrIndex\tExIndex\tItemExIndex\tRole\tWordDep\n1\t10\t101\tместо\tязык\n")
    path = sources["amr"] / "massive_amr.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["raw_amr"] = "(s / see-01 :ARG0 (b / boy) :ARG1 (u / amr-unknown) :location (c / city))"
    write(path, json.dumps(row, ensure_ascii=False) + "\n")
    return sources


@pytest.mark.parametrize("projection", ["role_assignment_and_slot_edges", "role_assignment_only"])
def test_semantic_replacements_and_provenance(tmp_path, monkeypatch, projection):
    sources = semantic_sources(tmp_path / "inputs")
    workspace = Workspace(tmp_path / "work")
    for source, directory in sources.items():
        pipeline.import_local(workspace, source, directory, complete=True)
    before = {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG}
    rules = normalization.load_rules()
    rules["framebank_projection"] = projection
    monkeypatch.setattr(normalization, "load_rules", lambda: rules)
    first = rebuild(workspace)
    with queries.connect(workspace.database()) as connection:
        semantic = connection.execute("""
          SELECT f.*,s.label AS subject_label,o.label AS object_label FROM fact_relation f
          JOIN entity s ON s.id=f.subject_id JOIN entity o ON o.id=f.object_id
          WHERE f.source='semontocor' AND f.predicate='core:agent' ORDER BY f.id
        """).fetchall()
        assert len(semantic) == 2
        assert {(x["subject_label"], x["object_label"]) for x in semantic} == {("Seeing #1", "Human #2")}
        anchors = {json.loads(x["attributes"])["normalization"]["communicative_anchor"] for x in semantic}
        assert len(anchors) == 2
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE predicate='semontocor:isAgentOf'").fetchone()
        assert connection.execute("SELECT count(*) FROM original_fact_relation WHERE predicate='semontocor:isAgentOf'").fetchone()[0] == 1
        assert connection.execute("SELECT 1 FROM fact_relation WHERE predicate='amr:ARG0'").fetchone()
        assert connection.execute("SELECT 1 FROM fact_relation WHERE predicate='semontocor:from'").fetchone()
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE source='semontocor' AND predicate='core:patient'").fetchone()
        assert connection.execute("SELECT 1 FROM fact_relation WHERE predicate='soc:object'").fetchone()
        for edge in connection.execute("SELECT attributes FROM fact_relation WHERE source='amr' AND predicate='core:location'"):
            attributes = json.loads(edge[0])["normalization"]
            assert attributes["context_kind"] == "question" and attributes["question_variables"]
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE predicate='framebank:Role'").fetchone()
        assert connection.execute("SELECT count(*) FROM original_fact_relation WHERE predicate='framebank:Role'").fetchone()[0] == 10
        assert connection.execute("SELECT count(*) FROM fact_relation WHERE predicate='core:unresolved_role'").fetchone()[0] == 3
        role_assignments = connection.execute("SELECT * FROM fact_relation WHERE predicate='core:semantic_role'").fetchall()
        assert len(role_assignments) == 7
        alternatives = [row for row in role_assignments
                        if json.loads(row["attributes"])["normalization"]["operator"] == "any_of"]
        assert len(alternatives) == 1
        alternative_slot = alternatives[0]["subject_id"]
        assert not connection.execute("SELECT 1 FROM fact_relation WHERE predicate='core:agent' AND object_id=?", (alternative_slot,)).fetchone()
        if projection == "role_assignment_and_slot_edges":
            assert connection.execute("SELECT 1 FROM fact_relation WHERE predicate='core:role_choice' AND object_id=?", (alternative_slot,)).fetchone()
            example = connection.execute("""
              SELECT e.kind,f.id FROM fact_relation f JOIN entity e ON e.id=f.subject_id
              WHERE f.source='framebank' AND f.predicate='core:location'
            """).fetchone()
            assert example["kind"] == "example"
            assert connection.execute("SELECT count(*) FROM relation_origin WHERE relation_id=?", (example["id"],)).fetchone()[0] == 2
            assert connection.execute("SELECT 1 FROM fact_relation WHERE predicate='role:framebank_theme'").fetchone()
        else:
            assert not connection.execute("SELECT 1 FROM fact_relation WHERE source='framebank' AND predicate='core:agent'").fetchone()
        card = queries.entity_card(workspace.database(), semantic[0]["subject_id"])
        assert card["relation_origins"]
        assert any(row["predicate"] in {"semontocor:hasAgent", "semontocor:isAgentOf"}
                   for row in card["relation_origins"])
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        assert connection.execute("SELECT count(*) FROM original_fact_relation").fetchone()[0] == first["diagnostics"]["semantic_normalization"]["before_relations"]
    second = rebuild(workspace, force=True)
    assert first["fingerprints"] == second["fingerprints"]
    assert first["id"] != second["id"]
    assert rebuild(workspace)["skipped"]
    assert {source: inventory(workspace.snapshot(source)[0] / "payload") for source in CATALOG} == before


def test_mapping_resources_and_environment_are_part_of_signature(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "work")
    import research.language_resources.warehouse as warehouse
    original = warehouse.digest_file
    first, inputs = input_signature(workspace)
    assert "semantic_normalization.json" in inputs["implementation"]
    assert "normalization.py" in inputs["implementation"]
    assert "uv.lock" in inputs["environment"]
    monkeypatch.setattr(warehouse, "digest_file", lambda path: "changed" if path.name == "semantic_normalization.json" else original(path))
    second, _ = input_signature(workspace)
    assert first != second


def test_role_hierarchy_cycles_fail_before_build(tmp_path):
    value = json.loads(normalization.RULES_FILE.read_text(encoding="utf-8"))
    value["role_parents"] = {"Agent": "Location", "Location": "Agent"}
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Cycle"):
        normalization.load_rules(path)


def test_failed_normalization_keeps_published_generation(tmp_path, monkeypatch):
    sources = semantic_sources(tmp_path / "inputs")
    workspace = Workspace(tmp_path / "work")
    pipeline.import_local(workspace, "semontocor", sources["semontocor"], complete=True)
    first = rebuild(workspace)
    normalize = normalization.normalize

    def fail_after_normalization(connection):
        normalize(connection)
        raise ValueError("injected failure after semantic normalization")

    monkeypatch.setattr(normalization, "normalize", fail_after_normalization)
    with pytest.raises(ValueError, match="injected failure"):
        rebuild(workspace, force=True)
    assert workspace.generation() == first
    assert workspace.database().exists()
    assert len(list((workspace.root / "warehouse").glob("*.sqlite"))) == 1
    assert pipeline.status(workspace)["last_build"]["status"] == "error"


def test_input_changes_during_build_prevent_publication(tmp_path, monkeypatch):
    import research.language_resources.warehouse as warehouse

    sources = semantic_sources(tmp_path / "inputs")
    workspace = Workspace(tmp_path / "work")
    pipeline.import_local(workspace, "semontocor", sources["semontocor"], complete=True)
    first = rebuild(workspace)
    signature, inputs = input_signature(workspace)
    calls = []

    def changed_signature(*args, **kwargs):
        calls.append(True)
        return (signature if len(calls) == 1 else "changed", inputs)

    monkeypatch.setattr(warehouse, "input_signature", changed_signature)
    with pytest.raises(ValueError, match="Build inputs changed during ETL"):
        rebuild(workspace, force=True)
    assert workspace.generation() == first
    assert len(list((workspace.root / "warehouse").glob("*.sqlite"))) == 1
