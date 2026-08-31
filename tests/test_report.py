from pathlib import Path

from filetrail.models import FileRecord, Origin
from filetrail.report import render_text, render_timeline
from filetrail.theme import Theme

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

    assert "0 of 1 files have a recorded origin." in output
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
    assert "1 of 1 files have a recorded origin." in output


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
