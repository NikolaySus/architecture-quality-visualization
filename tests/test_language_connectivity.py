"""Known weak components exercise streaming analysis and source membership."""

from contextlib import contextmanager
import sqlite3

import pytest

pytest.importorskip("filelock", reason="Install the language-resources dependency group")

from research.language_resources.connectivity import components
from research.language_resources import connectivity
from research.language_resources.storage import Workspace, atomic_json, digest_file


def make_graph(tmp_path, empty=False):
    workspace = Workspace(tmp_path / "work")
    database = workspace.root / "warehouse" / "fixture.sqlite"
    database.parent.mkdir(parents=True)
    connection = sqlite3.connect(database)
    with connection:
        connection.executescript("""
          CREATE TABLE entity(id TEXT PRIMARY KEY,source TEXT,kind TEXT,label TEXT,attributes TEXT DEFAULT '{}');
          CREATE TABLE fact_relation(subject_id TEXT,object_id TEXT,attributes TEXT DEFAULT '{}');
          CREATE TABLE entity_evidence(entity_id TEXT,source TEXT,file TEXT,record TEXT,rule TEXT);
        """)
        if not empty:
            connection.executemany("INSERT INTO entity(id,source,kind,label) VALUES(?,?,?,?)", [
                ("a", "ud", "token", "A"), ("b", None, "lexeme", "B"),
                ("c", "semontocor", "semantic_node", "C"), ("d", "amr", "sentence", "D"),
                ("e", "semontocor", "word_occurrence", "E"), ("f", "amr", "literal", "F"),
                ("g", "ruwordnet", "synset", "G")])
            connection.executemany("INSERT INTO fact_relation(subject_id,object_id) VALUES(?,?)", [
                ("a", "b"), ("c", "e"), ("e", "b"), ("d", "b"), ("f", "f"), ("a", "b")])
    connection.close()
    atomic_json(workspace.root / "current.json", {
        "id": "fixture", "database": database.name, "signature": "fixture",
        "inputs": {"snapshots": {}}})
    return workspace


def test_weak_components_membership_and_read_only_database(tmp_path):
    workspace = make_graph(tmp_path)
    before = digest_file(workspace.database())
    report = components(workspace)
    assert report["components"] == 3 and report["singleton_components"] == 2
    assert report["objects"] == 7 and report["edges"] == 6
    assert report["largest_size"] == 5
    assert [item["size"] for item in report["top_components"]] == [5, 1, 1]
    assert report["by_source"]["semontocor"]["percent"] == 100
    assert report["by_source"]["amr"]["total"] == 2
    assert report["by_source"]["amr"]["in_largest"] == 1
    assert report["by_source"]["amr"]["percent"] == 50
    assert report["by_source"]["amr"]["by_kind"]["literal"]["in_largest"] == 0
    assert report["by_source"]["shared"]["in_largest"] == 1
    assert digest_file(workspace.database()) == before
    assert (workspace.root / "analysis" / "connectivity-fixture.json").exists()


def test_empty_generation_and_missing_generation(tmp_path):
    workspace = make_graph(tmp_path, empty=True)
    report = components(workspace)
    assert report["components"] == 0 and report["largest_size"] == 0
    assert report["top_components"] == []
    assert report["by_source"]["amr"]["percent"] is None
    with pytest.raises(ValueError, match="Build a warehouse"):
        components(Workspace(tmp_path / "missing"))


def test_dangling_edges_are_reported(tmp_path):
    workspace = make_graph(tmp_path)
    with sqlite3.connect(workspace.database()) as connection:
        connection.execute("INSERT INTO fact_relation(subject_id,object_id) VALUES('a','missing')")
    with pytest.raises(ValueError, match="Dangling"):
        components(workspace)


def test_details_include_every_object_outside_the_largest_component(tmp_path, monkeypatch):
    workspace = make_graph(tmp_path)
    with sqlite3.connect(workspace.database()) as connection:
        connection.execute("INSERT INTO fact_relation(subject_id,object_id) VALUES('f','g')")
        connection.execute("INSERT INTO entity_evidence(entity_id,source,file) VALUES('f','amr','fixture')")
    original_connect = connectivity.connect

    @contextmanager
    def limited_connect(database):
        with original_connect(database) as connection:
            connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 1)
            yield connection

    monkeypatch.setattr(connectivity, "connect", limited_connect)
    report = components(workspace, details=True)
    others = report["other_components"]
    assert len(others) == report["components"] - 1
    assert sum(item["size"] for item in others) == report["objects"] - report["largest_size"]
    assert {node["id"] for item in others for node in item["nodes"]} == {"f", "g"}
    assert sum(len(item["edges"]) for item in others) == 2
    assert others[0]["evidence"][0]["file"] == "fixture"
    assert (workspace.root / "analysis" / "connectivity-details-fixture.json").exists()
