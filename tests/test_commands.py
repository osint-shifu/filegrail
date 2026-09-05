"""The command interface: modes are commands, options stay options."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from filegrail.cli import COMMANDS, build_parser, main


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

    assert "analyzed" in capsys.readouterr().out


def test_scan_can_be_named_explicitly(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main(["scan", str(tmp_path), "--no-color"]) == 0

    assert "analyzed" in capsys.readouterr().out


def test_help_lists_a_command(capsys):
    assert main(["help", "explain"]) == 0

    assert "filegrail explain" in capsys.readouterr().out


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
    """`filegrail scan` with no path scans the current directory, not a file
    called `scan`. Ambiguity resolved in favour of the command, which is what a
    reader of the usage line expects."""
    assert main(["scan", "--no-color", "--limit", "0"]) == 0

    assert "analyzed" in capsys.readouterr().out


def test_short_flags_work(tmp_path: Path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    assert main([str(tmp_path), "-j"]) == 0

    assert json.loads(capsys.readouterr().out)["files"]


def test_compare_ignores_what_merely_opened_a_file(tmp_path: Path, capsys):
    """An application that opened a file is not software that made it."""
    from filegrail.compare import compare
    from filegrail.models import FileRecord, Origin

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


def test_the_type_option_lists_every_family_it_accepts():
    """The help text was written by hand and `mail` had been added to the
    families without it, so `--type mail` worked and nothing said so."""
    from filegrail.filters import FAMILIES

    parser = build_parser()
    text = next(
        action.help
        for action in parser._actions
        if "--type" in getattr(action, "option_strings", [])
    )

    assert sorted(FAMILIES) == sorted(name for name in FAMILIES if name in text)


def test_clean_writes_every_file_it_says_it_wrote(tmp_path: Path, capsys):
    """The count in the summary has to match the files on disk.

    Two folders holding a `photo.jpg` used to produce one copy and a report
    claiming two, which is the worse half: somebody publishes the output of a
    command that told them it was complete.
    """
    from tests.photo import jpeg_with_exif

    source = tmp_path / "case"
    for folder, make in (("a", "NIKON"), ("b", "CANON")):
        (source / folder).mkdir(parents=True)
        jpeg_with_exif(source / folder / "photo.jpg", make, "MODEL", "2008:10:22 16:28:39")
    out = tmp_path / "clean"

    assert main(["clean", str(source), "--out", str(out), "--json"]) == 0

    document = json.loads(capsys.readouterr().out)
    claimed = {item["written"] for item in document["files"] if "written" in item}
    assert len(claimed) == document["summary"]["cleaned"] == 2
    assert {str(path) for path in out.rglob("*.jpg")} == claimed


def test_clean_does_not_overwrite_what_is_already_in_the_output(tmp_path: Path, capsys):
    from tests.photo import jpeg_with_exif

    source = tmp_path / "case"
    source.mkdir()
    jpeg_with_exif(source / "photo.jpg", "NIKON", "MODEL", "2008:10:22 16:28:39")
    out = tmp_path / "clean"
    out.mkdir()
    standing = out / "photo.jpg"
    standing.write_bytes(b"someone else's file")

    assert main(["clean", str(source), "--out", str(out), "--json"]) == 0

    assert standing.read_bytes() == b"someone else's file"
    assert json.loads(capsys.readouterr().out)["summary"]["cleaned"] == 0


def test_the_scan_document_carries_what_was_not_searched(tmp_path: Path, capsys):
    case = tmp_path / "case"
    (case / "node_modules").mkdir(parents=True)
    (case / "node_modules" / "index.js").write_text("x", encoding="utf-8")
    (case / "real.txt").write_text("x", encoding="utf-8")

    assert main([str(case), "--json", "--no-shell-history"]) == 0

    document = json.loads(capsys.readouterr().out)
    assert [Path(p).name for p in document["unsearched"]["skipped_by_name"]] == ["node_modules"]
    assert document["unsearched"]["unreadable"] == []


def test_no_skip_descends_into_the_names_a_scan_normally_leaves(tmp_path: Path, capsys):
    case = tmp_path / "case"
    (case / "build").mkdir(parents=True)
    (case / "build" / "shipped.txt").write_text("x", encoding="utf-8")

    assert main([str(case), "--json", "--no-shell-history"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["total"] == 0

    assert main([str(case), "--json", "--no-shell-history", "--no-skip"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["summary"]["total"] == 1
    assert document["unsearched"]["skipped_by_name"] == []


def _photo_that_will_not_come_fully_clean(path: Path) -> None:
    """A JPEG whose XMP packet sits after the end-of-image marker.

    Rebuilding the segment stream does not reach past that marker, so the packet
    survives the strip - which is exactly the case the copies are read back for.
    """
    from tests.photo import jpeg_with_exif

    jpeg_with_exif(path, "NIKON", "MODEL", "2008:10:22 16:28:39")
    path.write_bytes(
        path.read_bytes() + b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        b'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
        b'xmlns:xmp="http://ns.adobe.com/xap/1.0/"><xmp:CreatorTool>Some Editor'
        b"</xmp:CreatorTool></rdf:Description></rdf:RDF></x:xmpmeta>"
    )


def test_clean_check_answers_without_writing_anywhere(tmp_path: Path, capsys):
    from tests.photo import jpeg_with_exif

    source = tmp_path / "case"
    source.mkdir()
    jpeg_with_exif(source / "photo.jpg", "NIKON", "MODEL", "2008:10:22 16:28:39")

    assert main(["clean", str(source), "--check", "--json"]) == 0

    document = json.loads(capsys.readouterr().out)
    assert document["checked"] is True
    assert document["summary"]["cleaned"] == 1
    assert "destination" not in document
    assert [item["removed"] for item in document["files"]] == [["exif"]]
    assert list(source.iterdir()) == [source / "photo.jpg"]
    assert list(tmp_path.iterdir()) == [source]


def test_clean_check_exits_non_zero_when_a_copy_would_not_come_clean(tmp_path: Path, capsys):
    """The reason the mode has an exit code at all: it is a gate before publishing."""
    source = tmp_path / "case"
    source.mkdir()
    _photo_that_will_not_come_fully_clean(source / "photo.jpg")

    assert main(["clean", str(source), "--check", "--json"]) == 1

    assert json.loads(capsys.readouterr().out)["summary"]["still_readable"] == 1


def test_clean_exits_non_zero_when_a_copy_it_wrote_is_not_clean(tmp_path: Path, capsys):
    """The same question asked of the run that writes, or the check would be
    answering for a command that behaves differently."""
    source = tmp_path / "case"
    source.mkdir()
    _photo_that_will_not_come_fully_clean(source / "photo.jpg")

    assert main(["clean", str(source), "--out", str(tmp_path / "clean"), "--json"]) == 1


def test_clean_needs_a_destination_or_the_word_that_there_will_be_none(tmp_path: Path, capsys):
    source = tmp_path / "case"
    source.mkdir()

    assert main(["clean", str(source)]) == 2

    assert "--check" in capsys.readouterr().err


def test_the_check_report_says_that_nothing_was_written(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "110")
    from tests.photo import jpeg_with_exif

    source = tmp_path / "case"
    source.mkdir()
    jpeg_with_exif(source / "photo.jpg", "NIKON", "MODEL", "2008:10:22 16:28:39")

    assert main(["clean", str(source), "--check"]) == 0

    printed = " ".join(capsys.readouterr().out.split())
    assert "nothing written" in printed
    assert "1 would be cleaned" in printed


def test_clean_check_does_not_even_make_the_directory_it_would_write_to(tmp_path: Path, capsys):
    """A mode that writes nothing does not leave a directory behind as the one
    trace that it ran. The name is still reported, because it was still asked
    about: with `--out` this is a dry run of that exact command."""
    from tests.photo import jpeg_with_exif

    source = tmp_path / "case"
    source.mkdir()
    jpeg_with_exif(source / "photo.jpg", "NIKON", "MODEL", "2008:10:22 16:28:39")
    out = tmp_path / "clean"

    assert main(["clean", str(source), "--out", str(out), "--check", "--json"]) == 0

    assert not out.exists()
    assert json.loads(capsys.readouterr().out)["destination"] == str(out)
