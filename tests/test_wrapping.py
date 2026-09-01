"""Nothing in the report is truncated, and nothing is hidden behind a flag.

A provenance report is read to find things out. A value cut off at an ellipsis
is a value the reader now has to go and fetch another way, which defeats the
point of having read the file at all - so long values wrap, and every field a
reader decoded is on screen without asking for it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from filetrail.lineage import Link
from filetrail.models import FileRecord, Origin
from filetrail.report import render_text
from filetrail.theme import Theme

WIDTHS = [48, 56, 64, 80, 88, 110]

LONG_TOOL = "EASTMAN KODAK COMPANY KODAK CX7530 ZOOM DIGITAL CAMERA (processed with GIMP 2.4.5)"
LONG_URL = "https://portal.example.org/" + "billing-department/" * 6 + "invoice-scan.pdf"


def _record(name: str = "photo.jpg", **origin) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.append(Origin(**origin))
    return record


def _plain(width: int = 88) -> Theme:
    return Theme(colour=False, unicode=True, width=width)


#: One glyph each. The ASCII arrow is two characters and has to be removed as a
#: token: listing it character by character puts `-` in the set, which then eats
#: the leading hyphen off every wrapped continuation line.
GUTTER = "●←│├└*|+\\"
GUTTER_TOKENS = ("<-",)


def _flat(output: str) -> str:
    """The report with its gutter and all whitespace removed.

    A value the report wrapped is contiguous again here, which is the only way
    to assert that nothing was lost without asserting where the breaks landed.
    """
    kept = []
    for line in output.splitlines():
        body = line.strip()
        for token in GUTTER_TOKENS:
            if body.startswith(token):
                body = body[len(token) :].strip()
        # `body[:1] in GUTTER` would be True for the empty string, which is how
        # this loop first ran forever on a blank line.
        while body and body[0] in GUTTER:
            body = body[1:].strip()
        kept.append(body)
    return "".join("".join(part.split()) for part in kept)


# --- nothing is cut off ------------------------------------------------------


@pytest.mark.parametrize("width", WIDTHS)
def test_a_long_tool_name_survives_intact(width: int):
    record = _record(source="device-metadata", tool=LONG_TOOL)

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert "".join(LONG_TOOL.split()) in _flat(output)


@pytest.mark.parametrize("width", WIDTHS)
def test_a_long_url_survives_intact(width: int):
    record = _record(source="browser-download", url=LONG_URL)

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert LONG_URL in _flat(output)


@pytest.mark.parametrize("width", WIDTHS)
def test_a_long_field_value_survives_intact(width: int):
    value = "a-very-long-value-" * 8
    record = _record(source="document-metadata", tool="Word", fields={"Keywords": value})

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert value in _flat(output)


@pytest.mark.parametrize("width", WIDTHS)
def test_wrapping_still_respects_the_width(width: int):
    record = _record(source="device-metadata", tool=LONG_TOOL, fields={"Note": LONG_URL})

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert not [line for line in output.splitlines() if len(line) > width]


@pytest.mark.parametrize("width", WIDTHS)
def test_a_long_list_of_related_files_wraps_rather_than_overflows(width: int):
    """Every path in a lineage link is a file the reader may have to go and
    open. None of them may be cut, and none may push the entry past the edge."""
    record = _record(source="device-metadata", tool="Canon")
    record.links = [
        Link(
            kind="derived from",
            others=tuple(f"/case/a-rather-long-export-name-{n}.jpg" for n in range(4)),
            count=4,
        )
    ]

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert not [line for line in output.splitlines() if len(line) > width]
    for n in range(4):
        assert f"a-rather-long-export-name-{n}.jpg" in _flat(output)


def test_a_long_file_name_is_not_cut():
    name = "a-deeply-descriptive-file-name-that-keeps-going-and-going.jpg"
    record = _record(name, source="device-metadata", tool="Canon")

    output = render_text([record], Path("/case"), theme=_plain(64))

    # The size column shares the first line, so the name cannot simply be
    # reassembled; that both ends survived is what the test is really about.
    assert "…" not in output
    assert "a-deeply-descriptive" in output
    assert "going.jpg" in output


# --- everything is on screen -------------------------------------------------


def test_fields_are_shown_without_asking():
    record = _record(
        source="device-metadata",
        tool="NIKON",
        fields={"BodySerialNumber": "3001234", "GPSDateStamp": "2008:10:23"},
    )

    output = render_text([record], Path("/case"), theme=_plain())

    assert "BodySerialNumber" in output
    assert "3001234" in output
    assert "GPSDateStamp" in output


def test_brief_puts_them_away_again():
    """The summary view still exists for anyone scanning a large tree."""
    record = _record(source="device-metadata", tool="NIKON", fields={"BodySerialNumber": "3001"})

    output = render_text([record], Path("/case"), theme=_plain(), brief=True)

    assert "BodySerialNumber" not in output
    assert "NIKON" in output


def test_the_field_block_reads_as_a_tree():
    record = _record(source="device-metadata", tool="NIKON", fields={"A": "1", "B": "2"})

    output = render_text([record], Path("/case"), theme=_plain())

    assert "├" in output
    assert "└" in output


def test_the_last_field_closes_the_tree():
    record = _record(source="device-metadata", tool="NIKON", fields={"A": "1", "Zed": "2"})

    lines = [line for line in render_text([record], Path("/case"), theme=_plain()).splitlines()]
    branches = [line for line in lines if line.lstrip().startswith(("├", "└"))]

    assert branches[-1].lstrip().startswith("└")
    assert all(line.lstrip().startswith("├") for line in branches[:-1])


def test_the_ascii_tree_has_no_box_drawing():
    record = _record(source="device-metadata", tool="NIKON", fields={"A": "1", "B": "2"})

    output = render_text([record], Path("/case"), theme=Theme(False, False, 88))

    assert output.isascii()
