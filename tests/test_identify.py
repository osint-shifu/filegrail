"""Identifiers pulled out of what a scan read.

The corpus is what files record about themselves - an author line, a company, a
template path, a producing URL, a GPS fix - which is where the identifiers a
document body never mentions actually live. Document text is the second corpus,
off unless asked for, and the tests at the end of this file are about keeping
the two apart.
"""

from __future__ import annotations

import json
from pathlib import Path

from filegrail.identify import (
    PLACE,
    extract,
    find_coordinates,
    normalize_domain,
    normalize_url,
)
from filegrail.models import FileRecord, Origin
from filegrail.report import render_json, render_text
from filegrail.theme import Theme

PLAIN = Theme(colour=False, unicode=False, width=88)


def _record(name: str, **origin) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
    record.origins.append(Origin(**origin))
    return record


# --- the ported detectors ----------------------------------------------------


def test_an_unknown_tld_is_not_a_domain():
    assert normalize_domain("example.org") == "example.org"
    assert normalize_domain("report.finaldraft") is None


def test_a_url_normalises_to_scheme_host_path():
    assert normalize_url("https://Example.ORG/a/b/?q=1") == (
        "https://example.org/a/b?q=1",
        "example.org",
    )


def test_a_malformed_port_does_not_raise():
    assert normalize_url("http://localhost:1420$") is None


def test_a_bare_decimal_pair_is_not_a_coordinate():
    """An SVG path and a version tuple look exactly like one."""
    assert find_coordinates("43.467448, 11.885127") == []


def test_a_hemisphere_letter_makes_it_a_coordinate():
    found = find_coordinates("43.467448 N, 11.885127 E")

    assert len(found) == 1
    assert round(found[0][1], 4) == 43.4674


def test_null_island_is_rejected():
    assert find_coordinates("0.0 N, 0.0 E") == []


# --- over a scan's own metadata ---------------------------------------------


def test_an_email_in_a_document_author_is_found():
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    found = extract(records)

    assert [(i.type, i.normalized) for i in found if i.type == "email"] == [("email", "a@b.org")]


def test_the_field_it_came_from_is_recorded():
    """An identifier without its source is a lead nobody can check."""
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    email = next(i for i in extract(records) if i.type == "email")

    assert "report.pdf" in email.where[0]
    assert "Author" in email.where[0]


def test_the_same_value_across_files_is_one_identifier():
    records = [
        _record("a.pdf", source="document-metadata", fields={"Author": "a@b.org"}),
        _record("b.pdf", source="document-metadata", fields={"creator": "A@B.ORG"}),
    ]

    email = next(i for i in extract(records) if i.type == "email")

    assert email.files == 2
    assert email.count == 2


def test_a_url_origin_yields_its_domain():
    records = [_record("x.zip", source="browser-download", url="https://portal.example.org/a")]

    kinds = {i.type for i in extract(records)}

    assert "url" in kinds
    assert "domain" in kinds


def test_a_command_is_searched_too():
    records = [
        _record("r.csv", source="shell-history", command="curl -o r.csv https://api.example.org/x")
    ]

    # The full host, not the registrable domain: a subdomain is a pivot in its
    # own right and can always be truncated later.
    assert any(i.normalized == "api.example.org" for i in extract(records))


def test_a_private_address_is_flagged():
    records = [_record("log.txt", source="document-metadata", fields={"Host": "192.168.1.10"})]

    address = next(i for i in extract(records) if i.type == "ipv4")

    assert address.private is True


def test_a_version_string_is_not_an_address():
    records = [_record("a.pdf", source="document-metadata", fields={"Producer": "Tool v1.2.3.4"})]

    assert not [i for i in extract(records) if i.type == "ipv4"]


def test_a_version_in_a_software_field_is_not_an_address():
    """`LibreOffice/24.2.7.2` is the single most common string in this corpus,
    and nothing about its shape distinguishes it from an address - only the
    field it sits in does."""
    records = [
        _record("a.odt", source="document-metadata", tool="LibreOffice/24.2.7.2$Linux_X86_64"),
        _record("b.pdf", source="document-metadata", fields={"Producer": "LibreOffice 25.2.3.2"}),
    ]

    assert not [i for i in extract(records) if i.type == "ipv4"]


