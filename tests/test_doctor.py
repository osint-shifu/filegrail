"""What could be searched, reported before anything is searched.

`no recorded origin` means one of two very different things: the evidence was
searched and the file was not in it, or the evidence was never there to search.
A reader who assumes the first when the second is true has drawn a conclusion
the tool never supported.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from filetrail.cli import main
from filetrail.doctor import AVAILABLE, PARTIAL, UNAVAILABLE, survey
from filetrail.report import render_doctor
from filetrail.theme import Theme

PLAIN = Theme(colour=False, unicode=False, width=88)


def _state(found, name: str) -> str:
    return next(check.state for check in found.checks if check.name.startswith(name))


def _detail(found, name: str) -> str:
    return next(check.detail for check in found.checks if check.name.startswith(name))


# --- browsers ----------------------------------------------------------------


def test_no_profile_at_all_is_reported_as_unavailable(tmp_path: Path):
    found = survey(home=tmp_path)

    assert _state(found, "Chromium") == UNAVAILABLE
    assert _state(found, "Firefox") == UNAVAILABLE
    assert "no profile" in _detail(found, "Chromium")


def _chromium(home: Path, rows: list[tuple[str, int, str]]) -> Path:
    profile = home / ".config" / "google-chrome" / "Default"
    profile.mkdir(parents=True)
    database = profile / "History"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE downloads (id INTEGER, target_path TEXT, tab_url TEXT, referrer TEXT,"
        " start_time INTEGER, total_bytes INTEGER, mime_type TEXT, state INTEGER)"
    )
    for index, (target, start, url) in enumerate(rows):
        connection.execute(
            "INSERT INTO downloads VALUES (?,?,?,?,?,?,?,1)",
            (index, target, url, "", start, 0, ""),
        )
    connection.commit()
    connection.close()
    return database


def test_a_readable_profile_reports_its_record_count(tmp_path: Path):
    # Chrome time: microseconds since 1601. 13300000000000000 is in 2022.
    _chromium(tmp_path, [("/x/a.pdf", 13300000000000000, "https://example.org/a.pdf")])

    found = survey(home=tmp_path)

    assert _state(found, "Chromium") == AVAILABLE
    assert "1 records" in _detail(found, "Chromium")


def test_the_oldest_record_sets_the_horizon(tmp_path: Path):
    """The honest limit of what this machine can answer."""
    _chromium(
        tmp_path,
        [
            ("/x/a.pdf", 13300000000000000, "https://example.org/a.pdf"),
            ("/x/b.pdf", 13350000000000000, "https://example.org/b.pdf"),
        ],
    )

    found = survey(home=tmp_path)

    horizon = next(check for check in found.horizon if "oldest" in check.name)
    assert horizon.detail.startswith("2022")


def test_an_unreadable_profile_does_not_crash_the_survey(tmp_path: Path):
    profile = tmp_path / ".config" / "google-chrome" / "Default"
    profile.mkdir(parents=True)
    (profile / "History").write_bytes(b"this is not a database")

    found = survey(home=tmp_path)

    assert _state(found, "Chromium") == UNAVAILABLE


# --- the rest ----------------------------------------------------------------


def test_a_history_without_timestamps_is_only_partial(tmp_path: Path):
    """A command with no time is corroboration that cannot be placed."""
    (tmp_path / ".bash_history").write_text("ls -la\ncurl -o a.pdf https://x.org/\n")

    found = survey(home=tmp_path)

    assert _state(found, "Shell history") == PARTIAL
    assert "without timestamps" in _detail(found, "Shell history")


def test_a_history_with_timestamps_is_available(tmp_path: Path):
    (tmp_path / ".zsh_history").write_text(": 1724524931:0;curl -o a.pdf https://x.org/\n")

    found = survey(home=tmp_path)

    assert _state(found, "Shell history") == AVAILABLE
    assert "with timestamps" in _detail(found, "Shell history")


def test_c2pa_is_always_reported_as_unverified():
    """The one claim the tool must never let a reader over-read."""
    found = survey()

    assert _state(found, "C2PA") == UNAVAILABLE
    assert "crypto" in _detail(found, "C2PA")


def test_every_check_has_a_state_and_a_name(tmp_path: Path):
    found = survey(home=tmp_path)

    assert found.checks
    for check in found.checks:
        assert check.name
        assert check.state


# --- through the command line ------------------------------------------------


def test_the_command_prints_the_survey(capsys):
    assert main(["doctor", "--no-color"]) == 0

    out = capsys.readouterr().out
    assert "evidence sources" in out
    assert "C2PA" in out


def test_json_is_machine_readable(capsys):
    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert {entry["name"] for entry in payload["sources"]}
    assert all("state" in entry for entry in payload["sources"])


def test_the_survey_stays_inside_the_width(tmp_path: Path):
    found = survey(home=tmp_path)

    for width in (48, 64, 88, 110):
        output = render_doctor(found, Theme(colour=False, unicode=False, width=width))
        assert not [line for line in output.splitlines() if len(line) > width]


# --- the sources a scan actually consults -------------------------------------


XBEL = """<?xml version="1.0" encoding="UTF-8"?>
<xbel version="1.0"
  xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks">
  <bookmark href="file:///case/a.pdf" added="{first}">
    <info><metadata owner="http://freedesktop.org">
      <bookmark:applications>
        <bookmark:application name="LibreOffice Writer"/>
      </bookmark:applications>
    </metadata></info>
  </bookmark>
  <bookmark href="file:///case/b.pdf" added="{second}">
    <info><metadata owner="http://freedesktop.org">
      <bookmark:applications>
        <bookmark:application name="Okular"/>
      </bookmark:applications>
    </metadata></info>
  </bookmark>
