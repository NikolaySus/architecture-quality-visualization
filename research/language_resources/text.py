"""Derived word occurrences attached to the smallest aligned text fragment."""

from collections import Counter, defaultdict
import re

from .warehouse import lexical_key


WORD_PART = r"[^\W_](?:[^\W_]|[\u0300-\u036f])*"
WORD_PATTERN = re.compile(rf"{WORD_PART}(?:[-'’]{WORD_PART})*", re.UNICODE)
WORD_RULE = "smallest-text-container-v1"
LEMMA_RULE = "unambiguous-clean-ud-form-v2"
RUWORDNET_TEXT_RULE = "ruwordnet-text-fields-v1"


class WordIndex:
    """One lookup per observed UD form, with ambiguous lemmas left unresolved."""

    def __init__(self):
        self.forms = {}
        self.typo_forms = set()
        self.observations = Counter()

    def observe(self, form, lemma, pos, file, record, *, typo=False):
        if not form:
            return
        key = lexical_key(form)
        if typo:
            self.typo_forms.add(key)
            self.observations["excluded_typo_observations"] += 1
            return
        if not lemma or lemma == "_":
            return
        self.observations["clean_observations"] += 1
        lemma = lexical_key(lemma)
        if key not in self.forms:
            self.forms[key] = (lemma, pos, file, record)
        else:
            previous = self.forms[key]
            if previous and previous[0] != lemma:
                self.forms[key] = None
            elif previous and previous[1] != pos:
                self.forms[key] = (lemma, None, previous[2], previous[3])

    def lookup(self, form):
        return self.forms.get(lexical_key(form))

    def reason(self, form):
        key = lexical_key(form)
        if key in self.forms:
            return "unique_lemma" if self.forms[key] else "ambiguous_form"
        return "typo_only" if key in self.typo_forms else "absent_form"

    def summary(self):
        return {"clean_observations": self.observations["clean_observations"],
                "excluded_typo_observations": self.observations["excluded_typo_observations"],
                "unique_forms": sum(value is not None for value in self.forms.values()),
                "ambiguous_forms": sum(value is None for value in self.forms.values()),
                "typo_only_forms": sum(key not in self.forms for key in self.typo_forms)}


def word_matches(text):
    return list(WORD_PATTERN.finditer(text))


def write_words(writer, namespace, sentence, local_id, text, file, record, fragments=(), matches=None,
                *, container_attribute="sentence_id", context=None):
    matches = word_matches(text) if matches is None else matches
    keys = [lexical_key(match.group()) for match in matches]
    positions = defaultdict(list)
    for index, key in enumerate(keys):
        positions[key].append(index)
    owners = [[] for _ in matches]
    for fragment in fragments:
        fragment_keys = [lexical_key(match.group()) for match in word_matches(fragment["text"])]
        if not fragment_keys:
            continue
        span = fragment.get("span")
        if span is not None:
            starts = [index for index in positions[fragment_keys[0]]
                      if matches[index].start() == span[0]]
        else:
            starts = positions[fragment_keys[0]]
        aligned = [start for start in starts if keys[start:start + len(fragment_keys)] == fragment_keys
                   and (span is None or matches[start + len(fragment_keys) - 1].end() == span[1])]
        # Repeated phrases without offsets cannot identify a particular occurrence.
        if len(aligned) != 1:
            continue
        start = aligned[0]
        end = start + len(fragment_keys)
        bounds = fragment.get("container_span", (matches[start].start(), matches[end - 1].end()))
        width = bounds[1] - bounds[0]
        for index in range(start, end):
            if not owners[index] or width < owners[index][0][0]:
                owners[index] = [(width, fragment["id"])]
            elif width == owners[index][0][0]:
                owners[index].append((width, fragment["id"]))
    for index, match in enumerate(matches):
        word_record = f"{record}/word/{match.start()}:{match.end()}"
        lemma = writer.word_index.lookup(match.group()) if writer.word_index else None
        reason = writer.word_index.reason(match.group()) if writer.word_index else "ud_unavailable"
        writer.counts[f"word_{reason}"] += 1
        attributes = {**(context or {}), container_attribute: sentence, "start": match.start(), "end": match.end(),
                      "position": index, "lemma_status": "ud_form" if lemma else "unresolved",
                      "lemma_reason": reason}
        node = writer.entity(namespace, "word_occurrence",
            f"{local_id}/word/{match.start()}:{match.end()}", match.group(), attributes,
            file, word_record, WORD_RULE)
        parents = {owner for _, owner in owners[index]} or {sentence}
        for parent in sorted(parents):
            writer.edge(parent, "text:contains_word", node, file, word_record, WORD_RULE)
        if lemma:
            value, pos, ud_file, ud_record = lemma
            writer.lexeme(node, value, file, word_record, pos, rule=LEMMA_RULE,
                          attributes={"basis": "unique_lemma_for_non_typo_ud_form", "ud_file": ud_file,
                                      "ud_record": ud_record})
            writer.evidence.append((node, "ud", ud_file, ud_record, LEMMA_RULE))


