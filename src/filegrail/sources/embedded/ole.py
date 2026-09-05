"""Compound File Binary documents: the Office formats that predate OOXML.

A `.doc`, `.xls` or `.ppt` is a small filesystem in a file. Its provenance sits
in two streams that every Office release has written since 1995:

    \\x05SummaryInformation          the application, the author, the last
                                    editor, the title and the creation date
    \\x05DocumentSummaryInformation  the company, and the manager

Both are property sets, a format shared with Windows shell metadata, so the
parser here is a general one pointed at two known FMTIDs.

These files are still everywhere - government portals, journal supplements and
scanned archives hand them out daily - and their metadata is often richer than
the modern equivalent, because nobody has thought to strip it.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

SUFFIXES = {".doc", ".xls", ".ppt", ".dot", ".xlt", ".pps", ".pot", ".msg"}

_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_ENDOFCHAIN = 0xFFFFFFFE
_FREESECT = 0xFFFFFFFF

#: A directory entry is fixed width, and its name is UTF-16.
_ENTRY_SIZE = 128
_STREAM = 2
_ROOT = 5

#: Guards against a crafted file describing a chain that never ends.
_MAX_SECTORS = 1 << 18
_MAX_ENTRIES = 4096
_MAX_PROPERTIES = 256
_MAX_STRING = 1024

# Property set format identifiers, little-endian on disk.
_SUMMARY = bytes.fromhex("e0859ff2f94f6810ab9108002b27b3d9")
_DOCUMENT_SUMMARY = bytes.fromhex("02d5cdd59c2e1b10939708002b2cf9ae")

# SummaryInformation property ids.
_TITLE = 2
_AUTHOR = 4
_LAST_AUTHOR = 8
_CREATED = 12
_APPLICATION = 18

# DocumentSummaryInformation property ids.
_COMPANY = 15

_VT_I2 = 2
_VT_I4 = 3
_VT_LPSTR = 30
_VT_LPWSTR = 31
_VT_FILETIME = 64

#: FILETIME counts 100ns intervals from 1601-01-01.
_EPOCH_1601 = datetime(1601, 1, 1, tzinfo=timezone.utc)


@dataclass(slots=True)
class Document:
    """What a compound document says about its own creation."""

    tool: str | None = None
    author: str | None = None
    last_author: str | None = None
    company: str | None = None
    created: str | None = None
    title: str | None = None

    def __bool__(self) -> bool:
        return any(
            (self.tool, self.author, self.last_author, self.company, self.created, self.title)
        )


def read_ole(path: Path) -> Document | None:
    """Return what a compound document says about itself, or None."""
    try:
        with path.open("rb") as handle:
            data = handle.read()
    except OSError:
        return None
    if not data.startswith(_SIGNATURE):
        return None

    try:
        container = _Container(data)
        found = Document()
        _apply(found, container.stream("\x05SummaryInformation"), _SUMMARY)
        _apply(found, container.stream("\x05DocumentSummaryInformation"), _DOCUMENT_SUMMARY)
    except (struct.error, ValueError, IndexError):
        return None
    return found if found else None


def read_streams(path: Path, names: Iterable[str]) -> dict[str, bytes]:
    """Return whichever of the named streams a compound document holds.

    Exposed because not every compound document is an Office one. An Outlook
    `.msg` is this same container carrying a message instead of a spreadsheet,
    and its reader has no business walking a FAT of its own.
    """
    try:
        with path.open("rb") as handle:
            data = handle.read()
    except OSError:
        return {}
    if not data.startswith(_SIGNATURE):
        return {}

    try:
        container = _Container(data)
        found = {}
        for name in names:
            raw = container.stream(name)
            if raw is not None:
                found[name] = raw
    except (struct.error, ValueError, IndexError):
        return {}
    return found


# --- the container -----------------------------------------------------------


class _Container:
    """Enough of the compound file to resolve a named stream to its bytes."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        (minor,) = struct.unpack_from("<H", data, 24)
        sector_shift, mini_shift = struct.unpack_from("<HH", data, 30)
        if not 6 <= sector_shift <= 20 or not 2 <= mini_shift <= sector_shift:
            raise ValueError("implausible sector size")

        self.sector_size = 1 << sector_shift
        self.mini_size = 1 << mini_shift
        (fat_count,) = struct.unpack_from("<I", data, 44)
        (self.directory_start,) = struct.unpack_from("<I", data, 48)
        (self.cutoff,) = struct.unpack_from("<I", data, 56)
        mini_fat_start, mini_fat_count = struct.unpack_from("<II", data, 60)
        difat_start, difat_count = struct.unpack_from("<II", data, 68)
        self.version = minor

        self.fat = self._read_fat(fat_count, difat_start, difat_count)
        self.mini_fat = self._read_table(mini_fat_start, mini_fat_count * self.sector_size)
        self.entries = self._read_directory()

        root = self.entries[0] if self.entries else None
        self.mini_stream = b""
        if root and root.kind == _ROOT and root.size:
            self.mini_stream = self._read_chain(root.start, root.size, self.fat, self.sector_size)

    # -- sector plumbing --

    def _sector(self, index: int) -> bytes:
        offset = (index + 1) * self.sector_size
        chunk = self.data[offset : offset + self.sector_size]
        if len(chunk) < self.sector_size:
            raise ValueError("sector past end of file")
        return chunk

    def _read_fat(self, count: int, difat_start: int, difat_count: int) -> list[int]:
        """Collect the FAT from the sectors the DIFAT points at."""
        locations = [
            value
            for (value,) in struct.iter_unpack("<I", self.data[76 : 76 + 109 * 4])
            if value < _FREESECT - 1
        ][:count]

        sector = difat_start
        seen = 0
        while sector < _FREESECT - 1 and seen < difat_count and seen < _MAX_SECTORS:
            block = self._sector(sector)
            entries = [value for (value,) in struct.iter_unpack("<I", block)]
            locations.extend(value for value in entries[:-1] if value < _FREESECT - 1)
            sector = entries[-1]
            seen += 1

        table: list[int] = []
        for location in locations[:_MAX_SECTORS]:
            table.extend(value for (value,) in struct.iter_unpack("<I", self._sector(location)))
        return table

    def _read_table(self, start: int, size: int) -> list[int]:
        if start >= _FREESECT - 1 or size <= 0:
            return []
        blob = self._read_chain(start, size, self.fat, self.sector_size)
        return [value for (value,) in struct.iter_unpack("<I", blob[: len(blob) // 4 * 4])]

    def _read_chain(self, start: int, size: int, table: list[int], unit: int) -> bytes:
        """Follow a sector chain, stopping at its end or at the declared size."""
        out = bytearray()
        sector = start
        visited = 0
        while sector < _FREESECT - 1 and len(out) < size and visited < _MAX_SECTORS:
            if unit == self.sector_size:
                out += self._sector(sector)
            else:
                offset = sector * unit
                out += self.mini_stream[offset : offset + unit]
            if sector >= len(table):
                break
            sector = table[sector]
            visited += 1
        return bytes(out[:size])

    # -- directory --

    def _read_directory(self) -> list[_Entry]:
        blob = self._read_chain(
            self.directory_start, _MAX_ENTRIES * _ENTRY_SIZE, self.fat, self.sector_size
        )
        entries = []
        for offset in range(0, len(blob) - _ENTRY_SIZE + 1, _ENTRY_SIZE):
            entry = _Entry.parse(blob[offset : offset + _ENTRY_SIZE])
            if entry is not None:
                entries.append(entry)
        return entries

    def stream(self, name: str) -> bytes | None:
        for entry in self.entries:
            if entry.kind == _STREAM and entry.name == name:
                if entry.size < self.cutoff and self.mini_stream:
                    return self._read_chain(entry.start, entry.size, self.mini_fat, self.mini_size)
                return self._read_chain(entry.start, entry.size, self.fat, self.sector_size)
        return None


@dataclass(slots=True)
class _Entry:
    name: str
    kind: int
    start: int
    size: int

    @classmethod
    def parse(cls, raw: bytes) -> _Entry | None:
        (length,) = struct.unpack_from("<H", raw, 64)
        kind = raw[66]
        if kind not in (_STREAM, _ROOT) or not 2 <= length <= 64:
            return None
        name = raw[: length - 2].decode("utf-16-le", "replace")
        start, size = struct.unpack_from("<IQ", raw, 116)
        return cls(name=name, kind=kind, start=start, size=size)


# --- property sets -----------------------------------------------------------


def _apply(found: Document, blob: bytes | None, fmtid: bytes) -> None:
    if not blob:
        return
    properties = _read_property_set(blob, fmtid)
    if not properties:
        return

    if fmtid == _SUMMARY:
        found.tool = found.tool or _text(properties.get(_APPLICATION))
        found.author = found.author or _text(properties.get(_AUTHOR))
        found.last_author = found.last_author or _text(properties.get(_LAST_AUTHOR))
        found.title = found.title or _text(properties.get(_TITLE))
        found.created = found.created or _timestamp(properties.get(_CREATED))
    else:
        found.company = found.company or _text(properties.get(_COMPANY))


def _read_property_set(blob: bytes, fmtid: bytes) -> dict[int, object]:
    """Decode the first section whose format identifier matches."""
    if len(blob) < 48 or blob[:2] != b"\xfe\xff":
        return {}
    (count,) = struct.unpack_from("<I", blob, 24)

    for index in range(min(count, 8)):
        base = 28 + index * 20
        if base + 20 > len(blob):
            return {}
        identifier = blob[base : base + 16]
        (offset,) = struct.unpack_from("<I", blob, base + 16)
        if identifier == fmtid:
            return _read_section(blob, offset)
    return {}


def _read_section(blob: bytes, base: int) -> dict[int, object]:
    if base + 8 > len(blob):
        return {}
    size, count = struct.unpack_from("<II", blob, base)
    if size <= 0 or base + size > len(blob) + 1:
        size = len(blob) - base

    found: dict[int, object] = {}
    for index in range(min(count, _MAX_PROPERTIES)):
        entry = base + 8 + index * 8
        if entry + 8 > len(blob):
            break
        identifier, offset = struct.unpack_from("<II", blob, entry)
        value = _read_value(blob, base + offset)
        if value is not None:
            found[identifier] = value
    return found


def _read_value(blob: bytes, offset: int) -> object | None:
    if offset + 4 > len(blob) or offset < 0:
        return None
    (kind,) = struct.unpack_from("<I", blob, offset)
    body = offset + 4

    if kind in (_VT_LPSTR, _VT_LPWSTR):
        if body + 4 > len(blob):
            return None
        (length,) = struct.unpack_from("<I", blob, body)
        if kind == _VT_LPWSTR:
            length *= 2
        if not 0 < length <= _MAX_STRING or body + 4 + length > len(blob):
            return None
        raw = blob[body + 4 : body + 4 + length]
        encoding = "utf-16-le" if kind == _VT_LPWSTR else "utf-8"
        return raw.split(b"\x00\x00" if kind == _VT_LPWSTR else b"\x00")[0].decode(
            encoding, "replace"
        )

    if kind == _VT_FILETIME:
        if body + 8 > len(blob):
            return None
        (ticks,) = struct.unpack_from("<Q", blob, body)
        return ticks or None

    if kind in (_VT_I2, _VT_I4):
        width = 2 if kind == _VT_I2 else 4
        if body + width > len(blob):
            return None
        return int(struct.unpack_from("<h" if kind == _VT_I2 else "<i", blob, body)[0])

    return None


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().strip("\x00").strip()
    return cleaned or None


def _timestamp(value: object) -> str | None:
    """Turn a FILETIME into an ISO instant, rejecting implausible ones."""
    if not isinstance(value, int) or value <= 0:
        return None
    try:
        moment = _EPOCH_1601 + timedelta(microseconds=value // 10)
    except (OverflowError, OSError, ValueError):
        return None
    if not 1980 <= moment.year <= 2100:
        return None
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