</xbel>
"""


def _recent(home: Path, first: str, second: str) -> None:
    share = home / ".local" / "share"
    share.mkdir(parents=True)
    (share / "recently-used.xbel").write_text(
        XBEL.format(first=first, second=second), encoding="utf-8"
    )


def test_a_desktop_that_records_openings_is_reported(tmp_path: Path):
    """`scan` reads this on every run; the survey never mentioned it.

    A reader told which sources could be searched, and then handed a finding
    from one that was not on the list, has been given an incomplete promise -
    which is worse than none, because they cannot tell where the gap is.
    """
    _recent(tmp_path, "2026-04-17T09:00:00Z", "2026-08-30T11:00:00Z")

    found = survey(home=tmp_path)

    assert _state(found, "Recent documents") == AVAILABLE
    assert "2 files" in _detail(found, "Recent documents")


def test_a_desktop_with_no_record_of_openings_says_so(tmp_path: Path):
    found = survey(home=tmp_path)

    assert _state(found, "Recent documents") == UNAVAILABLE
    assert "no list found" in _detail(found, "Recent documents")


def test_the_recent_list_reports_how_far_back_it_reaches(tmp_path: Path):
    """The oldest entry is the honest limit, exactly as it is for a browser."""
    _recent(tmp_path, "2026-04-17T09:00:00Z", "2026-08-30T11:00:00Z")

    found = survey(home=tmp_path)

    horizon = {check.name: check.detail for check in found.horizon}
    assert horizon["Recent documents oldest entry"] == "2026-04-17"


def test_a_timestamped_shell_history_reports_how_far_back_it_reaches(tmp_path: Path):
    (tmp_path / ".zsh_history").write_text(
        ": 1713340800:0;curl -o a.pdf https://x.org/\n: 1756598400:0;ls\n"
    )

    found = survey(home=tmp_path)

    horizon = {check.name: check.detail for check in found.horizon}
    assert horizon["Shell history oldest command"] == "2024-04-17"


def test_a_shell_history_without_times_claims_no_horizon(tmp_path: Path):
    """Ordering survives; dates do not, and a horizon would be invented."""
    (tmp_path / ".bash_history").write_text("ls -la\n")

    found = survey(home=tmp_path)

    assert not [check for check in found.horizon if check.name.startswith("Shell")]


def test_every_source_that_reads_a_home_directory_is_surveyed():
    """The invariant that would have caught the missing one.

    Anything under `sources` that takes a home directory is evidence a scan
    will use, so `doctor` has to account for it or stop claiming to say what
    could be searched.
    """
    import inspect

    from filetrail import sources
    from filetrail.doctor import HOME_SOURCES

    reads_a_home = {
        name
        for name in sources.__all__
        if "home" in inspect.signature(getattr(sources, name)).parameters
    }

    assert reads_a_home == set(HOME_SOURCES), sorted(reads_a_home ^ set(HOME_SOURCES))


def test_every_surveyed_source_is_named_in_the_report(tmp_path: Path):
    """The registry is only worth having if the survey actually emits it."""
    from filetrail.doctor import HOME_SOURCES

    found = survey(home=tmp_path)

    names = {check.name for check in found.checks}
    for expected in (name for group in HOME_SOURCES.values() for name in group):
        assert expected in names, expected


def test_a_bash_history_with_times_also_reports_a_horizon(tmp_path: Path):
    """Two shells, two spellings of the same fact, one horizon."""
    (tmp_path / ".bash_history").write_text("#1713340800\ncurl -o a.pdf https://x.org/\n")

    found = survey(home=tmp_path)

    horizon = {check.name: check.detail for check in found.horizon}
    assert horizon["Shell history oldest command"] == "2024-04-17"


def test_the_horizon_note_covers_every_source_it_lists(tmp_path: Path):
    """The note named browser history back when browsers were the only horizon.

    With a shell and a desktop list beside them it describes one row of three
    and reads as though the other two carried no limit at all.
    """
    _recent(tmp_path, "2026-04-17T09:00:00Z", "2026-08-30T11:00:00Z")

    out = render_doctor(survey(home=tmp_path), PLAIN)

    assert "Recent documents oldest entry" in out
    assert "browser history" not in out


def _quarantine(home: Path, rows: int) -> None:
    import sqlite3

    from filetrail.sources.quarantine import QUARANTINE_DB

    path = home / QUARANTINE_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE LSQuarantineEvent (
          LSQuarantineEventIdentifier TEXT PRIMARY KEY,
          LSQuarantineTimeStamp REAL,
          LSQuarantineAgentName TEXT,
          LSQuarantineDataURLString TEXT,
          LSQuarantineOriginURLString TEXT);
    """)
    for index in range(rows):
        connection.execute(
            "INSERT INTO LSQuarantineEvent VALUES (?,?,?,?,?)",
            (f"id-{index}", 750_000_000.0 + index, "Safari", f"https://x.org/{index}.zip", None),
        )
    connection.commit()
    connection.close()


def test_a_quarantine_database_is_reported_with_what_it_holds(tmp_path: Path):
    _quarantine(tmp_path, rows=3)

    found = survey(home=tmp_path)

    assert _state(found, "macOS quarantine") == AVAILABLE
    assert "3 downloads" in _detail(found, "macOS quarantine")


def test_no_quarantine_database_says_so(tmp_path: Path):
    found = survey(home=tmp_path)

    assert _state(found, "macOS quarantine") == UNAVAILABLE


def test_the_quarantine_database_reports_how_far_back_it_reaches(tmp_path: Path):
    """Counted from 2001 like every Core Foundation timestamp."""
    _quarantine(tmp_path, rows=3)

    found = survey(home=tmp_path)

    horizon = {check.name: check.detail for check in found.horizon}
    assert horizon["macOS quarantine oldest download"] == "2024-10-07"
