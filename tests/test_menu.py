"""The interactive front end, driven by a scripted reader.

`run` takes its input, its output and its executor as arguments, so a test can
type into it and read back exactly which command line it built. Nothing here
scans anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from filetrail import menu
from filetrail.theme import Theme

PLAIN = Theme(colour=False, unicode=False, width=80)


class Session:
    """A scripted reader, a captured transcript and a record of what ran."""

    def __init__(self, *typed: str) -> None:
        self.typed = list(typed)
        self.lines: list[str] = []
        self.ran: list[list[str]] = []

    def read(self, prompt: str = "") -> str:
        if not self.typed:
            raise EOFError
        return self.typed.pop(0)

    def write(self, line: str = "") -> None:
        self.lines.append(line)

    def execute(self, argv: list[str]) -> int:
        self.ran.append(argv)
        return 0

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def go(self, start: Path) -> int:
        return menu.run(start, execute=self.execute, read=self.read, write=self.write, theme=PLAIN)


def test_quitting_runs_nothing(tmp_path: Path):
    session = Session("q")

    assert session.go(tmp_path) == 0
    assert session.ran == []


def test_end_of_input_leaves_quietly(tmp_path: Path):
    """A closed stdin must not raise; it means the same as `q`."""
    session = Session()

    assert session.go(tmp_path) == 0
    assert session.ran == []


@pytest.mark.parametrize(
    ("key", "flags"),
    [
        ("1", []),
        ("2", ["--unknown-only"]),
        ("3", ["--timeline"]),
        ("4", ["--verbose"]),
        ("5", ["--brief"]),
        ("6", ["--hash"]),
        ("7", ["--identify"]),
        ("8", ["--redact", "--json"]),
        ("i", ["--type", "image"]),
        ("d", ["--type", "document"]),
        ("s", ["--doctor"]),
        ("e", ["--explain"]),
    ],
)
def test_each_action_builds_its_command_line(tmp_path: Path, key: str, flags: list[str]):
    session = Session(key, "", "q")

    session.go(tmp_path)

    assert session.ran == [[str(tmp_path.resolve()), *flags]]


def test_bare_enter_runs_the_obvious_thing(tmp_path: Path):
    """Pressing Enter at the menu should scan, not complain."""
    session = Session("", "", "q")

    session.go(tmp_path)

    assert session.ran == [[str(tmp_path.resolve())]]


def test_the_command_is_shown_before_it_runs(tmp_path: Path):
    session = Session("2", "", "q")

    session.go(tmp_path)

    assert "filetrail" in session.text
    assert "--unknown-only" in session.text


def test_a_typed_path_changes_the_folder(tmp_path: Path):
    """Typing a path is what people try before they find the `f` key."""
    elsewhere = tmp_path / "case"
    elsewhere.mkdir()
    session = Session(str(elsewhere), "1", "", "q")

    session.go(tmp_path)

    assert session.ran == [[str(elsewhere.resolve())]]


def test_the_folder_key_asks_for_a_path(tmp_path: Path):
    elsewhere = tmp_path / "evidence"
    elsewhere.mkdir()
    session = Session("f", str(elsewhere), "1", "", "q")

    session.go(tmp_path)

    assert session.ran == [[str(elsewhere.resolve())]]


def test_a_missing_folder_is_reported_and_the_target_is_kept(tmp_path: Path):
    session = Session("/nowhere/at/all", "1", "", "q")

    session.go(tmp_path)

    assert "no such file or directory" in session.text
    assert session.ran == [[str(tmp_path.resolve())]]


def test_help_shows_the_real_usage_and_returns(tmp_path: Path):
    session = Session("h", "", "q")

    session.go(tmp_path)

    assert "--unknown-only" in session.text
    assert "usage: filetrail" in session.text
    assert session.ran == []


def test_the_folder_and_its_size_are_always_on_screen(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    session = Session("q")

    session.go(tmp_path)

    assert "2 files" in session.text
    assert str(tmp_path.resolve()) in session.text or "~/" in session.text


def test_a_single_file_is_counted_in_the_singular(tmp_path: Path):
    (tmp_path / "only.txt").write_text("x", encoding="utf-8")
    session = Session("q")

    session.go(tmp_path)

    assert "1 file" in session.text
    assert "1 files" not in session.text


def test_a_large_folder_is_flagged_before_anything_scans_it(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(menu, "_count", lambda target: 51_000)
    session = Session("q")

    session.go(tmp_path)

    assert "that is a lot of files" in session.text


def test_an_interrupted_scan_returns_to_the_menu(tmp_path: Path):
    """Ctrl-C should stop the scan, not the program."""

    def interrupted(argv: list[str]) -> int:
        raise KeyboardInterrupt

    session = Session("1", "", "q")
    menu.run(tmp_path, execute=interrupted, read=session.read, write=session.write, theme=PLAIN)

    assert "stopped" in session.text


def test_a_redirected_stream_has_no_menu():
    class NotATerminal:
        def isatty(self) -> bool:
            return False

    assert menu.available(NotATerminal()) is False
