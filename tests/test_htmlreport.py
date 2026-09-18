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
        "Conflicts",
        "File detail",
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
    assert '<input id="relationship-find" type="search"' in section
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


def _metadata_only() -> FileRecord:
    return _file(
        "tool.exe",
        EvidenceRecord(
            source="document-metadata",
            block="pe-header",
            tool="Example Tool 1.2",
            note="company Example Corp",
            fields={"Machine": "x64", "PDBPath": "C:\\build\\tool.pdb"},
        ),
    )


def test_a_file_with_only_metadata_gets_a_detail_block_with_every_field():
    """Metadata is something to read. Without a download record beside it the
    block used to be left out, and with it the fields were left out unless the
    report was asked for in full."""
    page = _page([_metadata_only()])
    section = page.split('<section id="detail"')[1].split("</section>")[0]

    assert '<details class="file" id="detail-001">' in section
    assert "<dt>PDBPath</dt>" in section
    assert "C:\\build\\tool.pdb" in section
    assert "<dt>Machine</dt>" in section


def _ids_and_targets(page: str) -> tuple[list[str], set[str]]:
    from html.parser import HTMLParser

    class Walk(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.ids: list[str] = []
            self.targets: set[str] = set()

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            held = dict(attrs)
            if held.get("id"):
                self.ids.append(held["id"])
            href = held.get("href") or ""
            if href.startswith("#") and len(href) > 1:
                self.targets.add(href[1:])

    walk = Walk()
    walk.feed(page)
    return walk.ids, walk.targets


def test_every_id_is_unique_and_every_internal_link_has_a_target():
    """A pivot shared by two files is listed twice - across files and under its
    type - and used to carry its anchor both times."""
    shared = "https://example.org/holiday.jpg"
    records = _corpus() + [
        _metadata_only(),
        _file("copy.jpg", EvidenceRecord(source="browser-download", url=shared)),
    ]

    page = _page(records)
    ids, targets = _ids_and_targets(page)

    assert "P01" in ids
    assert len(ids) == len(set(ids)), sorted(i for i in ids if ids.count(i) > 1)
    assert targets <= set(ids), sorted(targets - set(ids))


def test_the_print_layout_opens_every_block_and_lets_the_tables_fit_the_page():
    """A printed report used to lose the last column of the file index and the
    evidence of every relationship, and printed the controls instead."""
    page = _page(_corpus())
    printed = page.split("@media print{")[1].split("\n}\n")[0]

    assert "details:not([open])>:not(summary){display:block}" in printed
    assert ".wrap>table.index,.wrap>table.pivots,.wrap>table.relationships{min-width:0}" in printed
    assert ".rel-controls,.rel-kinds,.rel-focus{display:none!important}" in printed
    assert ".tbl.relationships td:last-child{grid-column:1/-1}" in printed
