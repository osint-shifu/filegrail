"""One file, every source, and why the verdict says what it says.

The report answers "what do we know". This answers "why should I believe it",
which is a different question and the one that decides whether a finding can be
used. It adds no data: it lays out what was already found, says which records
support each other and which do not, and draws the conclusion out loud so that a
reader can disagree with it.
"""

from __future__ import annotations

from pathlib import Path

from filegrail.explain import conclusion
from filegrail.models import FileRecord, Origin
from filegrail.reconcile import reconcile
from filegrail.report import render_explain
from filegrail.theme import Theme

PLAIN = Theme(colour=False, unicode=False, width=88)

DOWNLOAD = Origin(
    source="browser-download",
    url="https://example.org/holiday.jpg",
    tool="firefox",
    at="2026-08-24T19:02:11Z",
)
ZONE = Origin(source="windows-zone-identifier", url="https://example.org/holiday.jpg")
MIRROR = Origin(source="windows-zone-identifier", url="https://mirror.example.net/holiday.jpg")
CAMERA = Origin(
    source="device-metadata",
    tool="NIKON COOLPIX P6000",
    at="2008-10-22T16:28:39Z",
    geo="43.467448, 11.885127",
)
OPENED = Origin(source="recent-documents", tool="GIMP", note="opened by GIMP")


