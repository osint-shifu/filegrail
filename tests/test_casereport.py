"""The investigation report, read the way an analyst reads it.

Every object starts on its own line with its number, no name is broken inside a
column, the sections follow the questions a case is opened with, and a file with
nothing to say takes one line until `-v` asks for all of it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from filegrail.analysis import analyse
from filegrail.casereport import render_case
from filegrail.doctor import AVAILABLE, UNAVAILABLE, Check, Survey
from filegrail.identify import extract
from filegrail.models import EvidenceRecord, FileRecord
from filegrail.theme import Theme

ROOT = Path("/case")
NOW = datetime(2026, 9, 15, 21, 18, tzinfo=timezone.utc)
LONG = "investigative-case-file-review-final-version-for-the-board.pdf"

HEADINGS = (
    "CASE SUMMARY",
    "KEY FINDINGS",
    "EVIDENCE COVERAGE",
    "CONFLICTS",
    "FILES",
    "RELATIONSHIPS",
    "INVESTIGATIVE PIVOTS",
    "FILE DETAIL",
    "REPORT NOTES",
    "END OF REPORT",
)


def _theme(width: int = 94) -> Theme:
    return Theme(colour=False, unicode=True, width=width)


def _file(name: str, *evidence: EvidenceRecord, size: int = 1024) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=size, mtime="2026-01-01T00:00:00Z")
    record.evidence.extend(evidence)
    return record


def _corpus() -> list[FileRecord]:
    contested = _file(
        LONG,
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
        size=10,
    )
    photo = _file(
        "press/holiday.jpg",
        EvidenceRecord(source="device-metadata", block="exif", geo="43.46745,11.88513"),
        size=5000,
    )
    sheet = _file(
        "isamples/sheet.xlsx",
        EvidenceRecord(
            source="document-metadata", block="ooxml-properties", fields={"creator": "A. Person"}
        ),
        size=3000,
    )
    return [contested, photo, sheet, _file("notes.md", size=100)]


def _report(records: list[FileRecord], **options: object) -> str:
    found = extract(records)
    survey = Survey(
        checks=[
            Check("Chromium family downloads", AVAILABLE, "3 records across 3 of 3 profiles"),
            Check("Shell history", UNAVAILABLE, "no history file found"),
        ],
        horizon=[Check("Chromium family oldest record", AVAILABLE, "2026-09-15")],
    )
    case = analyse(records, ROOT, survey=survey, identifiers=found)
    return render_case(case, identifiers=found, now=NOW, **options)  # type: ignore[arg-type]


def test_the_sections_follow_the_questions_a_case_is_opened_with():
    lines = _report(_corpus(), theme=_theme()).splitlines()

    assert [line for line in lines if line in HEADINGS] == [
        "CASE SUMMARY",
        "KEY FINDINGS",
        "EVIDENCE COVERAGE",
        "CONFLICTS",
        "FILES",
        "INVESTIGATIVE PIVOTS",
        "FILE DETAIL",
        "REPORT NOTES",
        "END OF REPORT",
    ]


def test_every_object_starts_on_its_own_line_with_its_whole_name():
    lines = _report(_corpus(), theme=_theme()).splitlines()

    assert f"! #001  {LONG}" in lines
    assert f"! C01  #001  {LONG}" in lines


def test_a_file_with_nothing_to_say_takes_one_line_until_verbose_opens_it():
    quiet = _report(_corpus(), theme=_theme()).splitlines()
    (sheet,) = [line for line in quiet if line.startswith("  #003  ")]

    assert sheet == "  #003  sheet.xlsx  XLSX · 2.9 KB · OOXML properties · in isamples"
    assert "  #003  sheet.xlsx" in _report(_corpus(), theme=_theme(), verbose=True).splitlines()


def test_a_file_points_at_its_conflict_and_the_conflict_shows_both_statements():
    report = _report(_corpus(), theme=_theme())
    files = report.split("\nFILES\n")[1].split("\nINVESTIGATIVE PIVOTS\n")[0]

    assert re.search(r"conflicts\s+C01", files)
    assert re.search(r"PDF Info\s+2018-05-11 18:37:20 UTC", report)
    assert re.search(r"Delta\s+72 days earlier", report)


def test_the_notes_explain_only_the_match_bases_the_report_uses():
    notes = _report(_corpus(), theme=_theme()).split("\nREPORT NOTES\n")[1]

    assert "embedded" in notes
    assert "recorded-path" not in notes
