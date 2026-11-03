"""Compare generated OOXML with the approved September report and audit inputs."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from pypdf import PdfReader

from analyze import ROOT, audit


def validate():
    audit()
    path = ROOT / 'output/ruMTEB_23_обоснованность.docx'
    expected = json.loads((ROOT / 'data/provenance.json').read_text(encoding='utf-8'))
    with ZipFile(path) as archive:
        parts = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(archive.namelist())}
    assert parts == expected['reference_ooxml_parts_sha256'], 'Generated report differs from the approved September OOXML'
    doc = Document(path)
    assert len(doc.tables) == 2
    assert [len(table.rows) for table in doc.tables] == [24, 5]
    rendered = ROOT / 'output/render/ruMTEB_23_обоснованность.pdf'
    result = dict(ooxml_exact_match=True, table_rows=[24, 5], snapshot_date=expected['snapshot_date'])
    if rendered.exists():
        pdf = PdfReader(rendered)
        assert len(pdf.pages) == 3
        result['rendered_pages'] = 3
    (ROOT / 'output/validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    validate()