def _record(*origins: Origin) -> FileRecord:
    record = FileRecord(path="/case/holiday.jpg", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.extend(origins)
    return record


def _said(record: FileRecord) -> str:
    return " ".join(conclusion(record, reconcile(record)))


# --- the conclusion ----------------------------------------------------------


def test_nothing_at_all_says_so_and_points_at_doctor():
    """The advice has to name something a reader can actually type. `doctor`
    stopped being a flag when the modes became commands."""
    said = _said(_record())

    assert "nothing" in said.lower()
    assert "filegrail doctor" in said
    assert "--doctor" not in said


def test_one_record_is_described_as_uncorroborated():
    said = _said(_record(DOWNLOAD))

    assert "one" in said.lower()
    assert "corroborat" in said


def test_two_agreeing_records_are_described_as_independent():
    said = _said(_record(DOWNLOAD, ZONE))

    assert "two" in said.lower() or "2" in said
    assert "agree" in said


def test_a_conflict_is_stated_as_a_conflict():
    said = _said(_record(DOWNLOAD, MIRROR))

    assert "not agree" in said or "disagree" in said


def test_intrinsic_metadata_is_described_as_not_contesting_acquisition():
    """The distinction the whole model exists to keep."""
    said = _said(_record(DOWNLOAD, CAMERA))

    assert "earlier" in said


def test_interaction_is_never_described_as_explaining_arrival():
    said = _said(_record(OPENED))

    assert "handled" in said or "opened" in said
    assert "downloaded from" not in said


def test_a_timeline_conflict_is_called_out_in_the_conclusion():
    late = Origin(source="document-metadata", tool="Word", at="2026-09-01T10:00:00Z")

    said = _said(_record(DOWNLOAD, late))

    assert "after" in said


# --- the rendering -----------------------------------------------------------


def test_it_groups_the_sources_by_kind():
    output = render_explain(_record(DOWNLOAD, CAMERA, OPENED), theme=PLAIN)

    assert "ACQUISITION" in output
    assert "INTRINSIC" in output
    assert "INTERACTION" in output


def test_it_names_every_record_it_found():
    output = render_explain(_record(DOWNLOAD, ZONE, CAMERA), theme=PLAIN)

    assert "browser download" in output
    assert "Windows zone" in output
    assert "device metadata" in output


def test_it_shows_the_reconciliation_and_the_conclusion():
    output = render_explain(_record(DOWNLOAD, MIRROR), theme=PLAIN)

    assert "conflict" in output
    assert "CONCLUSION" in output
    assert "mirror.example.net" in output


def test_a_kind_with_no_records_gets_no_empty_heading():
    """The word still appears in the verdict state, so the heading is what is
    checked, not the word."""
    output = render_explain(_record(CAMERA), theme=PLAIN)

    headings = [line.strip() for line in output.splitlines() if "how the file reached" in line]
    assert not headings
    assert any("what the file records" in line for line in output.splitlines())


def test_it_stays_inside_the_width():
    record = _record(DOWNLOAD, MIRROR, CAMERA, OPENED)

    for width in (48, 64, 88, 110):
        output = render_explain(record, theme=Theme(colour=False, unicode=False, width=width))
        assert not [line for line in output.splitlines() if len(line) > width]


def test_the_conclusion_says_when_the_two_self_descriptions_contradict():
    """`does not contest the record above` is true of an acquisition record and
    silent about the thing that is actually contested here: the file's own two
    accounts of who made it."""
    record = FileRecord(path="/case/contested.jpg", size=494, mtime="2026-08-24T19:00:00Z")
    record.origins.append(
        Origin(source="iptc", block="iptc", fields={"By-line": "Francisco Gonzalez"})
    )
    record.origins.append(Origin(source="xmp", block="xmp", fields={"dc:creator": "Marta Nowak"}))

    output = render_explain(record, theme=Theme(colour=False, unicode=False, width=88))

    assert "contested attribution" in output
    assert "attribution_conflict" in output  # the kind, whole, not clipped
    assert "does not contest" not in output
    assert "disagree about" in output
    assert "IPTC" in output


def test_the_conclusion_does_not_rank_a_pdf_info_block_against_its_xmp():
    """IIM and EXIF go stale because an editor rewrites the XMP and copies them
    through untouched. A PDF is the other way about as often as not: an exporter
    stamps a fresh Info dictionary at export while carrying the XMP through from
    the source document, which is what the corpus file shows - XMP from February,
    Info from May. Naming the Info as the likelier to be stale would state the
    opposite of what happened."""
    record = FileRecord(path="/case/export.pdf", size=494, mtime="2026-08-24T19:00:00Z")
    record.origins.append(
        Origin(
            source="document-metadata",
            block="pdf-info",
            fields={"Creator": "Adobe InDesign CC 13.1"},
        )
    )
    record.origins.append(
        Origin(source="xmp", block="xmp", fields={"xmp:CreatorTool": "Adobe Illustrator CC 22.0"})
    )

    said = " ".join(
        render_explain(record, theme=Theme(colour=False, unicode=False, width=88)).split()
    )

    assert "disagree about Creator" in said
    assert "PDF Info is the likelier" not in said
    assert "neither is reliably the older" in said


def test_the_conclusion_names_the_blocks_that_actually_disagree():
    """A camera's tags and their XMP mirror contradict each other in the same
    way IIM and XMP do, and the reasoning is the same - but a conclusion that
    talks about the IPTC block of a file that has none is telling the reader
    about a piece of evidence that is not there."""
    record = FileRecord(path="/case/tampered.jpg", size=494, mtime="2026-08-24T19:00:00Z")
    record.origins.append(
        Origin(source="device-metadata", block="exif", fields={"Model": "Canon PowerShot G9"})
    )
    record.origins.append(Origin(source="xmp", block="xmp", fields={"tiff:Model": "NIKON D700"}))

    output = render_explain(record, theme=Theme(colour=False, unicode=False, width=88))

    assert "disagree about Model" in output
    assert "device metadata" in output
    assert "IPTC" not in output


def test_every_heading_is_uppercase_in_explain_and_compare():
    """The same reasoning as the scan report: without colour a heading has only
    its letters and its position left to distinguish it from body text, and a
    report read from a file has no colour."""
    from filegrail.compare import compare
    from filegrail.report import render_compare

    record = _record(DOWNLOAD, CAMERA, OPENED)
    explained = render_explain(record, theme=PLAIN)
    for heading in ("ACQUISITION", "RECONCILIATION", "CONCLUSION"):
        assert f"\n  {heading}" in explained, heading

    other = _record(DOWNLOAD, CAMERA)
    compared = render_compare(record, other, compare(record, other), theme=PLAIN)
    for heading in ("IDENTICAL", "ARRIVED BY", "ASSESSMENT"):
        assert f"\n  {heading}" in compared, heading


# --- what explain answers first -----------------------------------------------

NARROW = Theme(colour=False, unicode=False, width=72)


def test_the_conclusion_comes_before_the_evidence():
    """The command exists to answer *why does filegrail say this*. Putting the
    answer under everything it rests on makes the reader scroll for it."""
    output = render_explain(_record(DOWNLOAD, CAMERA, OPENED), theme=PLAIN)

    lines = output.splitlines()
    said = next(i for i, line in enumerate(lines) if line.startswith("  CONCLUSION"))
    evidence = next(i for i, line in enumerate(lines) if line.startswith("  ACQUISITION"))

    assert said < evidence


def test_the_state_of_the_evidence_is_stated_before_it_is_shown():
    output = render_explain(_record(DOWNLOAD, CAMERA, OPENED), theme=PLAIN)

    state = "\n".join(
        line for line in output.splitlines() if line.startswith("    ") and "record" in line
    )
    assert "acquisition" in state
    assert "intrinsic" in state
    assert "interaction" in state


def test_a_class_with_nothing_in_it_says_so_rather_than_vanishing():
    """An absent class is a fact about the file, not a gap in the report."""
    output = render_explain(_record(CAMERA), theme=PLAIN)

    assert "acquisition none" in " ".join(output.split())


def test_an_address_is_not_broken_in_the_middle_of_itself(tmp_path: Path):
    """A URL used to share a line with the source name and the strength, which
    left it a third of the terminal. Anything longer broke inside a token, and
    an address the report cut in half is one nothing can open or grep for."""
    long_url = "https://portal.example.org/press/2026/holiday-master.jpg"
    record = _record(Origin(source="browser-download", url=long_url, tool="firefox"))

    output = render_explain(record, theme=NARROW)

    assert long_url in output


def test_a_claim_carries_the_same_meter_the_scan_shows():
    """One vocabulary for strength across the two reports, or a reader has to
    learn that `direct` here and four bars there are the same statement."""
    output = render_explain(_record(DOWNLOAD), theme=Theme(colour=False, unicode=True, width=88))

    headline = next(line for line in output.splitlines() if line.startswith("  ←"))
    assert "▰" in headline
    assert headline.rstrip().endswith("direct")
