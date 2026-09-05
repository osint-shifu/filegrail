from pathlib import Path

import pytest

from filegrail import TAGLINE, __version__
from filegrail.models import FileRecord, Origin
from filegrail.report import render_text, render_timeline
from filegrail.theme import Theme

#: Deterministic rendering for assertions: no colour, no box drawing.
PLAIN = Theme(colour=False, unicode=False, width=88)


def _record(name: str, origin: Origin | None = None) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
    if origin is not None:
        record.origins.append(origin)
    return record


def _listed(output: str) -> int:
    """How many unexplained files the report actually named."""
    return sum(
        1
        for line in output.splitlines()
        if line.strip().startswith("f") and line.strip().split()[0].endswith(".txt")
    )


def test_unknown_list_is_capped(tmp_path: Path):
    records = [_record(f"f{index}.txt") for index in range(40)]

    output = render_text(records, Path("/case"), limit=5, theme=PLAIN)

    assert "... and 35 more" in output
    assert _listed(output) == 5


def test_no_cap_message_when_everything_fits():
    output = render_text([_record("a.txt"), _record("b.txt")], Path("/case"), limit=25)
    assert "more (--json" not in output


def test_zero_matches_explains_why():
    records = [_record("a.txt")]
    stats = {"browser_profiles": 4, "browser_records": 17}

    output = render_text(records, Path("/case"), stats=stats, theme=PLAIN)

    assert "1 file analyzed" in output
    assert "0 with findings" in output
    assert "17 download records across 4 browser profiles" in output
    assert "prune download history" in output


def test_zero_matches_with_no_readable_profile():
    stats = {"browser_profiles": 0, "browser_records": 0}

    output = render_text([_record("a.txt")], Path("/case"), stats=stats, theme=PLAIN)

    assert "No browser profile was readable" in output


def test_singular_wording():
    stats = {"browser_profiles": 1, "browser_records": 1}
    output = render_text([_record("a.txt")], Path("/case"), stats=stats, theme=PLAIN)
    assert "1 download record across 1 browser profile" in output


def test_no_explanation_when_something_matched():
    found = _record("a.txt", Origin(source="browser-download", url="https://example.org/a"))
    stats = {"browser_profiles": 1, "browser_records": 1}

    output = render_text([found], Path("/case"), stats=stats, theme=PLAIN)

    assert "prune download history" not in output
    assert "1 file analyzed" in output
    assert "1 with findings" in output


def test_limit_zero_lists_everything():
    records = [_record(f"f{index}.txt") for index in range(40)]

    output = render_text(records, Path("/case"), limit=0, theme=PLAIN)

    assert "more (--limit 0" not in output
    assert _listed(output) == 40


def test_document_metadata_without_a_tool_reports_the_date_it_found():
    origin = Origin(source="document-metadata", at="2026-07-20T19:05:21Z")
    record = _record("invoice.pdf", origin)

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "self-reported creation date" in output
    assert "self-reported metadata" not in output


def test_document_metadata_with_a_tool_says_what_made_it():
    origin = Origin(source="document-metadata", tool="Typst 0.14.2", at="2026-07-07T14:41:23Z")

    output = render_text([_record("spec.pdf", origin)], Path("/case"), theme=PLAIN)

    assert "made by Typst 0.14.2" in output


def test_a_dateless_xmp_packet_does_not_borrow_the_file_s_own_timestamp():
    """The report supplies a file's creation time for a claim that carries none,
    which is right for a download record and wrong here: a packet that names no
    date must not be shown appearing to claim one."""
    record = FileRecord(
        path="/case/photo.jpg",
        size=1,
        mtime="2026-08-24T19:00:00Z",
        btime="2023-06-01T08:00:00Z",
    )
    record.origins.append(Origin(source="xmp", tool="darktable 4.6.1", fields={"xmp:Rating": "3"}))

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "darktable 4.6.1" in output
    assert "2023-06-01" not in output


