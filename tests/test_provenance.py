"""Two questions, two answers, both always shown.

"Where did this file come from" and "what does this file say about its own
earlier life" are different questions, and a browser download record is not a
better answer to the second one than a camera's EXIF - it is not an answer to it
at all. Ranking them against each other means the stronger claim silently
deletes the weaker one, and for a geotagged photograph that was downloaded, the
thing deleted is the GPS fix.
"""

from __future__ import annotations

from pathlib import Path

from filetrail.models import ACQUISITION, CONFIDENCE, INTRINSIC, FileRecord, Origin
from filetrail.report import render_text
from filetrail.theme import Theme

PLAIN = Theme(colour=False, unicode=True, width=88)

DOWNLOAD = Origin(
    source="browser-download",
    url="https://example.org/holiday.jpg",
    tool="firefox",
    at="2026-08-24T19:02:11Z",
)
CAMERA = Origin(
    source="device-metadata",
    tool="NIKON COOLPIX P6000",
    at="2008-10-22T16:28:39Z",
    location="43.467448, 11.885127",
    fields={"BodySerialNumber": "3001234"},
)


def _record(*origins: Origin) -> FileRecord:
    record = FileRecord(path="/case/holiday.jpg", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.extend(origins)
    return record


# --- the classification ------------------------------------------------------


def test_every_source_is_classified():
    """An unclassified source would silently vanish from both halves."""
    assert set(CONFIDENCE) == ACQUISITION | INTRINSIC


def test_the_two_halves_do_not_overlap():
    assert not ACQUISITION & INTRINSIC


def test_a_download_is_acquisition_and_exif_is_intrinsic():
    record = _record(DOWNLOAD, CAMERA)

    assert record.acquisition is DOWNLOAD
    assert record.intrinsic is CAMERA


def test_a_file_with_only_one_kind_has_no_other():
    record = _record(CAMERA)

    assert record.acquisition is None
    assert record.intrinsic is CAMERA


def test_the_strongest_of_each_kind_wins_within_its_own_half():
    weak = Origin(source="shell-history", command="curl -o holiday.jpg https://example.org/")
    record = _record(weak, DOWNLOAD, CAMERA)

    assert record.acquisition is DOWNLOAD


# --- what the report shows ---------------------------------------------------


def test_a_downloaded_photograph_keeps_its_gps():
    """The regression this whole change exists to fix."""
    output = render_text([_record(DOWNLOAD, CAMERA)], Path("/case"), theme=PLAIN)

    assert "https://example.org/holiday.jpg" in output
    assert "NIKON COOLPIX P6000" in output
    assert "43.467448" in output
    assert "BodySerialNumber" in output


def test_acquisition_is_reported_before_intrinsic():
    """How it got here first; what it says about itself second."""
    output = render_text([_record(CAMERA, DOWNLOAD)], Path("/case"), theme=PLAIN)

    assert output.index("example.org/holiday.jpg") < output.index("NIKON COOLPIX P6000")


def test_a_file_with_one_kind_gains_no_empty_section():
    output = render_text([_record(CAMERA)], Path("/case"), theme=PLAIN)

    assert output.count("←") == 1


def test_brief_still_collapses_the_fields_of_both():
    output = render_text([_record(DOWNLOAD, CAMERA)], Path("/case"), theme=PLAIN, brief=True)

    assert "BodySerialNumber" not in output
    assert "NIKON COOLPIX P6000" in output
    assert "example.org/holiday.jpg" in output


def test_verbose_still_shows_every_claim():
    also = Origin(source="macos-wherefroms", url="https://mirror.example.net/holiday.jpg")
    output = render_text(
        [_record(DOWNLOAD, CAMERA, also)], Path("/case"), theme=PLAIN, verbose=True
    )

    assert "mirror.example.net" in output
    assert "example.org/holiday.jpg" in output
    assert "NIKON COOLPIX P6000" in output


def test_the_summary_counts_a_file_once():
    """Two claims about one file is still one file with a recorded origin."""
    output = render_text([_record(DOWNLOAD, CAMERA)], Path("/case"), theme=PLAIN)

    assert "1 of 1 files have a recorded origin." in output