def test_a_build_hash_in_a_software_field_is_not_evidence():
    records = [
        _record(
            "a.ods",
            source="document-metadata",
            tool="LibreOffice_project/c838ef25c16710f8838b1faec480ebba495259d0",
        )
    ]

    assert not [i for i in extract(records) if i.type == "sha1"]


def test_an_address_in_an_ordinary_field_is_still_found():
    """The suppression is per field, not global."""
    records = [_record("log.txt", source="document-metadata", fields={"Host": "203.0.113.7"})]

    assert [i.normalized for i in extract(records) if i.type == "ipv4"] == ["203.0.113.7"]


def test_nothing_found_is_an_empty_list():
    assert extract([_record("a.txt", source="filesystem")]) == []


# --- through the report ------------------------------------------------------


def test_the_identifier_section_is_absent_unless_asked_for():
    """The field itself is on screen by default; the cross-file roll-up is not."""
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    assert "identifiers" not in render_text(records, Path("/case"), theme=PLAIN)


def test_the_report_lists_them_on_request():
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    output = render_text(records, Path("/case"), theme=PLAIN, identify=True)

    assert "a@b.org" in output
    assert "email" in output


def test_json_carries_them_on_request():
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    payload = json.loads(render_json(records, Path("/case"), identify=True))

    emails = [i for i in payload["identifiers"] if i["type"] == "email"]
    assert emails[0]["normalized"] == "a@b.org"
    assert emails[0]["where"] == ["report.pdf · Author"]


def test_json_omits_them_otherwise():
    records = [_record("report.pdf", source="document-metadata", fields={"Author": "a@b.org"})]

    assert "identifiers" not in json.loads(render_json(records, Path("/case")))


def test_a_namespaced_software_field_is_still_a_software_field():
    """XMP names the same property `pdf:Producer`, and adds version fields of
    its own. A dotted quad is no more an address for having a namespace in front
    of the field it sits in."""
    records = [
        _record("a.pdf", source="xmp", fields={"pdf:Producer": "LibreOffice 25.2.3.2"}),
        _record("b.jpg", source="xmp", fields={"exif:GPSVersionID": "2.2.0.0"}),
    ]

    assert not [entry for entry in extract(records) if entry.type == "ipv4"]


def test_a_message_id_is_not_offered_as_an_address():
    """RFC 5322 builds a message id the same shape as a mailbox, so it matches
    every test for one. Nobody can write to it, and a lead nobody can follow is
    worse than no lead - the field name is known here, so it can be told."""
    record = FileRecord(path="/case/note.eml", size=10, mtime="")
    record.origins.append(
        Origin(
            source="email-header",
            fields={
                "Message-ID": "<20190304182228.7ttQ1a@example.com>",
                "From": "Jan Kowalski <jan@example.com>",
            },
        )
    )

    found = {(identifier.type, identifier.normalized) for identifier in extract([record])}

    assert ("email", "jan@example.com") in found
    assert not [value for kind, value in found if kind == "email" and "7ttq1a" in value]


# --- the second corpus --------------------------------------------------------
#
# `--content` widens what is searched from what files record about themselves to
# what they say. The two are kept apart on every entry: prose is an order of
# magnitude noisier than a property field, and a reader has to be able to tell a
# name somebody typed into a letter from a name a download record carried.


def _document(tmp_path: Path, text: str, name: str = "letter.txt", **origin: object) -> FileRecord:
    """A real file on disk, because reading content means opening it."""
    written = tmp_path / name
    written.write_text(text, encoding="utf-8")
    record = FileRecord(
        path=str(written), size=written.stat().st_size, mtime="2026-08-24T19:00:00Z"
    )
    if origin:
        record.origins.append(Origin(**origin))
    return record


def test_the_corpus_is_still_only_metadata_unless_asked(tmp_path: Path):
    """Every existing scan pays nothing for this and reports nothing from it."""
    record = _document(tmp_path, "write to ann.shaw@acme-legal.example", source="document-metadata")

    assert extract([record]) == []


def test_content_widens_the_corpus_to_what_the_document_says(tmp_path: Path):
    record = _document(tmp_path, "write to ann.shaw@acme-legal.example", source="document-metadata")

    found = extract([record], content=True)

    assert [entry.normalized for entry in found if entry.type == "email"] == [
        "ann.shaw@acme-legal.example"
    ]
    assert [entry.corpora for entry in found if entry.type == "email"] == [{"content"}]


