"""Compound File Binary documents: the pre-XML Word, Excel and PowerPoint files.

The fixtures here are assembled rather than committed, so every offset in them
is computed. A hand-counted length that happens to agree with a hand-counted
reader proves nothing; `test_corpus.py` checks the same reader against real
files, which is what proves the layout right.
"""

from __future__ import annotations

import struct
from datetime import datetime, timezone
from pathlib import Path

from filegrail.sources.embedded import read_embedded_metadata
from filegrail.sources.embedded.ole import read_ole
from tests.compound import (
    DOCSUMMARY_FMTID,
    MINI_CUTOFF,
    SUMMARY_FMTID,
    VT_FILETIME,
    VT_LPSTR,
    ole,
)

# --- property set stream -----------------------------------------------------


EPOCH_1601 = datetime(1601, 1, 1, tzinfo=timezone.utc)


def _filetime(moment: datetime) -> bytes:
    """Encode an instant the way Windows does: 100ns ticks from 1601."""
    return struct.pack("<Q", int((moment - EPOCH_1601).total_seconds()) * 10_000_000)


def _property_set(fmtid: bytes, properties: dict[int, tuple[int, object]]) -> bytes:
    """Build a one-section property set stream.

    `properties` maps a property id to its (type, value). Offsets inside the
    section are computed from the encoded values, never assumed.
    """
    identifiers = sorted(properties)
    encoded: list[bytes] = []
    for identifier in identifiers:
        category, value = properties[identifier]
        if category == VT_LPSTR:
            raw = value.encode("utf-8") + b"\x00"
            blob = struct.pack("<II", VT_LPSTR, len(raw)) + raw
        elif category == VT_FILETIME:
            blob = struct.pack("<I", VT_FILETIME) + _filetime(value)
        else:  # pragma: no cover - the tests use no other type
            raise AssertionError(f"unsupported property type {category}")
        encoded.append(blob + b"\x00" * (-len(blob) % 4))

    table_size = 8 + len(identifiers) * 8
    offsets = []
    running = table_size
    for blob in encoded:
        offsets.append(running)
        running += len(blob)

    section = struct.pack("<II", running, len(identifiers))
    for identifier, offset in zip(identifiers, offsets, strict=True):
        section += struct.pack("<II", identifier, offset)
    section += b"".join(encoded)

    header = struct.pack("<HHI", 0xFFFE, 0, 0x00020006) + b"\x00" * 16
    header += struct.pack("<I", 1) + fmtid + struct.pack("<I", len(header) + 4 + 16 + 4)
    return header + section


WORD = {
    2: (VT_LPSTR, "Quarterly report"),
    4: (VT_LPSTR, "Ada Lovelace"),
    8: (VT_LPSTR, "Charles Babbage"),
    12: (VT_FILETIME, datetime(2001, 2, 3, 4, 0, 0, tzinfo=timezone.utc)),
    18: (VT_LPSTR, "Microsoft Word 9.0"),
}


# --- tests -------------------------------------------------------------------


def test_summary_information_from_the_mini_stream(tmp_path: Path):
    document = tmp_path / "report.doc"
    document.write_bytes(ole({"\x05SummaryInformation": _property_set(SUMMARY_FMTID, WORD)}))

    found = read_ole(document)

    assert found.tool == "Microsoft Word 9.0"
    assert found.author == "Ada Lovelace"
    assert found.title == "Quarterly report"
    assert found.created == "2001-02-03T04:00:00Z"


def test_summary_information_from_a_full_sector_stream(tmp_path: Path):
    """Real spreadsheets pad the stream to the cutoff, which moves it out of
    the mini stream and onto the regular FAT."""
    payload = _property_set(SUMMARY_FMTID, WORD)
    book = tmp_path / "book.xls"
    book.write_bytes(
        ole({"\x05SummaryInformation": payload.ljust(MINI_CUTOFF, b"\x00")}),
    )

    assert read_ole(book).tool == "Microsoft Word 9.0"


def test_company_comes_from_the_document_summary(tmp_path: Path):
    deck = tmp_path / "deck.ppt"
    deck.write_bytes(
        ole(
            {
                "\x05SummaryInformation": _property_set(SUMMARY_FMTID, WORD),
                "\x05DocumentSummaryInformation": _property_set(
                    DOCSUMMARY_FMTID, {15: (VT_LPSTR, "Analytical Engine Co")}
                ),
            }
        )
    )

    assert "Analytical Engine Co" in read_ole(deck).company


def test_the_reader_reaches_the_origin(tmp_path: Path):
    document = tmp_path / "memo.doc"
    document.write_bytes(ole({"\x05SummaryInformation": _property_set(SUMMARY_FMTID, WORD)}))

    origin = read_embedded_metadata(document)

    assert origin.source == "document-metadata"
    assert origin.tool == "Microsoft Word 9.0"
    assert origin.at == "2001-02-03T04:00:00Z"
    assert "author Ada Lovelace" in origin.note


def test_a_document_without_a_summary_reports_nothing(tmp_path: Path):
    document = tmp_path / "bare.doc"
    document.write_bytes(ole({"WordDocument": b"\x00" * 128}))

    assert read_ole(document) is None


def test_a_file_that_is_not_a_compound_document(tmp_path: Path):
    document = tmp_path / "fake.doc"
    document.write_bytes(b"not a compound file at all")

    assert read_ole(document) is None
    assert read_embedded_metadata(document) is None