def test_an_edit_step_does_not_claim_the_editor_made_the_file():
    """xmpMM:History records what an application did to a file it did not
    create. "made by Photoshop" would turn a save into an origin."""
    record = _record(
        "export.jpg",
        Origin(
            source="xmp-history",
            tool="Adobe Photoshop 22.0",
            at="2019-03-04T12:41:55Z",
            note="saved",
        ),
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "made by Adobe Photoshop 22.0" not in output
    assert "saved" in output


def test_the_timeline_says_what_an_edit_was_made_with():
    """The timeline gives an event one line, so an action printed without its
    application is an event nobody can attribute."""
    record = _record(
        "export.jpg",
        Origin(
            source="xmp-history",
            tool="Adobe Photoshop 22.0",
            at="2019-03-04T12:41:55Z",
            note="saved",
        ),
    )

    output = render_timeline([record], Path("/case"), theme=PLAIN)

    assert "saved in Adobe Photoshop 22.0" in output


# --- what the report says before it says anything about a file ---------------


def _corpus() -> list[FileRecord]:
    """A directory of the ordinary shape: several types, most of them readable,
    a few that said nothing, and one pair of records that disagree."""
    records = [
        _record("photo.jpg", Origin(source="device-metadata", tool="NIKON", geo="43.4, 11.8")),
        _record("holiday.jpg", Origin(source="device-metadata", tool="NIKON")),
        _record("paper.pdf", Origin(source="document-metadata", block="pdf-info", tool="Word")),
        _record("report.pdf", Origin(source="document-metadata", block="pdf-info", tool="Word")),
        _record("figure.png", Origin(source="c2pa", tool="OpenAI Media Service API")),
        _record("notes.txt"),
        _record("scratch.bin"),
    ]
    records.append(
        FileRecord(
            path="/case/invoice.pdf",
            size=2048,
            mtime="2026-08-24T19:00:00Z",
            origins=[
                Origin(source="browser-download", url="https://one.example.org/invoice.pdf"),
                Origin(source="windows-zone-identifier", url="https://other.example.net/i.pdf"),
            ],
        )
    )
    return records


def _rule(line: str) -> bool:
    return bool(line.strip()) and set(line.strip()) <= {"-", "\u2500"}


def _at(output: str, heading: str) -> int:
    """Which line carries a section heading.

    A heading is a line at column two with a rule directly under it. Both halves
    matter: `findings` is a word the banner uses as a row label too, and a plain
    substring search compared the wrong two positions and passed.
    """
    lines = output.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.startswith(f"  {heading}") and _rule(lines[index + 1]):
            return index
    raise AssertionError(f"no {heading!r} section in the report")


def _line(output: str, text: str) -> int:
    for index, line in enumerate(output.splitlines()):
        if text in line:
            return index
    raise AssertionError(f"{text!r} is not in the report")


def _section(output: str, heading: str) -> list[str]:
    """The lines of one section, from its heading down to the next one.

    Asserting that a name appears somewhere in a long report proves nothing:
    every name in the attention block also appears in the entry it points at.
    """
    lines = output.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().startswith(heading))
    rules = [index for index, line in enumerate(lines) if _rule(line) and index > start + 1]
    return lines[start : (rules[0] - 1) if rules else len(lines)]


def test_the_masthead_says_what_is_in_the_directory():
    """Files, types and bytes, before anything is said about any of them."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "8 files" in output
    assert "5 types" in output
    assert "6 with findings" in output
    assert "2 without findings" in output


def test_the_masthead_does_not_call_a_metadata_block_a_traced_origin():
    """A file with EXIF has not been traced anywhere. Counting it as though it
    had is the report telling the reader something it does not know."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "traced" not in output


def test_the_inventory_lists_every_type_with_its_share_of_the_bytes():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "inventory" in output
    for extension in ("PDF", "JPEG", "PNG", "TXT", "BIN"):
        assert extension in output, extension


def test_the_inventory_names_the_families_the_type_filter_uses():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "image" in output
    assert "document" in output


def test_the_findings_section_says_what_was_found():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "findings" in output
    assert "file metadata" in output
    assert "device information" in output
    assert "content credentials" in output


def test_attention_raises_the_conflict_and_names_the_file():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    raised = "\n".join(_section(output, "notable findings"))

    assert "conflicting evidence" in raised
    assert "invoice.pdf" in raised


def test_a_quiet_directory_raises_nothing():
    records = [_record("a.pdf", Origin(source="document-metadata", tool="Word")) for _ in range(3)]

    output = render_text(records, Path("/case"), theme=PLAIN)

    assert "attention" not in output


