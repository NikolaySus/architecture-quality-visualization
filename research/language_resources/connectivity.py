"""Weak components of a pinned warehouse generation, using a streaming edge scan."""

from array import array
from collections import Counter, defaultdict
from heapq import nsmallest
import json
import sqlite3

from .queries import connect
from .storage import CATALOG, atomic_json, utc_now


def _root(parents, node):
    root = node
    while parents[root] >= 0:
        root = parents[root]
    while node != root:
        previous = parents[node]
        parents[node] = root
        node = previous
    return root


def _share(total, included):
    return {"total": total, "in_largest": included,
            "percent": round(100 * included / total, 6) if total else None}


def _component_details(connection, members):
    result = []
    batch_size = min(1000, connection.getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER))
    for rowids in members.values():
        nodes = []
        for offset in range(0, len(rowids), batch_size):
            batch = rowids[offset:offset + batch_size]
            placeholders = ",".join("?" for _ in batch)
            for row in connection.execute(f"SELECT * FROM entity WHERE rowid IN ({placeholders})", batch):
                nodes.append({**dict(row), "attributes": json.loads(row["attributes"])})
        nodes.sort(key=lambda node: node["id"])
        identifiers = [node["id"] for node in nodes]
        edges = []
        evidence = []
        for offset in range(0, len(identifiers), batch_size):
            batch = identifiers[offset:offset + batch_size]
            placeholders = ",".join("?" for _ in batch)
            for row in connection.execute(
                    f"SELECT * FROM fact_relation WHERE subject_id IN ({placeholders})", batch):
                edges.append({**dict(row), "attributes": json.loads(row["attributes"])})
            evidence.extend(dict(row) for row in connection.execute(
                f"SELECT * FROM entity_evidence WHERE entity_id IN ({placeholders})", batch))
        result.append({"id": identifiers[0], "size": len(nodes),
                       "sources": dict(Counter(node["source"] or "shared" for node in nodes)),
                       "nodes": nodes, "edges": edges, "evidence": evidence})
    return sorted(result, key=lambda item: (-item["size"], item["id"]))


def components(workspace, details=False):
    generation = workspace.generation()
    if not generation or not workspace.database(generation).exists():
        raise ValueError("Build a warehouse generation before counting components")
    database = workspace.database(generation)
    with connect(database) as connection:
        # The ID index fits in cache. Endpoint rowids avoid a Python hash map of IDs.
        connection.execute("PRAGMA cache_size=-1048576")
        count, first, last = connection.execute("SELECT count(*),min(rowid),max(rowid) FROM entity").fetchone()
        if count and (first != 1 or last != count):
            raise ValueError("Warehouse entity rowids must be dense. Rebuild this generation")
        expected_edges = connection.execute("SELECT count(*) FROM fact_relation").fetchone()[0]
        # Roots store negative component sizes, other entries store a parent index.
        parents = array("q", [-1]) * count
        edge_count = 0
        cursor = connection.execute("""
          SELECT s.rowid,o.rowid FROM fact_relation f
          JOIN entity s ON s.id=f.subject_id JOIN entity o ON o.id=f.object_id
        """)
        for subject, target in cursor:
            subject_root = _root(parents, subject - 1)
            target_root = _root(parents, target - 1)
            if subject_root != target_root:
                if parents[subject_root] > parents[target_root]:
                    subject_root, target_root = target_root, subject_root
                parents[subject_root] += parents[target_root]
                parents[target_root] = subject_root
            edge_count += 1
            if edge_count % 1_000_000 == 0:
                print(f"Components edges {edge_count}/{expected_edges}", flush=True)
        if edge_count != expected_edges:
            raise ValueError("Dangling graph edges encountered during component analysis")

        component_count = sum(size < 0 for size in parents)
        isolated_count = parents.count(-1)
        largest = nsmallest(10, ((size, root) for root, size in enumerate(parents) if size < 0))
        largest_root = largest[0][1] if largest else None
        top_components = []
        for size, root in largest:
            representative = connection.execute(
                "SELECT id,label,source,kind FROM entity WHERE rowid=?", (root + 1,)).fetchone()
            top_components.append({"size": -size, "percent": round(100 * -size / count, 6),
                                   "representative": dict(representative)})

        totals = Counter()
        included = Counter()
        outside = defaultdict(list)
        print("Components source membership", flush=True)
        for number, row in enumerate(connection.execute("SELECT rowid,source,kind FROM entity"), 1):
            key = (row["source"] or "shared", row["kind"])
            totals[key] += 1
            root = _root(parents, row["rowid"] - 1)
            if root == largest_root:
                included[key] += 1
            elif details:
                outside[root].append(row["rowid"])
            if number % 1_000_000 == 0:
                print(f"Components objects {number}/{count}", flush=True)
        other_components = _component_details(connection, outside) if details else None

    sources = sorted({source for source, _ in totals} | set(CATALOG) | {"shared"})
    by_source = {}
    for source in sources:
        kinds = {kind: _share(total, included[source, kind])
                 for (owner, kind), total in sorted(totals.items()) if owner == source}
        by_source[source] = {**_share(sum(item["total"] for item in kinds.values()),
                                    sum(item["in_largest"] for item in kinds.values())),
                             "by_kind": kinds}
    report = {"generation": generation["id"], "signature": generation["signature"],
              "database": generation["database"], "created_at": utc_now(),
              "method": "union_find", "direction": "ignored", "relations": "all_fact_relation",
              "snapshots": generation["inputs"]["snapshots"], "objects": count,
              "edges": edge_count, "components": component_count,
              "singleton_components": isolated_count,
              "largest_size": -largest[0][0] if largest else 0,
              "top_components": top_components, "by_source": by_source}
    if details:
        report["other_components"] = other_components
    prefix = "connectivity-details" if details else "connectivity"
    output = workspace.root / "analysis" / f"{prefix}-{generation['id']}.json"
    atomic_json(output, report)
    return {**report, "report_path": str(output)}
