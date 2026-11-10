"""Versioned semantic projections with reversible links to the input assertions."""

from collections import Counter, defaultdict
import hashlib
import json
import re
import sqlite3

from .storage import MODULE, json_text
from .warehouse import GraphWriter, lexical_key, stable_id


RULES_FILE = MODULE / "semantic_normalization.json"


def load_rules(path=RULES_FILE):
    rules = json.loads(path.read_text(encoding="utf-8"))
    if rules["framebank_projection"] not in {"role_assignment_and_slot_edges", "role_assignment_only"}:
        raise ValueError("Unknown FrameBank projection in semantic normalization rules")
    for start in rules["role_parents"]:
        role = start
        visited = set()
        while role in rules["role_parents"]:
            if role in visited:
                raise ValueError("Cycle in semantic role hierarchy")
            visited.add(role)
            role = rules["role_parents"][role]
    aliases = {key: value["role"] for key, value in rules["framebank_roles"].items()}
    aliases.update({key: value["role"] for key, value in rules["reviewed_framebank_aliases"].items()})
    aliases.update({lexical_key(value): value for value in aliases.values()})
    rules["role_aliases"] = aliases
    return rules


def parse_role(label, rules):
    """Resolve whole labels first, then homogeneous conjunctions or alternatives."""
    key = lexical_key(label)
    if key in rules["missing_role_labels"]:
        return {"status": "missing"}
    aliases = rules["role_aliases"]
    if key in aliases:
        return {"status": "mapped", "operator": "role", "roles": [aliases[key]]}
    alternative = "/" in key
    conjunction = " - " in key
    if alternative and conjunction:
        return {"status": "mixed_expression"}
    parts = key.split("/" if alternative else " - ")
    if len(parts) < 2 or any(part.strip() not in aliases for part in parts):
        return {"status": "unknown_label"}
    roles = sorted({aliases[part.strip()] for part in parts})
    operator = "any_of" if alternative else "all_of"
    return {"status": "mapped", "operator": operator if len(roles) > 1 else "role", "roles": roles}


def logical_fingerprints(connection):
    """Hash ordered logical rows, excluding generation IDs, dates and SQLite pages."""
    result = {}
    tables = {"entity": "id", "entity_evidence": "entity_id,source,file,record,rule",
              "relation_type": "id", "fact_relation": "id", "source_relation": "id",
              "relation_origin": "relation_id,source_relation_id,mapping_rule"}
    for table, ordering in tables.items():
        digest = hashlib.sha256()
        for row in connection.execute(f"SELECT * FROM {table} ORDER BY {ordering}"):
            digest.update((json_text(list(row)) + "\n").encode("utf-8"))
        result[table] = digest.hexdigest()
    return {"algorithm": "ordered-json-rows-sha256-v1", "tables": result,
            "graph": stable_id(result)}


