"""Do the acquisition records agree with each other?

One record is a claim. Two records that agree are corroboration. Two that
disagree are a finding in their own right - a file downloaded twice, a file
copied after acquisition, or origin metadata that was replaced - and a report
that silently prints the higher-scoring one has destroyed the finding.
"""

from __future__ import annotations

from pathlib import Path

from filetrail.models import FileRecord, Origin
from filetrail.reconcile import AGREEMENT, CONFLICT, NONE, PARTIAL, SINGLE, reconcile
from filetrail.report import render_text
from filetrail.theme import Theme

PLAIN = Theme(colour=False, unicode=True, width=88)


def _record(*origins: Origin, mtime: str = "2026-08-24T19:00:00Z") -> FileRecord:
    record = FileRecord(path="/case/a.pdf", size=4096, mtime=mtime)
    record.origins.extend(origins)
    return record


def _download(url: str, **extra) -> Origin:
    return Origin(source="browser-download", url=url, tool="firefox", **extra)


def _zone(url: str, **extra) -> Origin:
    return Origin(source="windows-zone-identifier", url=url, **extra)


# --- the verdict -------------------------------------------------------------


def test_no_acquisition_record_at_all():
    verdict = reconcile(_record(Origin(source="device-metadata", tool="Canon")))

    assert verdict.state == NONE


def test_one_record_is_not_corroboration():
    """A single source is the ordinary case, and not a finding either way."""
    verdict = reconcile(_record(_download("https://example.org/a.pdf")))

    assert verdict.state == SINGLE


def test_two_records_naming_the_same_url_agree():
    verdict = reconcile(
        _record(_download("https://example.org/a.pdf"), _zone("https://example.org/a.pdf"))
    )

    assert verdict.state == AGREEMENT
    assert "browser download" in " ".join(verdict.reasons)


def test_trivial_url_differences_still_agree():
    """A trailing slash and a capitalised host are the same address."""
    verdict = reconcile(
        _record(_download("https://Example.ORG/a.pdf"), _zone("https://example.org/a.pdf/"))
    )

    assert verdict.state == AGREEMENT


def test_the_same_host_by_a_different_path_is_partial():
    verdict = reconcile(
        _record(_download("https://example.org/a.pdf"), _zone("https://example.org/copy/a.pdf"))
    )

    assert verdict.state == PARTIAL
    assert "example.org" in " ".join(verdict.reasons)


def test_different_hosts_conflict():
    verdict = reconcile(
        _record(_download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf"))
    )

    assert verdict.state == CONFLICT
    reasons = " ".join(verdict.reasons)
    assert "example.com" in reasons
    assert "mirror.example.net" in reasons


def test_a_file_claiming_to_predate_nothing_is_unremarkable():
    """Created before it was downloaded is the normal order of events."""
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf", at="2026-08-24T19:02:11Z"),
            Origin(source="document-metadata", tool="Word", at="2026-08-01T10:00:00Z"),
        )
    )

    assert verdict.state == SINGLE
    assert not verdict.reasons


def test_a_file_claiming_to_postdate_its_download_is_flagged():
    """The bytes cannot have been authored after they arrived."""
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf", at="2026-08-01T10:00:00Z"),
            Origin(source="document-metadata", tool="Word", at="2026-08-24T19:02:11Z"),
        )
    )

    assert any("after" in reason for reason in verdict.reasons)


def test_a_name_only_match_is_called_out():
    origin = _download("https://example.org/a.pdf")
    origin.note = "matched by file name; the file was moved or renamed since download"

    verdict = reconcile(_record(origin))

    assert any("name" in reason for reason in verdict.reasons)


# --- what the report shows ---------------------------------------------------


def test_a_single_source_gets_no_verdict_line():
    """The common case must not be annotated, or the annotation means nothing."""
    output = render_text(
        [_record(_download("https://example.org/a.pdf"))], Path("/case"), theme=PLAIN
    )

    assert "agreement" not in output
    assert "conflict" not in output


def test_a_conflict_is_reported():
    record = _record(
        _download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf")
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "conflict" in output


def test_a_conflict_shows_both_records_without_verbose():
    """A verdict that refers to evidence the report hid is not a verdict."""
    record = _record(
        _download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf")
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "example.com/a.pdf" in output
    assert "mirror.example.net/a.pdf" in output


def test_agreement_is_reported_too():
    record = _record(_download("https://example.org/a.pdf"), _zone("https://example.org/a.pdf"))

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "agreement" in output