def test_the_report_reads_from_the_directory_down_to_the_file():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert _at(output, "inventory") < _at(output, "findings")
    assert _at(output, "findings") < _at(output, "notable findings")
    assert _at(output, "notable findings") < _line(output, "photo.jpg")
    assert _line(output, "photo.jpg") < _at(output, "no findings")
    assert _at(output, "no findings") < _at(output, "metadata sources")


def test_the_reader_table_is_technical_detail_and_goes_last():
    """It answers "which readers produced results", which is not the same
    question as "what was found" and must not stand in for it."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "metadata sources" in output
    assert _at(output, "metadata sources") > _at(output, "findings")


def test_the_last_line_counts_files_rather_than_recorded_origins():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "8 files analyzed" in output
    assert "6 with findings" in output
    assert "2 with no findings" in output
    assert "have a recorded origin" not in output


def test_one_file_is_not_given_an_inventory_of_itself():
    """`filegrail suspicious.pdf` is a common way in. A one-row inventory and a
    findings table over a single file is ceremony in front of the answer."""
    output = render_text(
        [_record("suspicious.pdf", Origin(source="document-metadata", tool="Word"))],
        Path("/case"),
        theme=PLAIN,
    )

    assert "inventory" not in output
    assert "suspicious.pdf" in output


def test_the_section_headings_say_what_the_section_holds():
    """`claimed by the file itself` is true and says nothing about what is in
    there; `no recorded origin` describes a narrower case than the list it
    heads, which holds every file nothing at all was found for."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "file metadata" in output
    assert "claimed by the file itself" not in output
    assert "no findings" in output
    assert "no recorded origin" not in output


# --- the report names itself -------------------------------------------------


def test_a_saved_report_says_what_produced_it():
    """`filegrail evidence/ --no-color > report.txt` has to be recognisable as
    a filegrail report months later, pasted into a case file, with nothing but
    the text."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "|_| |_|_" in output  # the wordmark's baseline row
    assert f"filegrail {__version__}" in output
    assert TAGLINE in output


def test_the_banner_says_what_was_scanned_and_what_came_back():
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "target" in output
    assert str(Path("/case")) in output  # spelled the way this platform does
    assert "scanned" in output
    assert "8 files" in output
    assert "5 types" in output


def test_the_banner_is_not_the_landing_screen():
    """The front door introduces the tool; a report identifies itself. Usage,
    commands and where to file a bug belong on one and not the other."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    for elsewhere in ("github.com", "Apache-2.0", "usage", "commands", "help <command>"):
        assert elsewhere not in output, elsewhere


@pytest.mark.parametrize("width", [48, 64, 80, 110])
def test_the_banner_fits_every_terminal(width: int):
    theme = Theme(colour=False, unicode=True, width=width)

    output = render_text(_corpus(), Path("/case"), theme=theme)

    assert f"filegrail {__version__}" in output
    assert not [line for line in output.splitlines() if len(line) > width]


def test_the_banner_is_ascii_where_the_terminal_is():
    output = render_text(_corpus(), Path("/case"), theme=Theme(False, False, 88))

    assert output.isascii()


# --- notable findings --------------------------------------------------------


def test_the_section_is_not_named_as_an_alarm():
    """Coordinates and Content Credentials are findings, not problems."""
    output = render_text(_corpus(), Path("/case"), theme=PLAIN)

    assert "notable findings" in output
    assert "attention" not in output


def test_a_bullet_still_means_a_file():
    """`●` is the entry glyph. Using it for a count line in another section
    spends the one symbol the gutter has for "this is a file"."""
    theme = Theme(colour=False, unicode=True, width=100)

    output = render_text(_corpus(), Path("/case"), theme=theme)
    notable = _section(output, "notable findings")

    assert not [line for line in notable if line.lstrip().startswith("●")]
    assert any("contains coordinates" in line for line in notable)


# --- the whole list, unless asked otherwise ----------------------------------


def _unexplained(count: int) -> list[FileRecord]:
    return [_record(f"f{index}.txt") for index in range(count)]


def test_every_file_with_no_findings_is_listed_by_default():
    """Nobody should have to run the tool a second time to see a list it
    already had."""
    output = render_text(_unexplained(40), Path("/case"), theme=PLAIN)

    assert "more (--limit" not in output
    assert _listed(output) == 40


def test_brief_is_where_the_list_gets_shortened():
    output = render_text(_unexplained(40), Path("/case"), theme=PLAIN, brief=True, limit=25)

    assert "... and 15 more" in output
