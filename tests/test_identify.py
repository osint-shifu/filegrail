"""Identifiers pulled out of the metadata a scan already read.

The corpus here is not document text. It is what files record about themselves -
an author line, a company, a template path, a producing URL, a GPS fix - which
is where the identifiers a document body never mentions actually live.
"""

from __future__ import annotations

import json
from pathlib import Path

from filetrail.identify import extract, find_coordinates, normalize_domain, normalize_url
from filetrail.models import FileRecord, Origin
from filetrail.report import render_json, render_text
from filetrail.theme import Theme

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
