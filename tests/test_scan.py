import sqlite3
from pathlib import Path

from filetrail.scan import scan
from filetrail.sources.fsattrs import read_file_attributes

from .test_browser import CHROMIUM_SCHEMA, START_TIME


def _profile_with(home: Path, target: str) -> None:
    profile = home / ".config" / "chromium" / "Default"
    profile.mkdir(parents=True)
    connection = sqlite3.connect(profile / "History")
    connection.executescript(CHROMIUM_SCHEMA)
    connection.execute(
        "INSERT INTO downloads VALUES (1,?,?,11,1,'','https://example.org/p','text/plain')",
        (target, START_TIME),
    )
    connection.commit()
    connection.close()


def test_exact_path_match_has_no_moved_note(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    evidence = case / "evidence.txt"
    evidence.write_text("hello world", encoding="utf-8")
    _profile_with(tmp_path, str(evidence))

    record = scan(case, home=tmp_path, use_shell_history=False)[0]

    assert record.best is not None
    assert record.best.source == "browser-download"
    assert record.best.note is None


def test_moved_file_is_matched_by_name_and_flagged(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    (case / "evidence.txt").write_text("hello world", encoding="utf-8")
    _profile_with(tmp_path, "/somewhere/else/evidence.txt")

    record = scan(case, home=tmp_path, use_shell_history=False)[0]

    assert record.best is not None
    assert "moved or renamed" in (record.best.note or "")


def test_file_without_any_origin(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    (case / "local.txt").write_text("made here", encoding="utf-8")

    record = scan(case, home=tmp_path, use_shell_history=False)[0]

    assert record.origins == []
    assert record.best is None
    assert record.size == 9


def test_hashing_is_opt_in(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    # Bytes, not text: `write_text` translates the newline to CRLF on Windows,
    # and a file this test hashes has to be the same file on every platform.
    (case / "a.txt").write_bytes(b"hello repro\n")

    assert scan(case, home=tmp_path, use_shell_history=False)[0].sha256 is None
    hashed = scan(case, home=tmp_path, use_shell_history=False, hash_files=True)[0]
    assert hashed.sha256 == "4e17aeaa904104862a741775bf05b6cb883716b07589e088c94d46d192ef4614"


def test_noise_directories_are_skipped(tmp_path: Path):
    case = tmp_path / "case"
    (case / ".git").mkdir(parents=True)
    (case / "__pycache__").mkdir()
    (case / ".git" / "config").write_text("x", encoding="utf-8")
    (case / "__pycache__" / "m.pyc").write_bytes(b"x")
    (case / "real.txt").write_text("x", encoding="utf-8")

    records = scan(case, home=tmp_path, use_shell_history=False)

    assert [Path(record.path).name for record in records] == ["real.txt"]


def test_xdg_xattr_is_read_when_supported(tmp_path: Path):
    import os

    target = tmp_path / "downloaded.bin"
    target.write_bytes(b"x")
    try:
        os.setxattr(str(target), "user.xdg.origin.url", b"https://example.org/downloaded.bin")
    except (AttributeError, OSError):
        return  # platform or filesystem does not support user xattrs

    origins = read_file_attributes(target)

    assert any(o.source == "xdg-xattr" for o in origins)
    assert origins[0].url == "https://example.org/downloaded.bin"