def test_a_value_from_a_document_says_where_in_the_document_it_was(tmp_path: Path):
    """An identifier reported as `notes.txt` sends somebody back to search the
    file. One reported as `notes.txt - line 3` does not."""
    record = _document(
        tmp_path,
        "nothing here\nnor here\nwrite to ann.shaw@acme-legal.example\n",
        name="notes.txt",
        source="document-metadata",
    )

    email = next(e for e in extract([record], content=True) if e.type == "email")

    assert email.where == [f"notes.txt{PLACE}line 3"]


def test_a_value_written_in_a_document_and_recorded_about_it_says_both(tmp_path: Path):
    """Two separate acts put it there, and neither half says that alone."""
    record = _document(
        tmp_path,
        "write to ann.shaw@acme-legal.example",
        source="document-metadata",
        fields={"Author": "ann.shaw@acme-legal.example"},
    )

    email = next(e for e in extract([record], content=True) if e.type == "email")

    assert email.corpora == {"metadata", "content"}
    assert email.count == 2


def test_a_value_the_document_names_and_the_arrival_record_names_is_marked(tmp_path: Path):
    """The whole reason for reading content: the body and the download agree."""
    record = _document(
        tmp_path,
        "invoice from acme-legal.example",
        source="browser-download",
        url="https://acme-legal.example/invoice.pdf",
    )

    found = extract([record], content=True)
    domain = next(entry for entry in found if entry.normalized == "acme-legal.example")

    assert domain.acquired is True
    assert domain.corpora == {"metadata", "content"}


def test_a_value_only_a_document_claims_about_itself_is_not_an_arrival(tmp_path: Path):
    """An intrinsic field travelled with the bytes; it does not say they arrived."""
    record = _document(
        tmp_path,
        "invoice from acme-legal.example",
        source="document-metadata",
        fields={"Company": "acme-legal.example"},
    )

    found = extract([record], content=True)
    domain = next(entry for entry in found if entry.normalized == "acme-legal.example")

    assert domain.acquired is False


def test_the_document_carries_the_corpus_of_every_identifier(tmp_path: Path):
    record = _document(
        tmp_path,
        "invoice from acme-legal.example",
        source="browser-download",
        url="https://acme-legal.example/invoice.pdf",
    )

    payload = json.loads(render_json([record], tmp_path, identify=True, content=True))
    domain = next(e for e in payload["identifiers"] if e["normalized"] == "acme-legal.example")

    assert domain["corpora"] == ["content", "metadata"]
    assert domain["acquired"] is True


def test_the_report_says_which_side_of_the_file_a_value_came_from(tmp_path: Path):
    # Two files, because the section that raises this only runs for a directory:
    # a report about one file has nothing to bury it under.
    records = [
        _document(
            tmp_path,
            "invoice from acme-legal.example",
            name="invoice.txt",
            source="browser-download",
            url="https://acme-legal.example/invoice.pdf",
        ),
        _document(
            tmp_path,
            "write to ann.shaw@other.example",
            name="notes.txt",
            source="document-metadata",
        ),
        _document(
            tmp_path,
            "not read, this is not a text format",
            name="holiday.jpg",
            source="device-metadata",
            fields={"Company": "third.example"},
        ),
    ]

    printed = " ".join(
        render_text(records, tmp_path, identify=True, content=True, theme=PLAIN).split()
    )

    assert "1 identifier is named in a document and in how it arrived" in printed
    # One word per side of the file, and the three cases are distinguishable.
    assert "acme-legal.example both" in printed
    assert "other.example text" in printed
    assert "third.example recorded" in printed


def test_the_report_has_no_corpus_column_when_there_is_one_corpus(tmp_path: Path):
    """A column saying the same word on every row is noise, not information."""
    record = _document(
        tmp_path,
        "nothing here",
        source="browser-download",
        url="https://acme-legal.example/invoice.pdf",
    )

    printed = " ".join(render_text([record], tmp_path, identify=True, theme=PLAIN).split())

    assert "acme-legal.example" in printed
    assert "recorded" not in printed
    assert "named in a document" not in printed
