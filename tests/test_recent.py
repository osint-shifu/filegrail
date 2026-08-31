"""The desktop's recently-used list, as circumstantial acquisition evidence."""

from __future__ import annotations

from pathlib import Path

from filetrail.models import ACQUISITION, CONFIDENCE
from filetrail.sources.recent import collect_recent_files

XBEL = """<?xml version="1.0" encoding="UTF-8"?>
<xbel version="1.0"
      xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks">
  <bookmark href="file:///case/a%20photo.jpg" added="2026-08-24T19:02:11Z">
    <info><metadata owner="http://freedesktop.org">
      <bookmark:applications>
        <bookmark:application name="GIMP" exec="gimp %u" count="2"/>
        <bookmark:application name="Eye of GNOME" exec="eog %u" count="1"/>
      </bookmark:applications>
    </metadata></info>
  </bookmark>
  <bookmark href="https://example.org/not-a-file" added="2026-08-24T19:02:11Z"/>
</xbel>
"""


def _home(tmp_path: Path, body: str = XBEL) -> Path:
    target = tmp_path / ".local" / "share"
    target.mkdir(parents=True)
    (target / "recently-used.xbel").write_text(body, encoding="utf-8")
    return tmp_path


def test_a_bookmark_names_the_application_that_opened_it(tmp_path: Path):
    found = collect_recent_files(home=_home(tmp_path))

    origin = found["/case/a photo.jpg"][0]
    assert origin.tool == "GIMP"
    assert "GIMP" in origin.note
    assert "Eye of GNOME" in origin.note


def test_the_percent_escapes_in_the_path_are_decoded(tmp_path: Path):
    found = collect_recent_files(home=_home(tmp_path))

    assert "/case/a photo.jpg" in found


def test_a_bookmark_that_is_not_a_file_is_ignored(tmp_path: Path):
    found = collect_recent_files(home=_home(tmp_path))

    assert len(found) == 1


def test_a_missing_list_is_not_an_error(tmp_path: Path):
    assert collect_recent_files(home=tmp_path) == {}


def test_a_corrupt_list_is_not_an_error(tmp_path: Path):
    assert collect_recent_files(home=_home(tmp_path, "<xbel>truncated")) == {}


def test_it_ranks_below_shell_history():
    """Opening a file proves contact, not acquisition."""
    assert CONFIDENCE["recent-documents"] < CONFIDENCE["shell-history"]


def test_it_is_classified_as_acquisition():
    assert "recent-documents" in ACQUISITION
