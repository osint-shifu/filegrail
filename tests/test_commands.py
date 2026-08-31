"""The command interface: modes are commands, options stay options."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from filetrail.cli import COMMANDS, main


@pytest.fixture
def two(tmp_path: Path) -> tuple[Path, Path]:
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    return tmp_path / "a.txt", tmp_path / "b.txt"


def test_no_arguments_introduces_the_tool(capsys):
    assert main([]) == 0

    assert "usage" in capsys.readouterr().out


def test_a_bare_path_still_scans(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main([str(tmp_path), "--no-color"]) == 0

    assert "traced" in capsys.readouterr().out


def test_scan_can_be_named_explicitly(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main(["scan", str(tmp_path), "--no-color"]) == 0

    assert "traced" in capsys.readouterr().out


def test_help_lists_a_command(capsys):
    assert main(["help", "explain"]) == 0

    assert "filetrail explain" in capsys.readouterr().out


def test_help_refuses_an_unknown_command(capsys):
    assert main(["help", "nonsense"]) == 2

    err = capsys.readouterr().err
    assert "no such command" in err
    for name in COMMANDS:
        assert name in err


def test_explain_takes_one_file(two, capsys):
    left, _ = two

    assert main(["explain", str(left), "--no-color"]) == 0

    assert "conclusion" in capsys.readouterr().out


def test_explain_refuses_a_directory(tmp_path: Path, capsys):
    assert main(["explain", str(tmp_path)]) == 2

    assert "one file" in capsys.readouterr().err


def test_compare_takes_two_files(two, capsys):
    left, right = two

    assert main(["compare", str(left), str(right), "--no-color"]) == 0

    assert "assessment" in capsys.readouterr().out


def test_compare_refuses_a_missing_file(two, capsys):
    left, _ = two

    assert main(["compare", str(left), "/nowhere/at/all"]) == 2

    assert "two files" in capsys.readouterr().err


def test_compare_is_machine_readable(two, capsys):
    left, right = two

    assert main(["compare", str(left), str(right), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "assessment" in payload
    assert "acquisition" in payload


def test_explain_is_machine_readable(two, capsys):
    left, _ = two

    assert main(["explain", str(left), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert {"file", "reconciliation", "conclusion"} <= set(payload)


def test_a_path_named_like_a_command_still_needs_the_command_form(tmp_path: Path, capsys):
    """`filetrail scan` with no path scans the current directory, not a file
    called `scan`. Ambiguity resolved in favour of the command, which is what a
    reader of the usage line expects."""
    assert main(["scan", "--no-color", "--limit", "0"]) == 0

    assert "traced" in capsys.readouterr().out


def test_short_flags_work(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main([str(tmp_path), "-j"]) == 0

    assert json.loads(capsys.readouterr().out)["files"]


def test_compare_ignores_what_merely_opened_a_file(tmp_path: Path, capsys):
    """An application that opened a file is not software that made it."""
    from filetrail.compare import compare
    from filetrail.models import FileRecord, Origin

    def _rec(name: str, tool: str) -> FileRecord:
        record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
        record.origins.append(Origin(source="device-metadata", tool="Canon EOS R5"))
        record.origins.append(
            Origin(source="recent-documents", tool=tool, note=f"opened by {tool}")
        )
        return record

    found = compare(_rec("a.jpg", "GIMP"), _rec("b.jpg", "Telegram Desktop"))

    assert not found.differing
    assert ("Software", "Canon EOS R5") in found.shared
