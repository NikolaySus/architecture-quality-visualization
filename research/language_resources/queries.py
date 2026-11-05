"""Bounded read-only queries against an immutable warehouse generation."""

from collections import deque
from contextlib import contextmanager
import json
import re
import sqlite3


@contextmanager
def connect(database):
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        yield connection
    finally:
        connection.close()


def search(database, text="", source=None, kind=None, page=0, page_size=50):
    conditions = []
    arguments = []
    if text.strip():
        tokens = re.findall(r"\w+", text, re.UNICODE)
        if tokens:
            query = " AND ".join('"' + token + '"*' for token in tokens)
            conditions.append("(entity.rowid IN (SELECT rowid FROM entity_fts WHERE entity_fts MATCH ?) OR entity.id=? OR entity.local_id=?)")
            arguments.extend([query, text, text])
        else:
            conditions.append("(entity.id=? OR entity.local_id=?)")
            arguments.extend([text, text])
    if source:
        conditions.append("source IS NULL" if source == "shared" else "source=?")
        if source != "shared":
            arguments.append(source)
    if kind:
        conditions.append("kind=?")
        arguments.append(kind)
    clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    with connect(database) as connection:
        rows = connection.execute("SELECT id,source,kind,namespace,local_id,label FROM entity" + clause +
            " ORDER BY rowid LIMIT ? OFFSET ?", [*arguments, page_size + 1, page * page_size]).fetchall()
    return [dict(row) for row in rows[:page_size]], len(rows) > page_size


def kinds(database):
    with connect(database) as connection:
        return [row[0] for row in connection.execute("SELECT DISTINCT kind FROM entity ORDER BY kind")]


def entity_card(database, entity_id, limit=200):
    with connect(database) as connection:
        row = connection.execute("SELECT * FROM entity WHERE id=?", (entity_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["attributes"] = json.loads(result["attributes"])
        evidence = connection.execute("SELECT * FROM entity_evidence WHERE entity_id=? LIMIT ?",
                                      (entity_id, limit + 1)).fetchall()
        relations = connection.execute("""
          SELECT f.*,s.label AS subject_label,o.label AS object_label
          FROM fact_relation f JOIN entity s ON s.id=f.subject_id JOIN entity o ON o.id=f.object_id
          WHERE f.subject_id=? OR f.object_id=? LIMIT ?
        """, (entity_id, entity_id, limit + 1)).fetchall()
        result["evidence"] = [dict(item) for item in evidence[:limit]]
        result["relations"] = [dict(item) for item in relations[:limit]]
        result["truncated"] = len(evidence) > limit or len(relations) > limit
        return result


def neighborhood(database, root, depth=1, limit=200, edge_limit=5000):
    if not 1 <= depth <= 3 or limit < 1 or edge_limit < 1:
        raise ValueError("Graph depth must be 1..3 and node/edge limits must be positive")
    with connect(database) as connection:
        if not connection.execute("SELECT 1 FROM entity WHERE id=?", (root,)).fetchone():
            return {"nodes": [], "edges": [], "truncated": False}
        selected = {root}
        frontier = deque([(root, 0)])
        edges = {}
        truncated = False
        while frontier:
            node, level = frontier.popleft()
            if level >= depth:
                continue
            candidates = connection.execute("""
              SELECT * FROM fact_relation WHERE subject_id=? OR object_id=? LIMIT ?
            """, (node, node, edge_limit + 1))
            for candidate in candidates:
                if candidate["id"] in edges:
                    continue
                endpoints = {candidate["subject_id"], candidate["object_id"]}
                new_nodes = endpoints - selected
                if len(selected) + len(new_nodes) > limit:
                    truncated = True
                    continue
                if len(edges) >= edge_limit:
                    truncated = True
                    frontier.clear()
                    break
                selected.update(new_nodes)
                frontier.extend((new_node, level + 1) for new_node in sorted(new_nodes))
                edges[candidate["id"]] = dict(candidate)
        nodes = []
        selected_ids = sorted(selected)
        # Keep large neighborhoods below SQLite's per-statement parameter limit.
        for offset in range(0, len(selected_ids), 1000):
            batch = selected_ids[offset:offset + 1000]
            placeholders = ",".join("?" for _ in batch)
            nodes.extend(dict(row) for row in connection.execute(
                f"SELECT id,label,kind,source FROM entity WHERE id IN ({placeholders}) ORDER BY id", batch))
    return {"nodes": nodes, "edges": list(edges.values()), "truncated": truncated}