class Normalizer:
    def __init__(self, connection, rules):
        self.connection = connection
        self.rules = rules
        self.version = rules["version"]
        self.writers = {}
        self.origins = []
        self.counts = Counter()
        self.samples = defaultdict(list)
        self.denotations = set()
        self.hierarchy = set()
        self.expressions = set()
        self.unresolved_roles = Counter()
        self.role_definitions = {}
        for value in rules["framebank_roles"].values():
            self.role_definitions.setdefault(value["role"], value["definition"])

    def writer(self, source):
        if source not in self.writers:
            self.writers[source] = GraphWriter(self.connection, source, table_prefix="normalization_")
        return self.writers[source]

    def emit(self, original, subject, predicate, target, rule, details, extra_inputs=()):
        mapping_rule = self.version + "/" + rule
        metadata = {"version": self.version, "rule": rule, "original_id": original["id"],
                    "original_predicate": original["predicate"], "original_subject": original["subject_id"],
                    "original_object": original["object_id"], "original_rule": original["rule"], **details}
        attributes = {**json.loads(original["attributes"]), "normalization": metadata}
        identifier = self.writer(original["source"]).edge(subject, predicate, target,
            original["file"], original["record"], mapping_rule, attributes)
        self.origins.append((identifier, original["id"], mapping_rule, json_text({"input_role": "source"})))
        for extra in extra_inputs:
            self.origins.append((identifier, extra, mapping_rule, json_text({"input_role": "context"})))
        self.counts[f"output:{original['source']}"] += 1
        self.counts[f"rule:{rule}"] += 1
        if len(self.samples[rule]) < 5:
            self.samples[rule].append({"input": original["id"], "output": identifier,
                "subject": subject, "predicate": predicate, "object": target, "details": details})
        if len(self.origins) >= 10000:
            self.flush_origins()
        return identifier

    def flush_origins(self):
        self.connection.executemany("INSERT INTO normalization_origin VALUES(?,?,?,?)", self.origins)
        self.origins.clear()

    def role_term(self, key, original):
        writer = self.writer(original["source"])
        predicate = self.rules["core_roles"].get(key)
        identifier = writer.entity("semantic:roles", "role", key, key,
            {"role_key": key, "core_predicate": "core:" + predicate if predicate else None,
             "definition": self.role_definitions.get(key, ""), "catalog": self.version},
            original["file"], original["record"], self.version + "/role_catalog", shared=True)
        parent = self.rules["role_parents"].get(key)
        if parent and (key, parent) not in self.hierarchy:
            self.hierarchy.add((key, parent))
            parent_id = self.role_term(parent, original)
            self.emit(original, identifier, "core:subrole_of", parent_id, "role_hierarchy",
                      {"level": "role_vocabulary", "role": key, "parent": parent})
        return identifier

    def role_expression(self, parsed, original):
        roles = parsed["roles"]
        if parsed["operator"] == "role":
            return self.role_term(roles[0], original)
        key = json_text({"operator": parsed["operator"], "roles": roles})
        identifier = self.writer(original["source"]).entity("semantic:roles", "role_expression", key,
            (" OR " if parsed["operator"] == "any_of" else " AND ").join(roles),
            {"operator": parsed["operator"], "roles": roles, "catalog": self.version},
            original["file"], original["record"], self.version + "/role_expression", shared=True)
        if key not in self.expressions:
            self.expressions.add(key)
            for position, role in enumerate(roles):
                member = self.role_term(role, original)
                self.emit(original, identifier,
                    "core:alternative_role" if parsed["operator"] == "any_of" else "core:joint_role",
                    member, "role_expression", {"level": "role_vocabulary", "position": position})
        return identifier

    def semantic_relation(self, original, mapping, context):
        subject, target = original["subject_id"], original["object_id"]
        if mapping["inverse"]:
            subject, target = target, subject
        self.emit(original, subject, mapping["predicate"], target, "semantic_relation",
            {**context, "inverted": mapping["inverse"], "role": mapping.get("role"),
             "communicative_anchor": original["subject_id"] if original["source"] == "semontocor" else None})

    def framebank_role(self, original, label, owners):
        parsed = parse_role(label, self.rules)
        self.counts["framebank_role:" + parsed["status"]] += 1
        context = {"level": "slot_annotation", "role_status": parsed["status"], "raw_role": label}
        owner = owners[0] if len(owners) == 1 else None
        context_inputs = [owner["id"]] if owner else []
        if owner:
            context.update({"context_id": owner["owner"],
                            "level": "construction_schema" if owner["kind"] == "construction" else "example_annotation"})
        else:
            self.counts["framebank_owner:" + ("missing" if not owners else "ambiguous")] += 1
        if parsed["status"] != "mapped":
            self.unresolved_roles[(label, parsed["status"])] += 1
            self.emit(original, original["subject_id"], "core:unresolved_role", original["object_id"],
                      "unresolved_role", context, context_inputs)
            return
        target = self.role_expression(parsed, original)
        self.emit(original, original["subject_id"], "core:semantic_role", target, "role_assignment",
                  {**context, "operator": parsed["operator"], "roles": parsed["roles"]}, context_inputs)
        denotation = (original["object_id"], target)
        if denotation not in self.denotations:
            self.denotations.add(denotation)
            self.emit(original, original["object_id"], "core:role_denotation", target, "role_denotation",
                      {"level": "role_vocabulary", "raw_role": label})
        if self.rules["framebank_projection"] != "role_assignment_and_slot_edges" or not owner:
            return
        if parsed["operator"] == "any_of":
            self.emit(original, owner["owner"], "core:role_choice", original["subject_id"], "slot_role_choice",
                      {**context, "role_expression_id": target, "roles": parsed["roles"]}, [owner["id"]])
            return
        for role in parsed["roles"]:
            name = self.rules["core_roles"].get(role)
            predicate = "core:" + name if name else "role:framebank_" + re.sub(r"(?<!^)(?=[A-Z])", "_", role).lower()
            self.emit(original, owner["owner"], predicate, original["subject_id"], "slot_role",
                      {**context, "role": role, "operator": parsed["operator"]}, [owner["id"]])


