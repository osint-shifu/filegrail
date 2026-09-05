"""Nothing in the report is truncated, and nothing is hidden behind a flag.

A provenance report is read to find things out. A value cut off at an ellipsis
is a value the reader now has to go and fetch another way, which defeats the
point of having read the file at all - so long values wrap, and every field a
reader decoded is on screen without asking for it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from filegrail.lineage import Link
from filegrail.models import FileRecord, Origin
from filegrail.report import render_text, render_timeline
from filegrail.theme import Theme

WIDTHS = [48, 56, 64, 72, 80, 88, 110]

#: The right-aligned timestamp column, which shares a line with the name beside
#: it and has to be removed before that name can be reassembled.
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

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


def _survives(name: str, flattened: str) -> bool:
    """Whether a path survived wrapping, whichever separator the platform uses.

    Both sides lose their separators before they are compared. The report
    prints a path the way the host spells it, and on Windows that is the same
    character the ASCII gutter uses for `└` - so a wrapped path cannot be
    reassembled with the separators left in.
    """
    stripped = flattened.replace("\\", "").replace("/", "")
    return name.replace("/", "") in stripped


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


# --- the names of things are data too ----------------------------------------

LONG_FIELD = "xmpMM:DerivedFrom/stRef:originalDocumentID"


@pytest.mark.parametrize("width", WIDTHS)
def test_a_long_field_name_survives_intact(width: int):
    """A field name is half of what a field says. `xmpMM:DerivedFrom/stRef…`
    four times over is four rows the reader cannot tell apart, and the value
    beside each of them is then unattributable."""
    record = _record(source="xmp", tool="Illustrator", fields={LONG_FIELD: "xmp.did:1234"})

    output = render_text([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert LONG_FIELD in _flat(output)
    assert "xmp.did:1234" in _flat(output)


def test_field_names_that_differ_late_stay_distinguishable():
    """The real case: four XMP names sharing a thirty-character prefix."""
    fields = {f"xmpMM:DerivedFrom/stRef:{tail}": tail for tail in ("documentID", "instanceID")}
    record = _record(source="xmp", tool="Illustrator", fields=fields)

    flat = _flat(render_text([record], Path("/case"), theme=_plain(88)))

    for name in fields:
        assert name in flat, name


@pytest.mark.parametrize("width", WIDTHS)
def test_a_file_with_no_findings_keeps_its_whole_name(width: int):
    """It is a list of open questions. A name cut short is a question the
    reader cannot go and answer."""
    name = "isamples/ark_28722_k27w68z78metadata-E555826E-42A5-4293-3B0A-0C76553A9B53.json"
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")

    other = _record(source="device-metadata", tool="Canon")

    output = render_text([record, other], Path("/case"), theme=_plain(width))

    # The timestamp is right-aligned on the name's first line, so it has to come
    # out before the wrapped halves of the name are contiguous again.
    assert "…" not in output
    assert _survives(name, _flat(_STAMP.sub("", output)))


@pytest.mark.parametrize("width", WIDTHS)
def test_an_identifier_is_not_cut_to_fit_its_column(width: int):
    """An identifier is what somebody pivots on next. Half of one is nothing."""
    address = "a-very-long-mailbox-name-indeed@subdomain.department.example.org"
    record = _record(source="document-metadata", tool="Word", fields={"Author": address})

    output = render_text([record], Path("/case"), theme=_plain(width), identify=True)

    assert "…" not in output
    assert address in _flat(output)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_timeline_does_not_cut_a_name_or_a_claim(width: int):
    """`--timeline` is the same evidence in a different order, held to the same
    rule as the report it came from."""
    name = "a-deeply-descriptive-file-name-that-keeps-going-and-going.jpg"
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
    record.origins.append(
        Origin(source="browser-download", url=LONG_URL, at="2026-08-24T19:02:11Z")
    )

    output = render_timeline([record], Path("/case"), theme=_plain(width))

    assert "…" not in output
    assert name in _flat(output)
    assert LONG_URL in _flat(output)
    assert not [line for line in output.splitlines() if len(line) > width]


def test_an_absurd_extension_is_named_in_full_and_stays_inside_the_terminal():
    """An extension is data like anything else. It is not cut to keep the grid,
    and it does not push the grid past the edge of the terminal either."""
    absurd = "backup-2026-08-24T19-02-11Z-part0001"
    records = [
        FileRecord(path=f"/case/a.{absurd}", size=10, mtime="2026-08-24T19:00:00Z"),
        _record("b.pdf", source="document-metadata", tool="Word"),
    ]

    output = render_text(records, Path("/case"), theme=_plain(48))

    assert "…" not in output
    assert absurd.upper() in _flat(output)
    assert not [line for line in output.splitlines() if len(line) > 48]


def test_a_name_that_fits_the_line_is_not_split_by_the_timestamp_beside_it():
    """Splitting `...9B53.xml` into `...9B53.x` and `ml` to keep a timestamp
    company is the layout winning an argument it should not have had. The name
    takes the width and the timestamp follows it."""
    name = "isamples/ark_28722_k27w68z78metadata-E555826E-42A5-4293-3B0A-0C76553A9B53.xml"
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
    other = _record(source="device-metadata", tool="Canon")

    output = render_text([record, other], Path("/case"), theme=_plain(100))

    shown = str(Path(name))  # the report prints it the way the platform spells it
    assert any(shown in line for line in output.splitlines()), "the name was broken up"
    assert not [line for line in output.splitlines() if len(line) > 100]
