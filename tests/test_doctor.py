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


def test_the_flag_prints_the_survey(capsys):
    assert main(["--doctor", "--no-color"]) == 0

    out = capsys.readouterr().out
    assert "evidence sources" in out
    assert "C2PA" in out


def test_json_is_machine_readable(capsys):
    assert main(["--doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert {entry["name"] for entry in payload["sources"]}
    assert all("state" in entry for entry in payload["sources"])


def test_the_survey_stays_inside_the_width(tmp_path: Path):
    found = survey(home=tmp_path)

    for width in (48, 64, 88, 110):
        output = render_doctor(found, Theme(colour=False, unicode=False, width=width))
        assert not [line for line in output.splitlines() if len(line) > width]
