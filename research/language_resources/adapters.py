"""Read-only extraction of native source structures into typed assertions."""

import csv
from contextlib import closing
import json
import re
import sqlite3
import xml.etree.ElementTree as ET

import conllu
import penman
from penman.models.amr import model as amr_model

from .downloads import files_named
from .text import write_words, write_massive_words


def relative(path, payload):
    return path.relative_to(payload).as_posix()


def token_id(value):
    return "".join(map(str, value)) if isinstance(value, tuple) else str(value)


def read_ud(payload, writer):
    for path in sorted(payload.rglob("ru_*-ud-*.conllu")):
        if "not-to-release" in path.parts:
            continue
        file = relative(path, payload)
        corpus = path.name.split("-ud-")[0]
        namespace = f"ud:{corpus}"
        document_id = path.stem
        with path.open(encoding="utf-8-sig") as stream:
            for sequence, sentence in enumerate(conllu.parse_incr(stream), 1):
                document_id = sentence.metadata.get("newdoc id", document_id)
                document = writer.entity(namespace, "document", document_id, document_id,
                                         file=file, record=document_id)
                local_id = sentence.metadata.get("sent_id", f"{path.stem}:{sequence}")
                sentence_node = writer.entity(namespace, "sentence", local_id,
                    sentence.metadata.get("text", local_id), {"raw": sentence.metadata}, file, local_id)
                writer.edge(document, "text:contains", sentence_node, file, local_id)
                nodes = {}
                for token in sentence:
                    identifier = token_id(token["id"])
                    record = f"{local_id}/token/{identifier}"
                    kind = "multiword_token" if "-" in identifier else "token"
                    node = writer.entity(namespace, kind, f"{local_id}/{identifier}",
                                         token["form"], {"raw": dict(token)}, file, record)
                    nodes[identifier] = node
                    writer.edge(sentence_node, "text:contains", node, file, record)
                    writer.lexeme(node, token.get("lemma"), file, record, token.get("upos"))
                    if writer.word_index is not None and isinstance(token["id"], int):
                        writer.word_index.observe(token["form"], token.get("lemma"), token.get("upos"), file, record)
                for token in sentence:
                    identifier = token_id(token["id"])
                    record = f"{local_id}/token/{identifier}"
                    target = nodes[identifier]
                    if "-" in identifier:
                        start, end = map(int, identifier.split("-"))
                        for member in range(start, end + 1):
                            writer.edge(target, "ud:multiword_member", nodes[str(member)], file, record)
                        continue
                    head = token.get("head")
                    if head is not None:
                        parent = sentence_node if head == 0 else nodes[token_id(head)]
                        writer.edge(parent, "ud:" + (token.get("deprel") or "dep"), target, file, record)
                    for relation, enhanced_head in token.get("deps") or []:
                        parent = sentence_node if enhanced_head == 0 else nodes[token_id(enhanced_head)]
                        writer.edge(parent, "ud-enhanced:" + relation, target, file, record)
                if sequence % 10000 == 0:
                    print(f"  UD {path.name}: {sequence} sentences", flush=True)


def read_ruwordnet(payload, writer):
    paths = list(payload.rglob("*.db")) + list(payload.rglob("*.sqlite"))
    path = paths[0]
    file = relative(path, payload)
    namespace = "ruwordnet"
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, kind in [("synset", "synset"), ("sense", "sense"),
                            ("wn_synset", "external_synset"), ("wn_sense", "external_sense")]:
            if table not in tables:
                continue
            for source_row in connection.execute(f'SELECT * FROM "{table}"'):
                row = dict(source_row)
                local_id = str(row.get("id", row.get("key")))
                record = f"{table}:{local_id}"
                node = writer.entity(namespace, kind, local_id,
                    row.get("name") or row.get("title") or row.get("definition") or local_id,
                    {"raw": row}, file, record)
                if table in {"sense", "wn_sense"}:
                    target_kind = "synset" if table == "sense" else "external_synset"
                    target = writer.entity(namespace, target_kind, row["synset_id"],
                                           row["synset_id"], file=file, record=record)
                    writer.edge(node, "ruwordnet:sense_of", target, file, record)
                if table == "sense":
                    writer.lexeme(node, row.get("lemma") or row.get("name"), file, record)
                if len(writer.entities) >= 10000:
                    writer.flush()
        for table in sorted(tables):
            if not table.endswith("_relation"):
                continue
            columns = list(connection.execute(f'PRAGMA table_info("{table}")'))
            references = {row[3]: row[2] for row in connection.execute(f'PRAGMA foreign_key_list("{table}")')}
            if len(columns) != 2:
                raise ValueError(f"Unsupported RuWordNet relation schema: {table}")
            kinds = {"sense": "sense", "synset": "synset", "wn_synset": "external_synset", "wn_sense": "external_sense"}
            for row in connection.execute(f'SELECT * FROM "{table}"'):
                record = table + ":" + json.dumps(list(row), ensure_ascii=False)
                endpoints = []
                for column, identifier in zip(columns, row):
                    kind = kinds[references[column[1]]]
                    endpoints.append(writer.entity(namespace, kind, identifier, identifier,
                                                  file=file, record=record))
                writer.edge(endpoints[0], "ruwordnet:" + table.removesuffix("_relation"), endpoints[1],
                            file, record)


