"""Three kinds of claim, and typed findings rather than prose.

`acquisition` says how the file reached this machine. `interaction` says
something here handled it afterwards, which is not the same thing and must not
be presented as though it were. `intrinsic` says what the file records about its
own earlier life.

Findings carry a kind as well as a sentence, because a consumer reading the JSON
should not have to pattern-match English to tell a source conflict from a
timeline conflict.
"""

from __future__ import annotations

from filetrail.models import (
    ACQUISITION,
    CONFIDENCE,
    INTERACTION,
    INTRINSIC,
    FileRecord,
    Origin,
    kind,
)
from filetrail.reconcile import (
    CORROBORATION,
    SIZE_MISMATCH,
    SOURCE_CONFLICT,
    TIMELINE_CONFLICT,
    WEAK_MATCH,
    reconcile,
)


def _record(*origins: Origin) -> FileRecord:
    record = FileRecord(path="/case/a.pdf", size=4096, mtime="2026-08-24T19:00:00Z")
    record.origins.extend(origins)
    return record


# --- the three kinds ---------------------------------------------------------


def test_a_download_is_acquisition():
    assert kind(Origin(source="browser-download", url="https://x.org/a")) == ACQUISITION


def test_exif_is_intrinsic():
    assert kind(Origin(source="device-metadata", tool="Canon")) == INTRINSIC


def test_the_recent_documents_list_is_interaction_not_acquisition():
    """An application opening a file did not put it there."""
    assert kind(Origin(source="recent-documents", tool="GIMP")) == INTERACTION


def test_a_fetch_command_is_acquisition():
    origin = Origin(source="shell-history", tool="curl", command="curl -o a.pdf https://x.org/")

    assert kind(origin) == ACQUISITION


def test_a_command_that_merely_names_the_file_is_interaction():
    """`cat a.pdf` proves contact. It does not say where the bytes came from."""
    origin = Origin(source="shell-history", tool="cat", command="cat a.pdf")

    assert kind(origin) == INTERACTION


def test_every_source_has_a_kind():
    for source in CONFIDENCE:
        assert kind(Origin(source=source)) in (ACQUISITION, INTERACTION, INTRINSIC)


# --- typed findings ----------------------------------------------------------


def _download(url: str, **extra) -> Origin:
    return Origin(source="browser-download", url=url, tool="firefox", **extra)


def _kinds(verdict) -> set[str]:
    return {finding.kind for finding in verdict.findings}


def test_different_hosts_are_a_source_conflict():
    verdict = reconcile(
        _record(
            _download("https://example.com/a.pdf"),
            Origin(source="windows-zone-identifier", url="https://mirror.example.net/a.pdf"),
        )
    )

    assert SOURCE_CONFLICT in _kinds(verdict)
    assert TIMELINE_CONFLICT not in _kinds(verdict)


def test_creation_after_arrival_is_a_timeline_conflict():
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf", at="2026-08-01T10:00:00Z"),
            Origin(source="document-metadata", tool="Word", at="2026-08-24T19:02:11Z"),
        )
    )

    assert TIMELINE_CONFLICT in _kinds(verdict)
    assert SOURCE_CONFLICT not in _kinds(verdict)


def test_the_two_conflicts_are_independent():
    """A file can have both, and they are different problems."""
    verdict = reconcile(
        _record(
            _download("https://example.com/a.pdf", at="2026-08-01T10:00:00Z"),
            Origin(source="windows-zone-identifier", url="https://mirror.example.net/a.pdf"),
            Origin(source="document-metadata", tool="Word", at="2026-08-24T19:02:11Z"),
        )
    )

    assert {SOURCE_CONFLICT, TIMELINE_CONFLICT} <= _kinds(verdict)


def test_agreement_is_typed_too():
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf"),
            Origin(source="windows-zone-identifier", url="https://example.org/a.pdf"),
        )
    )

    assert CORROBORATION in _kinds(verdict)


def test_a_name_match_with_a_wrong_size_is_typed():
    origin = _download("https://example.org/a.pdf", bytes=9999)
    origin.note = "matched by file name, but the recorded size differs (9999 bytes recorded)"

    assert SIZE_MISMATCH in _kinds(reconcile(_record(origin)))


def test_a_bare_name_match_is_typed_as_weak():
    origin = _download("https://example.org/a.pdf")
    origin.note = "matched by file name; the file was moved or renamed since download"

    assert WEAK_MATCH in _kinds(reconcile(_record(origin)))


def test_interaction_records_never_create_a_source_conflict():
    """Two applications opening a file is not a disagreement about anything."""
    verdict = reconcile(
        _record(
            Origin(source="recent-documents", tool="GIMP", note="opened by GIMP"),
            Origin(source="recent-documents", tool="Eye of GNOME", note="opened by Eye of GNOME"),
        )
    )

    assert SOURCE_CONFLICT not in _kinds(verdict)


def test_json_carries_the_kind_and_the_sentence():
    verdict = reconcile(
        _record(
            _download("https://example.com/a.pdf"),
            Origin(source="windows-zone-identifier", url="https://mirror.example.net/a.pdf"),
        )
    )

    payload = verdict.to_dict()
    assert payload["state"]
    assert all({"kind", "text"} <= set(finding) for finding in payload["findings"])
