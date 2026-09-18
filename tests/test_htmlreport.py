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
    outward = r"""\b(?:src|href|action)\s*=\s*["'](?!#|data:image/svg\+xml,)"""
    assert not re.search(outward, page)
    assert page.count("<link") == 1 and 'rel="icon" href="data:image/svg+xml,' in page
    assert "@import" not in page and "url(" not in page
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


def test_the_cards_open_what_they_count_and_the_index_sorts_by_raw_values():
    page = _page(_corpus())

    assert 'href="#files" data-filter="origin"' in page
    assert 'href="#conflicts"' in page
    assert 'class="tbl index" id="index"' in page
    assert 'data-value="1024"' in page


def test_a_copy_button_copies_the_value_shown_and_keeps_no_copy_of_its_own():
    page = _page(_corpus())

    assert '<span class="v">https://example.org/holiday.jpg</span><button class="copy"' in page
    assert "data-copy" not in page


def test_the_sections_come_in_the_order_they_are_worked_through():
    page = _page(_corpus())

    assert re.findall(r"<h2>([^<]+)</h2>", page) == [
        "Summary",
        "Key findings",
        "Files",
        "Relationships",
        "Investigative pivots",
        "File detail",
        "Conflicts",
        "Report notes",
    ]


def test_report_notes_are_brief_and_only_explain_match_bases_in_use():
    page = _page(_corpus())
    section = page.split('<section id="notes"')[1].split("</section>")[0]

    assert "how it arrived here" in section
    assert "what the file says about itself" in section
    assert "what happened to it here" in section
    assert "file bytes" in section
    assert "exact path in an external store" in section
    assert "same name and size" not in section
    assert "How a file reached the examined environment" not in section


def test_relationship_explorer_uses_the_evidence_backed_graph():
    page = _page(_corpus())
    section = page.split('<section id="relationships"')[1].split("</section>")[0]

    assert '<select id="relationship-node">' in section
    assert '<optgroup label="files">' in section
    assert '<optgroup label="domains">' in section
    assert 'data-kind="has identifier"' in section
    assert 'data-kind="origin URL"' in section
    assert 'data-kind="URL host"' in section
    assert 'data-rel-focus="domain:example.org"' in section
    assert "browser-download" in section
    assert "recorded-path" in section
    assert "URL host" in section and "derived" in section


def test_relationship_explorer_includes_authors_and_cameras_without_clustering():
    record = _file(
        "photo.jpg",
        EvidenceRecord(
            source="device-metadata",
            block="exif",
            fields={
                "Make": "NIKON",
                "Model": "Z 8",
                "BodySerialNumber": "BODY-1042",
                "Artist": "Anna Nowak",
            },
        ),
    )

    page = _page([record])

    assert 'data-kind="author"' in page
    assert 'data-kind="camera body"' in page
    assert 'data-kind="camera model"' in page
    assert '<optgroup label="people">' in page
    assert '<optgroup label="camera bodies">' in page
    assert '<optgroup label="camera models">' in page


def test_every_pivot_is_listed_with_the_files_it_was_found_in():
    page = _page(_corpus())
    panel = page.split('id="pivots-type-url"')[1].split('class="panel')[0]

    assert '<span class="v">https://example.org/holiday.jpg</span>' in panel
    assert 'href="#file-002"' in panel


def test_a_conflict_says_which_statement_is_how_much_earlier():
    assert "XMP is 72 days earlier than PDF Info" in _page(_corpus())
