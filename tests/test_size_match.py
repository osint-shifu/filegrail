"""Corroborating a name match with the size the record kept."""

from __future__ import annotations

from filetrail.models import FileRecord, Origin
from filetrail.reconcile import reconcile
from filetrail.scan import matched_by_name


def _origin(size: int | None) -> Origin:
    return Origin(source="browser-download", url="https://example.org/a.pdf", bytes=size)


def test_a_matching_size_corroborates_the_name():
    found = matched_by_name(_origin(4096), 4096)

    assert "size" in found.note
    assert "differs" not in found.note


def test_a_differing_size_says_so():
    """Same name, different bytes: very likely a different file."""
    found = matched_by_name(_origin(9999), 4096)

    assert "differs" in found.note


def test_no_recorded_size_leaves_the_name_match_as_it_was():
    found = matched_by_name(_origin(None), 4096)

    assert "matched by file name" in found.note
    assert "size" not in found.note


def test_a_size_mismatch_reaches_the_verdict():
    record = FileRecord(path="/case/a.pdf", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.append(matched_by_name(_origin(9999), 4096))

    verdict = reconcile(record)

    assert any("differs" in reason for reason in verdict.reasons)


def test_a_size_match_is_not_reported_as_a_problem():
    record = FileRecord(path="/case/a.pdf", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.append(matched_by_name(_origin(4096), 4096))

    verdict = reconcile(record)

    assert not any("differs" in reason for reason in verdict.reasons)
