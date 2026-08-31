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

from filetrail.sources.embedded import read_embedded_metadata
from filetrail.sources.embedded.ole import read_ole

SECTOR = 512
MINI_SECTOR = 64
MINI_CUTOFF = 4096

FREE = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD

SUMMARY_FMTID = bytes.fromhex("e0859ff2f94f6810ab9108002b27b3d9")
DOCSUMMARY_FMTID = bytes.fromhex("02d5cdd59c2e1b10939708002b2cf9ae")

VT_LPSTR = 30
VT_FILETIME = 64


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
        kind, value = properties[identifier]
        if kind == VT_LPSTR:
            raw = value.encode("utf-8") + b"\x00"
            blob = struct.pack("<II", VT_LPSTR, len(raw)) + raw
        elif kind == VT_FILETIME:
            blob = struct.pack("<I", VT_FILETIME) + _filetime(value)
        else:  # pragma: no cover - the tests use no other type
            raise AssertionError(f"unsupported property type {kind}")
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


# --- compound file -----------------------------------------------------------


def _directory_entry(name: str, kind: int, start: int, size: int, child: int = FREE) -> bytes:
    raw = name.encode("utf-16-le") + b"\x00\x00"
    entry = raw.ljust(64, b"\x00")[:64]
    entry += struct.pack("<HBB", len(raw), kind, 1)
    entry += struct.pack("<III", FREE, FREE, child)
    entry += b"\x00" * 16 + b"\x00" * 4 + b"\x00" * 16
    entry += struct.pack("<IQ", start, size)
    assert len(entry) == 128
    return entry


def _chain(first: int, count: int) -> list[int]:
    return [first + step + 1 for step in range(count - 1)] + [ENDOFCHAIN]


def _ole(streams: dict[str, bytes]) -> bytes:
    """Assemble a v3 compound file holding `streams`.

    A stream shorter than the cutoff goes into the mini stream, exactly as an
    encoder writes it, so the mini-FAT path is exercised rather than assumed.
    """
    big = {name: data for name, data in streams.items() if len(data) >= MINI_CUTOFF}
    small = {name: data for name, data in streams.items() if len(data) < MINI_CUTOFF}

    sectors: list[bytes] = []
    fat: list[int] = []
    directory: list[bytes] = []

    def allocate(payload: bytes, unit: int) -> tuple[int, int]:
        """Append `payload` as whole sectors, returning its start and count."""
        start = len(sectors)
        padded = payload + b"\x00" * (-len(payload) % unit)
        for offset in range(0, len(padded), unit):
            sectors.append(padded[offset : offset + unit].ljust(unit, b"\x00"))
        return start, (len(padded) // unit) or 0

    entries: list[tuple[str, int, int, int]] = []

    for name, data in big.items():
        start, count = allocate(data, SECTOR)
        fat.extend(_chain(start, count))
        entries.append((name, 2, start, len(data)))

    mini_stream = b""
    mini_fat: list[int] = []
    for name, data in small.items():
        index = len(mini_stream) // MINI_SECTOR
        padded = data + b"\x00" * (-len(data) % MINI_SECTOR)
        count = len(padded) // MINI_SECTOR
        mini_stream += padded
        mini_fat.extend(_chain(index, count))
        entries.append((name, 2, index, len(data)))

    mini_start = ENDOFCHAIN
    if mini_stream:
        mini_start, count = allocate(mini_stream, SECTOR)
        fat.extend(_chain(mini_start, count))

    mini_fat_start, mini_fat_count = ENDOFCHAIN, 0
    if mini_fat:
        blob = b"".join(struct.pack("<I", entry) for entry in mini_fat)
        mini_fat_start, mini_fat_count = allocate(blob, SECTOR)
        fat.extend(_chain(mini_fat_start, mini_fat_count))

    root = _directory_entry("Root Entry", 5, mini_start, len(mini_stream), child=1)
    directory.append(root)
    for name, kind, start, size in entries:
        directory.append(_directory_entry(name, kind, start, size))

    directory_start, directory_count = allocate(b"".join(directory), SECTOR)
    fat.extend(_chain(directory_start, directory_count))

    # The FAT describes the sectors it occupies too, so its own length has to
    # settle before it can be written: n data entries plus its own count must
    # fit in that same count of sectors.
    per_sector = SECTOR // 4
    fat_start = len(sectors)
    fat_count = 1
    while len(fat) + fat_count > fat_count * per_sector:
        fat_count += 1
        if fat_count > 64:  # pragma: no cover - fixtures are far smaller
            raise AssertionError("fixture too large")

    assert len(fat) == fat_start, "one FAT entry per allocated sector"
    fat.extend([FATSECT] * fat_count)
    table = b"".join(struct.pack("<I", entry) for entry in fat)
    table += struct.pack("<I", FREE) * (fat_count * per_sector - len(fat))
    for offset in range(0, len(table), SECTOR):
        sectors.append(table[offset : offset + SECTOR])

    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16
    header += struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6)
    header += b"\x00" * 6
    header += struct.pack("<III", 0, fat_count, directory_start)
    header += struct.pack("<II", 0, MINI_CUTOFF)
    header += struct.pack("<III", mini_fat_start, mini_fat_count, ENDOFCHAIN)
    header += struct.pack("<I", 0)
    difat = [fat_start + step for step in range(fat_count)]
    difat += [FREE] * (109 - len(difat))
    header += b"".join(struct.pack("<I", entry) for entry in difat)
    assert len(header) == SECTOR

    return header + b"".join(sectors)


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
    document.write_bytes(_ole({"\x05SummaryInformation": _property_set(SUMMARY_FMTID, WORD)}))

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
        _ole({"\x05SummaryInformation": payload.ljust(MINI_CUTOFF, b"\x00")}),
    )

    assert read_ole(book).tool == "Microsoft Word 9.0"


def test_company_comes_from_the_document_summary(tmp_path: Path):
    deck = tmp_path / "deck.ppt"
    deck.write_bytes(
        _ole(
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
    document.write_bytes(_ole({"\x05SummaryInformation": _property_set(SUMMARY_FMTID, WORD)}))

    origin = read_embedded_metadata(document)

    assert origin.source == "document-metadata"
    assert origin.tool == "Microsoft Word 9.0"
    assert origin.at == "2001-02-03T04:00:00Z"
    assert "author Ada Lovelace" in origin.note


def test_a_document_without_a_summary_reports_nothing(tmp_path: Path):
    document = tmp_path / "bare.doc"
    document.write_bytes(_ole({"WordDocument": b"\x00" * 128}))

    assert read_ole(document) is None


def test_a_file_that_is_not_a_compound_document(tmp_path: Path):
    document = tmp_path / "fake.doc"
    document.write_bytes(b"not a compound file at all")

    assert read_ole(document) is None
    assert read_embedded_metadata(document) is None
