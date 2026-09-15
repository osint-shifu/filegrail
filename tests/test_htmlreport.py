"""The investigation report as a page: dark, self-contained, and unable to say
anything to anybody by being opened.

A file's metadata is untrusted input. A name or a field that carries markup has
to arrive in the page as text, and nothing in the page may reach outside it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from filegrail.analysis import analyse
from filegrail.htmlreport import render_html
from filegrail.identify import extract
from filegrail.models import EvidenceRecord, FileRecord

ROOT = Path("/case")
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=timezone.utc)


def _file(name: str, *evidence: EvidenceRecord, size: int = 1024) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=size, mtime="2026-01-01T00:00:00Z")
    record.evidence.extend(evidence)
    return record


def _corpus() -> list[FileRecord]:
    contested = _file(
        "report.pdf",
        EvidenceRecord(
            source="document-metadata",
            block="pdf-info",
            fields={"Creator": "Adobe InDesign", "CreationDate": "D:20180511143720-04'00'"},
        ),
        EvidenceRecord(
            source="xmp",
            block="xmp",
            fields={
                "xmp:CreatorTool": "Adobe Illustrator",
                "xmp:CreateDate": "2018-02-28T13:44:18-05:00",
            },
        ),
    )
    download = _file(
        "press/holiday.jpg",
        EvidenceRecord(source="browser-download", url="https://example.org/holiday.jpg"),
    )
    return [contested, download, _file("notes.md")]


def _page(records: list[FileRecord], **options: object) -> str:
    found = extract(records)
    case = analyse(records, ROOT, identifiers=found)
    return render_html(case, identifiers=found, now=NOW, **options)  # type: ignore[arg-type]


def test_the_page_is_dark_self_contained_and_reaches_nothing_outside_itself():
    page = _page(_corpus())

    assert page.startswith("<!doctype html>")
    assert "color-scheme:dark" in page
    assert "default-src 'none'" in page
    assert "@media print" in page
    assert not re.search(r"""\b(?:src|href|action)\s*=\s*["'](?!#)""", page)
    assert "<link" not in page and "@import" not in page and "url(" not in page
    assert "https://example.org/holiday.jpg" in page


def test_every_value_that_came_out_of_a_file_is_escaped():
    hostile = "<script>alert(1)</script>"
    record = _file(
        f"{hostile}.pdf",
        EvidenceRecord(
            source="document-metadata",
            block="pdf-info",
            fields={"Author": hostile, "Title": '"><img src=x onerror=alert(1)>'},
        ),
    )

    page = _page([record], verbose=True)

    assert "<script>alert" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_the_numbers_are_anchors_and_the_references_lead_to_them():
    page = _page(_corpus())

    for anchor in ('id="file-001"', 'id="F01"', 'id="C01"'):
        assert anchor in page
    assert 'href="#C01"' in page
    assert 'href="#file-001"' in page
