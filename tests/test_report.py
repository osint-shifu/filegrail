from pathlib import Path

from whence.models import FileRecord, Origin
from whence.report import render_text


def _record(name: str, origin: Origin | None = None) -> FileRecord:
    record = FileRecord(path=f"/case/{name}", size=1, mtime="2026-08-24T19:00:00Z")
    if origin is not None:
        record.origins.append(origin)
    return record


def test_unknown_list_is_capped(tmp_path: Path):
    records = [_record(f"f{index}.txt") for index in range(40)]

    output = render_text(records, Path("/case"), limit=5)

    assert "... and 35 more" in output
    assert output.count("    created ") == 5


def test_no_cap_message_when_everything_fits():
    output = render_text([_record("a.txt"), _record("b.txt")], Path("/case"), limit=25)
    assert "more (--json" not in output


def test_zero_matches_explains_why():
    records = [_record("a.txt")]
    stats = {"browser_profiles": 4, "browser_records": 17}

    output = render_text(records, Path("/case"), stats=stats)

    assert "0 of 1 files have a recorded origin." in output
    assert "17 download records across 4 browser profiles" in output
    assert "prune download history" in output


def test_zero_matches_with_no_readable_profile():
    stats = {"browser_profiles": 0, "browser_records": 0}

    output = render_text([_record("a.txt")], Path("/case"), stats=stats)

    assert "No browser profile was readable" in output


def test_singular_wording():
    stats = {"browser_profiles": 1, "browser_records": 1}
    output = render_text([_record("a.txt")], Path("/case"), stats=stats)
    assert "1 download record across 1 browser profile" in output


def test_no_explanation_when_something_matched():
    found = _record("a.txt", Origin(source="browser-download", url="https://example.org/a"))
    stats = {"browser_profiles": 1, "browser_records": 1}

    output = render_text([found], Path("/case"), stats=stats)

    assert "prune download history" not in output
    assert "1 of 1 files have a recorded origin." in output