def tabular_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        first_line = stream.readline()
        stream.seek(0)
        delimiter = "\t" if "\t" in first_line else ";" if ";" in first_line else ","
        for line, row in enumerate(csv.DictReader(stream, delimiter=delimiter), 2):
            if None in row:
                raise ValueError(f"Unexpected columns in {path.name}:{line}")
            yield str(line), {key: value or "" for key, value in row.items()}


def read_framebank(payload, writer):
    namespace = "framebank"
    for name in ["framebank_dict_cx.txt", "framebank_dict_cx_items.txt",
                 "exampleindex.csv", "framebank_anno_ex_items.txt", "framebank_anno_ex_circ.txt"]:
        for path in files_named(payload, name):
            file = relative(path, payload)
            for record, row in tabular_rows(path):
                construction_id = row.get("ConstrIndex")
                example_id = row.get("ExIndex")
                construction = None
                if construction_id:
                    construction = writer.entity(namespace, "construction", construction_id,
                        row.get("ConstrName") or row.get("Constr") or construction_id,
                        {"raw": row} if name == "framebank_dict_cx.txt" else None, file, record)
                example = None
                if example_id:
                    example = writer.entity(namespace, "example", example_id,
                        row.get("Example") or example_id,
                        {"raw": row} if name == "exampleindex.csv" else None, file, record)
                if construction and example:
                    writer.edge(example, "framebank:instantiates", construction, file, record)
                if name in {"framebank_dict_cx_items.txt", "framebank_anno_ex_items.txt", "framebank_anno_ex_circ.txt"}:
                    local_id = row.get("ItemExIndex") or f"{name}:{construction_id}:{example_id}:{row.get('Place', row.get('PlaceC', record))}"
                    element = writer.entity(namespace, "construction_element", local_id,
                        row.get("WordDep") or row.get("Phrase") or row.get("Role") or local_id,
                        {"raw": row}, file, record)
                    owner = example or construction
                    if owner:
                        writer.edge(owner, "framebank:has_element", element, file, record)
                    if construction and example:
                        writer.edge(element, "framebank:construction", construction, file, record)
                    for field in ["Role", "SemClass", "Sem"]:
                        if row.get(field) and row[field] not in {"-", "N/A"}:
                            value = writer.entity(namespace, "role" if field == "Role" else "semantic_constraint",
                                field + ":" + row[field], row[field], file=file, record=record)
                            writer.edge(element, "framebank:" + field, value, file, record)
                for lemma in row.get("KeyLexemes", "").split(","):
                    lemma = lemma.strip()
                    if construction and re.fullmatch(r"[А-Яа-яЁё]+(?:[ -][А-Яа-яЁё]+)*", lemma):
                        writer.lexeme(construction, lemma, file, record)
                if len(writer.entities) >= 10000:
                    writer.flush()
                if int(record) % 50000 == 0:
                    print(f"  FrameBank {name}: {record} rows", flush=True)


def read_semontocor(payload, writer):
    namespace = "semontocor"
    ns = {"s": "http://www.w3.org/2000/svg"}
    for path in sorted(payload.rglob("*.svg")):
        file = relative(path, payload)
        tree = ET.parse(path)
        graph = tree.find(".//s:g[@class='graph']", ns)
        if graph is None:
            raise ValueError(f"Expected Graphviz SVG: {file}")
        text = " ".join(element.text or "" for element in graph.findall("s:text", ns)).strip()
        sentence = writer.entity(namespace, "sentence", file, text or path.stem,
                                 {"raw": {"text": text, "format": "graphviz-svg"}}, file, "graph")
        nodes = {}
        for group in graph.findall(".//s:g[@class='node']", ns):
            title = group.findtext("s:title", namespaces=ns)
            if not title or title in nodes:
                raise ValueError(f"Missing or duplicate SVG node title in {file}")
            label = " ".join(element.text or "" for element in group.findall(".//s:text", ns))
            node = writer.entity(namespace, "semantic_node", file + "#" + title, label or title,
                                 {"raw": {"title": title, "label": label}}, file, title)
            nodes[title] = node
            writer.edge(sentence, "semontocor:contains", node, file, title)
        for group in graph.findall(".//s:g[@class='edge']", ns):
            title = group.findtext("s:title", namespaces=ns) or ""
            endpoints = title.split("->")
            if len(endpoints) != 2 or any(endpoint not in nodes for endpoint in endpoints):
                raise ValueError(f"Unresolved SVG edge {title} in {file}")
            label = " ".join(element.text or "" for element in group.findall(".//s:text", ns)).strip()
            writer.edge(nodes[endpoints[0]], "semontocor:" + (label or "unlabeled"), nodes[endpoints[1]],
                        file, group.attrib.get("id", title), attributes={"raw": {"title": title, "label": label}})
        fragments = []
        for group in graph.findall(".//s:g[@class='cluster']", ns):
            title = group.findtext("s:title", namespaces=ns) or group.attrib["id"]
            label = " ".join(element.text or "" for element in group.findall("s:text", ns))
            fragment = writer.entity(namespace, "surface_fragment", file + "#" + title, label or title,
                                     {"raw": {"title": title, "label": label}}, file, title)
            writer.edge(sentence, "semontocor:surface_fragment", fragment, file, title)
            fragments.append({"id": fragment, "text": label})
        write_words(writer, namespace, sentence, file, text, file, "graph", fragments)


