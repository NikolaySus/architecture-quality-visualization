"""Star-shaped assertion storage and atomic publication of complete SQLite generations."""

import hashlib
from collections import Counter
import json
import sqlite3
import sys
import unicodedata
import uuid
from importlib.metadata import version

from .storage import CATALOG, MODULE, atomic_json, digest_file, json_text, utc_now


SCHEMA_VERSION = 2
RULE_VERSION = "explicit-lexical-and-words-v5"
COMPONENT_RULE = "published-lemma-components-v1"
SCHEMA = """
PRAGMA journal_mode=DELETE;
PRAGMA cache_size=-262144;
PRAGMA temp_store=FILE;
CREATE TABLE source_snapshot(source TEXT PRIMARY KEY, snapshot_id TEXT, manifest TEXT NOT NULL);
CREATE TABLE entity(
 id TEXT PRIMARY KEY, source TEXT REFERENCES source_snapshot(source), kind TEXT NOT NULL,
 namespace TEXT NOT NULL, local_id TEXT NOT NULL, label TEXT NOT NULL, attributes TEXT NOT NULL
);
CREATE TABLE entity_evidence(
 entity_id TEXT NOT NULL REFERENCES entity(id), source TEXT NOT NULL REFERENCES source_snapshot(source),
 file TEXT NOT NULL, record TEXT NOT NULL, rule TEXT NOT NULL,
 PRIMARY KEY(entity_id, source, file, record, rule)
) WITHOUT ROWID;
CREATE TABLE relation_type(id TEXT PRIMARY KEY);
CREATE TABLE fact_relation(
 id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES entity(id),
 predicate TEXT NOT NULL REFERENCES relation_type(id), object_id TEXT NOT NULL REFERENCES entity(id),
 source TEXT NOT NULL REFERENCES source_snapshot(source), file TEXT NOT NULL,
 record TEXT NOT NULL, rule TEXT NOT NULL, attributes TEXT NOT NULL
);
CREATE TABLE source_relation(
 id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES entity(id),
 predicate TEXT NOT NULL, object_id TEXT NOT NULL REFERENCES entity(id),
 source TEXT NOT NULL REFERENCES source_snapshot(source), file TEXT NOT NULL,
 record TEXT NOT NULL, rule TEXT NOT NULL, attributes TEXT NOT NULL
);
CREATE TABLE relation_origin(
 relation_id TEXT NOT NULL REFERENCES fact_relation(id),
 source_relation_id TEXT NOT NULL REFERENCES source_relation(id),
 mapping_rule TEXT NOT NULL, attributes TEXT NOT NULL,
 PRIMARY KEY(relation_id,source_relation_id,mapping_rule)
) WITHOUT ROWID;
CREATE INDEX relation_origin_source ON relation_origin(source_relation_id);
CREATE VIEW original_fact_relation AS
 SELECT * FROM source_relation
 UNION ALL
 SELECT f.* FROM fact_relation f
 WHERE NOT EXISTS(SELECT 1 FROM source_relation s WHERE s.id=f.id)
   AND NOT EXISTS(SELECT 1 FROM relation_origin o WHERE o.relation_id=f.id);
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def stable_id(*parts):
    return hashlib.sha256(json_text(parts).encode("utf-8")).hexdigest()


def lexical_key(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


class GraphWriter:
    """Adapters write bounded batches. Source-local identifiers survive rebuilds."""

    def __init__(self, connection, source, word_index=None, table_prefix="input_"):
        self.connection = connection
        self.source = source
        self.word_index = word_index
        self.table_prefix = table_prefix
        self.entities = []
        self.evidence = []
        self.relations = []
        self.shared_entities = set()
        self.counts = Counter()
        self.skipped_keys = []

    def entity(self, namespace, kind, local_id, label, attributes=None,
               file="", record="", rule="source", shared=False):
        source = None if shared else self.source
        entity_id = stable_id(source, namespace, kind, str(local_id))
        if not shared or entity_id not in self.shared_entities:
            self.entities.append((entity_id, source, kind, namespace, str(local_id), str(label),
                                  json_text(attributes or {})))
            if shared:
                self.shared_entities.add(entity_id)
        self.evidence.append((entity_id, self.source, file, str(record), rule))
        return entity_id

    def edge(self, subject, predicate, target, file, record, rule="source", attributes=None):
        attributes = json_text(attributes or {})
        relation_id = stable_id(subject, predicate, target, self.source, file, str(record), rule, attributes)
        self.relations.append((relation_id, subject, predicate, target, self.source,
                               file, str(record), rule, attributes))
        if len(self.entities) + len(self.relations) >= 10000:
            self.flush()
        return relation_id

    def _lexeme_node(self, lemma, file, record, rule):
        key = lexical_key(lemma)
        return self.entity("lexicon:ru", "lexeme", key, key,
                           {"language": "ru", "normalization": "NFC-casefold-whitespace"},
                           file, record, rule, shared=True)

    def lexeme(self, owner, lemma, file, record, pos=None, rule="lexical-anchor-v1", attributes=None):
        if not lemma or lemma == "_":
            return
        node = self._lexeme_node(lemma, file, record, rule)
        self.edge(owner, "lexical:lemma_match", node, file, record,
                  rule, {"lemma": lemma, "pos": pos, **(attributes or {})})
        if len(lemma.split()) < 2:
            return
        # Local import keeps the shared tokenizer in text.py without an import cycle.
        from .text import word_matches

        matches = word_matches(lemma)
        if len(matches) < 2:
            return
        self.counts["multiword_lemma_observations"] += 1
        for position, match in enumerate(matches):
            component = self._lexeme_node(match.group(), file, record, COMPONENT_RULE)
            self.edge(node, "lexical:has_component", component, file, record, COMPONENT_RULE,
                      {"lemma": lemma, "component": match.group(), "position": position,
                       "start": match.start(), "end": match.end()})
            self.counts["component_assertions"] += 1

    def flush(self):
        self.connection.executemany(f"INSERT INTO {self.table_prefix}entity VALUES(?,?,?,?,?,?,?)", self.entities)
        self.connection.executemany(f"INSERT INTO {self.table_prefix}entity_evidence VALUES(?,?,?,?,?)", self.evidence)
        self.connection.executemany(f"INSERT INTO {self.table_prefix}fact_relation VALUES(?,?,?,?,?,?,?,?,?)", self.relations)
        self.entities.clear()
        self.evidence.clear()
        self.relations.clear()


def input_signature(workspace, snapshots=None):
    implementation = {name: digest_file(MODULE / name) for name in [
        "adapters.py", "warehouse.py", "text.py", "storage.py", "downloads.py",
        "normalization.py", "semantic_normalization.json"]}
    project = MODULE.parents[1]
    environment = {name: digest_file(project / name) for name in ["uv.lock", "pyproject.toml", ".python-version"]}
    environment.update({"python": list(sys.version_info[:3]), "sqlite": sqlite3.sqlite_version,
                        "platform": sys.platform,
                        "unicode": unicodedata.unidata_version,
                        "packages": {name: version(name) for name in ["conllu", "penman"]}})
    inputs = {"snapshots": workspace.active() if snapshots is None else snapshots, "schema": SCHEMA_VERSION,
              "rules": RULE_VERSION, "implementation": implementation, "environment": environment}
    return stable_id(inputs), inputs


def _publish_generation(workspace, connection, database, generation_id, signature, inputs, snapshots, diagnostics):
    from .normalization import logical_fingerprints

    # Keep the parent-key working set in cache during reference validation.
    connection.execute("PRAGMA cache_size=-1048576")
    print("ETL check references", flush=True)
    violations = connection.execute("PRAGMA foreign_key_check").fetchmany(5)
    if violations:
        raise ValueError(f"Dangling graph references: {violations}")
    print("ETL check structure", flush=True)
    if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise ValueError("Warehouse structural integrity check failed")
    counts = {name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
              for name in ["entity", "fact_relation", "entity_evidence", "source_relation", "relation_origin"]}
    print("ETL logical fingerprints", flush=True)
    fingerprints = logical_fingerprints(connection)
    print("ETL recheck build inputs", flush=True)
    if input_signature(workspace)[0] != signature:
        raise ValueError("Build inputs changed during ETL. Run rebuild again")
    for source in snapshots:
        workspace.verify(source)
    result = {"id": generation_id, "database": database.name, "signature": signature,
              "inputs": inputs, "created_at": utc_now(), "counts": counts,
              "diagnostics": diagnostics,
              "fingerprints": fingerprints,
              "validation": {"foreign_keys": "pass", "sqlite_quick_check": "pass",
                             "build_inputs_unchanged": "pass", "snapshot_hashes": "pass"},
              "sources": {source: {"available": source in snapshots,
                  "complete": snapshots[source][1]["complete"] if source in snapshots else False}
                  for source in CATALOG}}
    connection.execute("INSERT INTO metadata VALUES('generation',?)", (json_text(result),))
    connection.commit()
    connection.close()
    atomic_json(workspace.root / "build.json", {"status": "ok", "generation": generation_id})
    atomic_json(workspace.root / "current.json", result)
    return result


def rebuild(workspace, force=False):
    from .adapters import ADAPTERS
    from .text import WordIndex
    from .normalization import normalize

    with workspace.lock():
        signature, inputs = input_signature(workspace)
        try:
            snapshots = {source: workspace.verify(source) for source in inputs["snapshots"]}
        except Exception as error:
            atomic_json(workspace.root / "build.json", {"status": "error", "at": utc_now(), "error": str(error)})
            raise
        current = workspace.generation()
        if current and current["signature"] == signature and workspace.database().exists() and not force:
            return {**current, "skipped": True}
        warehouse = workspace.root / "warehouse"
        warehouse.mkdir(parents=True, exist_ok=True)
        generation_id = uuid.uuid4().hex
        database = warehouse / (generation_id + ".sqlite")
        input_database = warehouse / (generation_id + ".input.sqlite")
        connection = sqlite3.connect(database)
        input_connection = sqlite3.connect(input_database)
        try:
            connection.executescript(SCHEMA)
            input_connection.executescript(SCHEMA)
            # The private input spool has no uniqueness indexes. Assertions are merged
            # in global key order, avoiding random B-tree writes for every source row.
            for table in ["entity", "entity_evidence", "fact_relation"]:
                input_connection.execute(f"CREATE TABLE input_{table} AS SELECT * FROM {table} WHERE 0")
            input_connection.commit()
            for source, (_, manifest) in snapshots.items():
                connection.execute("INSERT INTO source_snapshot VALUES(?,?,?)",
                                   (source, manifest["id"], json_text(manifest)))
            word_index = WordIndex() if "ud" in snapshots else None
            diagnostics = {"sources": {}}
            for source in sorted(snapshots, key=lambda name: (name != "ud", name)):
                directory, _ = snapshots[source]
                print(f"ETL {source}", flush=True)
                writer = GraphWriter(input_connection, source, word_index)
                ADAPTERS[source](directory / "payload", writer)
                writer.flush()
                input_connection.commit()
                diagnostics["sources"][source] = {"counts": dict(writer.counts), "skipped_keys": writer.skipped_keys}
            diagnostics["ud_word_index"] = word_index.summary() if word_index else None
            print("ETL diagnostics " + json_text(diagnostics), flush=True)
            input_connection.close()
            connection.execute("ATTACH DATABASE ? AS staging", (str(input_database),))
            print("ETL merge entities", flush=True)
            # Preserve the last full native record, or the first placeholder when
            # the source never supplies a full record for an object.
            connection.execute("""
                INSERT INTO entity
                SELECT id,source,kind,namespace,local_id,label,attributes FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY id ORDER BY
                            CASE WHEN attributes<>'{}' AND label<>'' THEN 0 ELSE 1 END,
                            CASE WHEN attributes<>'{}' AND label<>'' THEN -rowid ELSE rowid END
                    ) AS occurrence
                    FROM staging.input_entity
                ) WHERE occurrence=1 ORDER BY id
            """)
            print("ETL merge provenance", flush=True)
            connection.execute("""
                INSERT INTO entity_evidence SELECT DISTINCT * FROM staging.input_entity_evidence
                ORDER BY entity_id,source,file,record,rule
            """)
            print("ETL merge relations", flush=True)
            connection.execute("""
                INSERT INTO relation_type SELECT DISTINCT predicate FROM staging.input_fact_relation ORDER BY predicate
            """)
            connection.execute("""
                INSERT INTO fact_relation SELECT * FROM staging.input_fact_relation GROUP BY id ORDER BY id
            """)
            connection.commit()
            connection.execute("DETACH DATABASE staging")
            input_database.unlink()
            print("ETL indexes", flush=True)
            connection.executescript("""
                CREATE INDEX entity_filter ON entity(source,kind,label);
                CREATE INDEX entity_local_id ON entity(local_id);
                CREATE INDEX relation_subject ON fact_relation(subject_id,predicate);
                CREATE INDEX relation_object ON fact_relation(object_id,predicate);
                CREATE INDEX relation_source ON fact_relation(source,predicate);
            """)
            print("ETL semantic normalization", flush=True)
            diagnostics["semantic_normalization"] = normalize(connection)
            connection.commit()
            print("ETL text search", flush=True)
            connection.executescript("""
                CREATE VIRTUAL TABLE entity_fts USING fts5(label,local_id,id,
                    content='entity',content_rowid='rowid', tokenize='unicode61 remove_diacritics 0');
                INSERT INTO entity_fts(entity_fts) VALUES('rebuild');
            """)
            return _publish_generation(workspace, connection, database, generation_id,
                                       signature, inputs, snapshots, diagnostics)
        except Exception as error:
            input_connection.close()
            connection.close()
            database.unlink(missing_ok=True)
            input_database.unlink(missing_ok=True)
            atomic_json(workspace.root / "build.json", {"status": "error", "at": utc_now(), "error": str(error)})
            raise