def parenthetical_spans(text):
    """Return balanced parenthesis interiors in outer-to-inner source order."""
    stack = []
    spans = []
    for position, character in enumerate(text):
        if character == "(":
            stack.append(position)
        elif character == ")" and stack:
            spans.append((stack.pop() + 1, position))
    return sorted(spans)


def write_ruwordnet_text(writer, owner, synset_id, field, text, file, record):
    """Keep titles, definitions and parenthetical context as source-local mentions."""
    if not text or not text.strip():
        return
    local_id = f"synset:{synset_id}/{field}"
    field_record = f"{record}/{field}"
    container = writer.entity("ruwordnet", "surface_fragment", local_id, text,
        {"source_entity_id": owner, "field": field, "role": "source_field", "raw": {"text": text}},
        file, field_record, RUWORDNET_TEXT_RULE)
    writer.edge(owner, f"ruwordnet:{field}_text", container, file, field_record, RUWORDNET_TEXT_RULE)
    writer.counts[f"ruwordnet_{field}_fields"] += 1
    fragments = []
    parents = []
    spans = parenthetical_spans(text)
    writer.counts["ruwordnet_unmatched_parentheses"] += text.count("(") + text.count(")") - 2 * len(spans)
    for start, end in spans:
        label = text[start:end]
        if not label.strip():
            continue
        while parents and start >= parents[-1][1]:
            parents.pop()
        parent = parents[-1][2] if parents else container
        fragment_record = f"{field_record}/parenthetical/{start}:{end}"
        fragment = writer.entity("ruwordnet", "surface_fragment",
            f"{local_id}/parenthetical/{start}:{end}", label,
            {"source_entity_id": owner, "text_container_id": container, "field": field,
             "role": "parenthetical", "start": start, "end": end, "raw": {"text": label}},
            file, fragment_record, RUWORDNET_TEXT_RULE)
        writer.edge(parent, "text:contains_fragment", fragment, file, fragment_record, RUWORDNET_TEXT_RULE)
        parents.append((start, end, fragment))
        matches = word_matches(label)
        word_span = (start + matches[0].start(), start + matches[-1].end()) if matches else (start, end)
        fragments.append({"id": fragment, "text": label, "span": word_span, "container_span": (start, end)})
        writer.counts["ruwordnet_parenthetical_fragments"] += 1
    matches = word_matches(text)
    write_words(writer, "ruwordnet", container, local_id, text, file, field_record, fragments, matches=matches,
                container_attribute="text_container_id",
                context={"source_entity_id": owner, "source_record": record, "source_field": field})
    writer.counts[f"ruwordnet_{field}_words"] += len(matches)


def write_massive_words(writer, sentence, local_id, text, annotation, file, record):
    """Keep the annotated slot boundaries, including repeated equal slot values."""
    fragments = []
    pieces = []
    end = 0
    length = 0
    for match in re.finditer(r"\[([^:\[\]]+):\s*([^\[\]]*)\]", annotation):
        prefix = annotation[end:match.start()]
        pieces.append(prefix)
        length += len(prefix)
        value = match.group(2).strip()
        fragment = writer.entity("amr", "surface_fragment", f"{local_id}/slot/{match.start()}", value,
            {"raw": {"slot_type": match.group(1).strip(), "text": value,
                     "annotation_start": match.start(), "annotation_end": match.end()}},
            file, record, "massive-slot-fragment-v1")
        writer.edge(sentence, "amr:surface_fragment", fragment, file, record, "massive-slot-fragment-v1")
        value_matches = word_matches(value)
        span = ((length + value_matches[0].start(), length + value_matches[-1].end())
                if value_matches else (None, None))
        fragments.append({"id": fragment, "text": value, "span": span})
        pieces.append(value)
        length += len(value)
        end = match.end()
    pieces.append(annotation[end:])
    clean_matches = word_matches("".join(pieces))
    text_matches = word_matches(text)
    if [lexical_key(m.group()) for m in clean_matches] == [lexical_key(m.group()) for m in text_matches]:
        offsets = {m.start(): target.start() for m, target in zip(clean_matches, text_matches)}
        ends = {m.end(): target.end() for m, target in zip(clean_matches, text_matches)}
        for fragment in fragments:
            start, end = fragment["span"]
            fragment["span"] = (offsets.get(start), ends.get(end))
    else:
        # Distinct text versions require an unambiguous phrase match.
        for fragment in fragments:
            fragment.pop("span")
    write_words(writer, "amr", sentence, local_id, text, file, record, fragments, matches=text_matches)