def normalize(connection, rules=None):
    rules = load_rules() if rules is None else rules
    previous_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    predicates = ["semontocor:" + key for key in rules["semontocor"]]
    predicates.extend("amr:" + key for key in rules["amr"])
    predicates.append("framebank:Role")
    placeholders = ",".join("?" for _ in predicates)
    connection.execute(f"CREATE TEMP TABLE normalization_input AS SELECT * FROM fact_relation WHERE predicate IN ({placeholders})", predicates)
    before = connection.execute("SELECT count(*) FROM fact_relation").fetchone()[0]
    input_count = connection.execute("SELECT count(*) FROM normalization_input").fetchone()[0]
    if not input_count:
        connection.execute("DROP TABLE normalization_input")
        connection.row_factory = previous_factory
        return {"version": rules["version"], "inputs": 0, "skipped": True,
                "before_relations": before, "after_relations": before}
    connection.executescript("""
      CREATE UNIQUE INDEX normalization_input_id ON normalization_input(id);
      CREATE INDEX normalization_input_record ON normalization_input(subject_id,file,record);
      CREATE TEMP TABLE normalization_owner AS
        SELECT f.id,f.subject_id AS owner,f.object_id AS slot,f.file,f.record,e.kind
        FROM fact_relation f JOIN normalization_input n
          ON n.source='framebank' AND n.subject_id=f.object_id AND n.file=f.file AND n.record=f.record
        JOIN entity e ON e.id=f.subject_id
        WHERE f.source='framebank' AND f.predicate='framebank:has_element'
        GROUP BY f.id ORDER BY f.id;
      INSERT INTO source_relation SELECT * FROM normalization_input ORDER BY id;
      INSERT OR IGNORE INTO source_relation
        SELECT f.* FROM fact_relation f JOIN normalization_owner o ON o.id=f.id ORDER BY f.id;
      CREATE TEMP TABLE normalization_entity AS SELECT * FROM entity WHERE 0;
      CREATE TEMP TABLE normalization_entity_evidence AS SELECT * FROM entity_evidence WHERE 0;
      CREATE TEMP TABLE normalization_fact_relation AS SELECT * FROM fact_relation WHERE 0;
      CREATE TEMP TABLE normalization_origin AS SELECT * FROM relation_origin WHERE 0;
    """)
    owners = defaultdict(list)
    for row in connection.execute("SELECT * FROM normalization_owner ORDER BY id"):
        owners[(row["slot"], row["file"], row["record"])].append(dict(row))
    labels = {row["id"]: row["label"] for row in connection.execute(
        "SELECT id,label FROM entity WHERE source='framebank' AND kind='role'")}
    amr_contexts = {}
    question_contexts = defaultdict(list)
    for row in connection.execute("SELECT id,local_id,attributes FROM entity WHERE source='amr' AND kind='semantic_node'"):
        prefix = row["local_id"].split("/", 1)[0]
        context_id = stable_id("amr", "amr", "sentence", prefix)
        amr_contexts[row["id"]] = (context_id, prefix.rsplit(":", 1)[-1])
        if json.loads(row["attributes"]).get("raw", {}).get("concept") == "amr-unknown":
            question_contexts[context_id].append(row["id"])
    normalizer = Normalizer(connection, rules)
    for row in connection.execute("SELECT * FROM normalization_input ORDER BY id"):
        original = dict(row)
        source = original["source"]
        name = original["predicate"].split(":", 1)[1]
        normalizer.counts["input:" + source] += 1
        if source == "semontocor":
            context_id = stable_id(source, source, "sentence", original["file"])
            normalizer.semantic_relation(original, rules["semontocor"][name],
                {"level": "text_graph", "context_id": context_id})
        elif source == "amr":
            context_id, locale = amr_contexts[original["subject_id"]]
            normalizer.semantic_relation(original, {"predicate": rules["amr"][name], "inverse": False},
                {"level": "text_graph", "context_id": context_id, "locale": locale,
                 "context_kind": "question" if context_id in question_contexts else "source_annotation",
                 "question_variables": sorted(question_contexts.get(context_id, []))})
        else:
            normalizer.framebank_role(original, labels[original["object_id"]],
                owners[(original["subject_id"], original["file"], original["record"])])
    for writer in normalizer.writers.values():
        writer.flush()
    normalizer.flush_origins()
    # Shared vocabulary objects have identical attributes across all supporting records.
    if connection.execute("""
      SELECT id FROM normalization_entity GROUP BY id
      HAVING count(DISTINCT label)>1 OR count(DISTINCT attributes)>1 LIMIT 1
    """).fetchone():
        raise ValueError("Conflicting definitions of normalized vocabulary objects")
    connection.executescript("""
      INSERT OR IGNORE INTO entity SELECT * FROM normalization_entity GROUP BY id ORDER BY id;
      INSERT OR IGNORE INTO entity_evidence SELECT DISTINCT * FROM normalization_entity_evidence
        ORDER BY entity_id,source,file,record,rule;
      DELETE FROM fact_relation WHERE id IN (SELECT id FROM normalization_input);
      INSERT OR IGNORE INTO relation_type
        SELECT DISTINCT predicate FROM normalization_fact_relation ORDER BY predicate;
      INSERT INTO fact_relation SELECT * FROM normalization_fact_relation GROUP BY id ORDER BY id;
      INSERT INTO relation_origin SELECT DISTINCT * FROM normalization_origin
        ORDER BY relation_id,source_relation_id,mapping_rule;
      DELETE FROM relation_type WHERE id NOT IN (SELECT DISTINCT predicate FROM fact_relation);
    """)
    unmapped_input = connection.execute("""
      SELECT n.id FROM normalization_input n WHERE NOT EXISTS(
        SELECT 1 FROM relation_origin o WHERE o.source_relation_id=n.id) LIMIT 1
    """).fetchone()
    if unmapped_input:
        raise ValueError("Normalization discarded an input assertion")
    if connection.execute("""
      SELECT * FROM normalization_input EXCEPT SELECT * FROM source_relation LIMIT 1
    """).fetchone():
        raise ValueError("Normalization changed an original assertion")
    if connection.execute("""
      SELECT id FROM normalization_fact_relation n WHERE NOT EXISTS(
        SELECT 1 FROM relation_origin o WHERE o.relation_id=n.id) LIMIT 1
    """).fetchone():
        raise ValueError("Normalized assertion has no origin")
    if connection.execute("""
      SELECT f.id FROM normalization_fact_relation f
      LEFT JOIN entity e ON e.id=json_extract(f.attributes,'$.normalization.context_id')
      WHERE json_extract(f.attributes,'$.normalization.context_id') IS NOT NULL
        AND e.id IS NULL LIMIT 1
    """).fetchone():
        raise ValueError("Normalized assertion references a missing context")
    after = connection.execute("SELECT count(*) FROM fact_relation").fetchone()[0]
    original_count = connection.execute("SELECT count(*) FROM original_fact_relation").fetchone()[0]
    if original_count != before:
        raise ValueError("Original assertion count changed during normalization")
    result = {"version": rules["version"], "inputs": input_count, "before_relations": before,
              "after_relations": after, "original_relations": original_count,
              "counts": dict(normalizer.counts), "samples": dict(normalizer.samples),
              "unresolved_roles": [{"label": label, "reason": reason, "count": count}
                  for (label, reason), count in sorted(normalizer.unresolved_roles.items(),
                      key=lambda item: (-item[1], item[0]))],
              "framebank_projection": rules["framebank_projection"],
              "validation": {"input_coverage": "pass", "original_assertion_count": "pass",
                             "original_assertion_values": "pass", "output_origins": "pass",
                             "context_references": "pass"}}
    connection.executescript("""
      DROP TABLE normalization_input;
      DROP TABLE normalization_owner;
      DROP TABLE normalization_entity;
      DROP TABLE normalization_entity_evidence;
      DROP TABLE normalization_fact_relation;
      DROP TABLE normalization_origin;
    """)
    connection.row_factory = previous_factory
    return result

