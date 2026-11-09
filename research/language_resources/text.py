"""Derived word occurrences attached to the smallest aligned text fragment."""

from collections import defaultdict
import re

from .warehouse import lexical_key


WORD_PART = r"[^\W_](?:[^\W_]|[\u0300-\u036f])*"
WORD_PATTERN = re.compile(rf"{WORD_PART}(?:[-'’]{WORD_PART})*", re.UNICODE)
WORD_RULE = "smallest-text-container-v1"
LEMMA_RULE = "unambiguous-ud-form-v1"


class WordIndex:
    """One lookup per observed UD form, with ambiguous lemmas left unresolved."""

    def __init__(self):
        self.forms = {}

    def observe(self, form, lemma, pos, file, record):
        if not form or not lemma or lemma == "_":
            return
        key = lexical_key(form)
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


def word_matches(text):
    return list(WORD_PATTERN.finditer(text))


def write_words(writer, namespace, sentence, local_id, text, file, record, fragments=(), matches=None):
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
        width = matches[end - 1].end() - matches[start].start()
        for index in range(start, end):
            if not owners[index] or width < owners[index][0][0]:
                owners[index] = [(width, fragment["id"])]
            elif width == owners[index][0][0]:
                owners[index].append((width, fragment["id"]))
    for index, match in enumerate(matches):
        word_record = f"{record}/word/{match.start()}:{match.end()}"
        lemma = writer.word_index.lookup(match.group()) if writer.word_index else None
        attributes = {"sentence_id": sentence, "start": match.start(), "end": match.end(),
                      "position": index, "lemma_status": "ud_form" if lemma else "unresolved"}
        node = writer.entity(namespace, "word_occurrence",
            f"{local_id}/word/{match.start()}:{match.end()}", match.group(), attributes,
            file, word_record, WORD_RULE)
        parents = {owner for _, owner in owners[index]} or {sentence}
        for parent in sorted(parents):
            writer.edge(parent, "text:contains_word", node, file, word_record, WORD_RULE)
        if lemma:
            value, pos, ud_file, ud_record = lemma
            writer.lexeme(node, value, file, word_record, pos, rule=LEMMA_RULE,
                          attributes={"basis": "unique_lemma_for_ud_form", "ud_file": ud_file,
                                      "ud_record": ud_record})
            writer.evidence.append((node, "ud", ud_file, ud_record, LEMMA_RULE))


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
