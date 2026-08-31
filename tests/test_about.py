"""The screen `filetrail` shows when it is run with nothing to do.

Typing the name of a tool and having it start work on the current directory is
a surprise, and in a home directory an expensive one. Bare `filetrail`
introduces itself and says how to point it somewhere instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from filetrail import REPOSITORY, __version__, about
from filetrail.cli import main
from filetrail.theme import Theme

#: The screen prints the repository without its scheme, so the line fits beside
#: the wordmark on an eighty-column terminal.
SHOWN_REPOSITORY = REPOSITORY.split("//", 1)[-1]

PLAIN = Theme(colour=False, unicode=False, width=80)

WIDTHS = [48, 56, 64, 80, 88, 110]


def _screen(theme: Theme | None = None) -> str:
    return about.render(theme=theme or PLAIN)


def test_it_says_what_it_is():
    screen = _screen()

    assert "filetrail" in screen
    assert __version__ in screen
    assert SHOWN_REPOSITORY in screen


def test_it_says_how_to_scan_the_current_folder():
    """The one thing someone needs next, and the one thing a bare run no
    longer does for them."""
    assert "filetrail <path>" in _screen()


def test_it_shows_the_wordmark():
    assert "|_| |_|_" in _screen()


def test_a_checkout_is_told_what_makes_the_examples_work(monkeypatch):
    """Printing `filetrail` at a shell that has no such command is how the
    screen gets disproved on the reader's first attempt."""
    monkeypatch.setattr(about.sys, "argv", ["/data/filetrail/src/filetrail/cli.py"])
    monkeypatch.setattr(about.shutil, "which", lambda name: None)
    monkeypatch.setenv("PYTHONPATH", "src")

    screen = _screen(Theme(colour=False, unicode=False, width=92))

    assert "alias filetrail=" in screen
    assert "pipx install filetrail" in screen
    assert "PYTHONPATH=src" in screen


def test_an_installed_run_says_nothing_about_installing(monkeypatch):
    monkeypatch.setattr(about.shutil, "which", lambda name: "/usr/local/bin/filetrail")

    screen = _screen()

    assert "alias filetrail=" not in screen
    assert "pipx install" not in screen


def test_it_shows_examples_and_flags():
    screen = _screen()

    for flag in ("--unknown-only", "--brief", "--identify", "--json", "--redact", "--version"):
        assert flag in screen, flag
    for command in ("scan", "explain", "compare", "doctor", "menu", "help"):
        assert command in screen, command


def test_it_does_not_list_the_evidence_sources():
    """That table belongs in `doctor`, where the question has been asked."""
    screen = _screen()

    assert "content credentials" not in screen
    assert "doctor" in screen


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("unicode_ok", [True, False])
def test_it_stays_inside_the_terminal_width(width: int, unicode_ok: bool):
    theme = Theme(colour=False, unicode=unicode_ok, width=width)

    screen = about.render(theme=theme)

    assert not [line for line in screen.splitlines() if len(line) > width]


def test_an_ascii_terminal_gets_ascii():
    screen = about.render(theme=Theme(colour=False, unicode=False, width=80))

    assert screen.isascii()


# --- how the command line reaches it ----------------------------------------


def test_a_bare_run_introduces_itself_and_scans_nothing(capsys):
    assert main([]) == 0

    out = capsys.readouterr().out
    assert SHOWN_REPOSITORY in out
    assert "traced" not in out  # the report's masthead, which must not appear


def test_help_with_no_command_shows_the_same_screen(capsys):
    assert main(["help"]) == 0

    assert SHOWN_REPOSITORY in capsys.readouterr().out


def test_an_explicit_dot_still_scans(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["."]) == 0

    out = capsys.readouterr().out
    assert "traced" in out
    assert SHOWN_REPOSITORY not in out


def test_a_path_with_flags_still_scans(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main([str(tmp_path), "--no-color"]) == 0

    assert "traced" in capsys.readouterr().out
