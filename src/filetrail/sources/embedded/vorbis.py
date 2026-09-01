"""Vorbis comments, as FLAC, Ogg Vorbis and Opus all carry them.

One layout in three containers: a vendor string written by whatever produced the
file, then a list of `NAME=value` entries. The list of names is open - a studio
writes whatever it uses - so every name is kept as written.

FLAC keeps the block among the metadata blocks at the front of the file, which
can be walked exactly. Ogg keeps it in the second packet of the stream, and this
reader finds it by the marker that opens that packet rather than by reassembling
Ogg pages: the header is at the front of every file anyone writes, and page
reassembly is a great deal of machinery for a block that has already been found.
The cost is that a comment block long enough to be split across pages stops
being readable partway, which is why every length is checked against what was
actually read.
"""

from __future__ import annotations

import struct
from pathlib import Path

FLAC_SUFFIXES = {".flac"}
OGG_SUFFIXES = {".ogg", ".oga", ".opus", ".spx"}
SUFFIXES = FLAC_SUFFIXES | OGG_SUFFIXES

_FLAC_MAGIC = b"fLaC"
_OGG_MAGIC = b"OggS"

#: What opens the comment packet, per codec.
_MARKERS = (b"\x03vorbis", b"OpusTags", b"\x7fFLAC")

_COMMENT_BLOCK = 4
_MAX_BLOCKS = 32
_MAX_COMMENTS = 256
_MAX_BLOCK = 2 * 1024 * 1024

#: Longer than this and it is not something a person typed. Cover art arrives
#: base64-encoded in a comment like any other, and a screenful of it would bury
#: the handful of values that say where the recording came from.
_MAX_VALUE = 4096

#: Enough to reach the header of any file anyone writes.
_WINDOW = 1024 * 1024


def read_comments(path: Path) -> dict[str, str] | None:
    """Return the comments of `path`, or None when it carries none."""
    try:
        with path.open("rb") as handle:
            data = handle.read(_WINDOW)
    except OSError:
        return None

    if data.startswith(_FLAC_MAGIC):
        found = _flac(data)
    elif data.startswith(_OGG_MAGIC):
        found = _ogg(data)
    else:
        return None
    return found or None


def _flac(data: bytes) -> dict[str, str]:
    """Walk the metadata blocks, which say their own type and length."""
    at = len(_FLAC_MAGIC)
    for _ in range(_MAX_BLOCKS):
        if at + 4 > len(data):
            return {}
        header = data[at]
        size = int.from_bytes(data[at + 1 : at + 4], "big")
        at += 4
        if size > len(data) - at or size > _MAX_BLOCK:
            return {}
        if header & 0x7F == _COMMENT_BLOCK:
            return _comments(data, at, at + size)
        if header & 0x80:  # the last block; the audio frames follow
            return {}
        at += size
    return {}


def _ogg(data: bytes) -> dict[str, str]:
    for marker in _MARKERS:
        at = data.find(marker)
        if at >= 0:
            return _comments(data, at + len(marker), len(data))
    return {}


def _comments(data: bytes, at: int, end: int) -> dict[str, str]:
    """The vendor string, then `NAME=value` entries, all little-endian."""
    vendor, at = _entry(data, at, end)
    if vendor is None:
        return {}

    found: dict[str, str] = {}
    if text := _text(vendor):
        found["Vendor"] = text
    if at + 4 > end:
        return found
    (count,) = struct.unpack_from("<I", data, at)
    at += 4

    for _ in range(min(count, _MAX_COMMENTS)):
        raw, at = _entry(data, at, end)
        if raw is None:
            # A length past what was read means the block was split across Ogg
            # pages. Reading on would report a page header as though a studio
            # had typed it, so what was recovered is returned as it stands.
            return found
        name, sign, value = raw.partition(b"=")
        if not sign or len(value) > _MAX_VALUE:
            continue
        if (text := _text(value)) and (label := _text(name)):
            found.setdefault(label, text)
    return found


def _entry(data: bytes, at: int, end: int) -> tuple[bytes | None, int]:
    if at + 4 > end:
        return None, at
    (size,) = struct.unpack_from("<I", data, at)
    at += 4
    if size > end - at:
        return None, at
    return data[at : at + size], at + size


def _text(raw: bytes) -> str | None:
    return " ".join(raw.decode("utf-8", "replace").split()) or None