def jsonl_rows(path):
    with path.open(encoding="utf-8-sig") as stream:
        for line, text in enumerate(stream, 1):
            if text.strip():
                yield str(line), json.loads(text)


def named_entities(annotation):
    """The entity construction used in the authors' MASSIVE-AMR notebook."""
    entities = []
    for slot in re.findall(r"\[(.*?)\]", annotation):
        kind, value = slot.split(":", 1)
        parts = [word.replace("'s", "") for word in value.strip().split() if word not in {"the", "this"}]
        operators = " ".join(f":op{index} {json.dumps(word, ensure_ascii=False)}" for index, word in enumerate(parts, 1))
        entities.append((kind.strip(), f"/ name {operators})"))
    return sorted(entities)


def localize_amr(raw_amr, english, russian):
    if "definition_word" in russian:
        return None, ["definition_word excluded by the authors' localization procedure"]
    english_entities = named_entities(english)
    russian_entities = named_entities(russian)
    issues = []
    if len(english_entities) != len(russian_entities):
        issues.append("Unequal number of annotated entity slots")
    for english_entity, russian_entity in zip(english_entities, russian_entities):
        if english_entity[0] != russian_entity[0]:
            issues.append("Entity slot types do not match")
        elif english_entity[1] not in raw_amr:
            issues.append(f"English entity absent from AMR: {english_entity[0]}")
        else:
            raw_amr = raw_amr.replace(english_entity[1], russian_entity[1])
    if issues:
        return None, issues
    return raw_amr, []


def write_amr_graph(writer, graph_id, raw_amr, owner, file, record, rule):
    graph = penman.decode(raw_amr, model=amr_model)
    variables = set(graph.variables())
    nodes = {}
    for instance in graph.instances():
        nodes[instance.source] = writer.entity("amr", "semantic_node", graph_id + "/" + instance.source,
            instance.target, {"raw": {"variable": instance.source, "concept": instance.target}}, file, record, rule)
        writer.edge(owner, "amr:contains", nodes[instance.source], file, record, rule)
    for number, (subject, predicate, value) in enumerate(graph.triples):
        if predicate == ":instance":
            continue
        if value in variables:
            target = nodes[value]
        else:
            target = writer.entity("amr", "literal", f"{graph_id}/literal/{number}", str(value),
                {"raw": {"value": value}}, file, record, rule)
        writer.edge(nodes[subject], "amr:" + predicate.removeprefix(":"), target, file, record, rule)
    if graph.top:
        writer.edge(owner, "amr:top", nodes[graph.top], file, record, rule)


def read_amr(payload, writer):
    locales = {}
    for locale in ["ru-RU", "en-US"]:
        matches = files_named(payload, locale + ".jsonl")
        locales[locale] = {str(row["id"]): (relative(matches[0], payload), line, row)
                           for line, row in jsonl_rows(matches[0])} if matches else {}
    path = files_named(payload, "massive_amr.jsonl")[0]
    file = relative(path, payload)
    for line, row in jsonl_rows(path):
        identifier = str(row["id"])
        english_row = locales["en-US"].get(identifier)
        english = english_row[2] if english_row else row
        owner = writer.entity("amr", "sentence", identifier + ":en-US", row["utt"], {"raw": row}, file, line)
        write_amr_graph(writer, identifier + ":en-US", row["raw_amr"], owner, file, line, "source")
        russian_row = locales["ru-RU"].get(identifier)
        if not russian_row:
            continue
        russian_file, russian_line, russian = russian_row
        localized, issues = localize_amr(row["raw_amr"], english["annot_utt"], russian["annot_utt"])
        translated = writer.entity("amr", "sentence", identifier + ":ru-RU", russian["utt"],
            {"raw": russian, "localization_issues": issues,
             "localized_amr": localized, "rule": "massive-authors-localization-v1"}, russian_file, russian_line)
        writer.edge(translated, "amr:parallel_source_id", owner, russian_file, russian_line,
                    "massive-id-alignment-v1", {"source_id": identifier})
        write_massive_words(writer, translated, identifier + ":ru-RU", russian["utt"],
                            russian.get("annot_utt", ""), russian_file, russian_line)
        if localized:
            # Both the Russian sentence and the source graph contribute provenance.
            writer.evidence.append((translated, writer.source, file, line, "massive-authors-localization-v1"))
            write_amr_graph(writer, identifier + ":ru-RU", localized, translated,
                            file, line, "massive-authors-localization-v1")


ADAPTERS = {"ud": read_ud, "ruwordnet": read_ruwordnet, "framebank": read_framebank,
            "semontocor": read_semontocor, "amr": read_amr}
