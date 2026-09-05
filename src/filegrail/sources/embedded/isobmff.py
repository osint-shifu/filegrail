"""MP4, MOV and the rest of the ISO base media family.

Video is where provenance most often survives untouched, because the writing
device stamps the container and few tools rewrite it afterwards. Three things
are worth reading:

    the encoder or camera        udta atoms, ``\\xa9too``, ``\\xa9swr``, ``\\xa9mak``
    the creation time            ``mvhd``, or ``\\xa9day``
    where it was recorded        ``\\xa9xyz``, an ISO 6709 coordinate string
"""

from __future__ import annotations

import re
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO

SUFFIXES = {".mp4", ".m4v", ".m4a", ".mov", ".qt", ".3gp", ".heic", ".heif", ".avif"}

# ISO base media times count seconds from 1904-01-01.
_EPOCH_1904 = datetime(1904, 1, 1, tzinfo=timezone.utc)

_CONTAINERS = {b"moov", b"udta", b"trak", b"mdia", b"meta", b"ilst"}
_MAX_DEPTH = 8
_MAX_ATOMS = 2048
_MAX_TEXT = 512

ENCODER_ATOMS = (b"\xa9too", b"\xa9swr", b"\xa9enc")
MAKE_ATOMS = (b"\xa9mak", b"\xa9xmk")
MODEL_ATOMS = (b"\xa9mod", b"\xa9xmd")
DATE_ATOMS = (b"\xa9day", b"\xa9cre")
LOCATION_ATOMS = (b"\xa9xyz", b"loci")

_ISO6709 = re.compile(r"^([-+]\d{1,3}(?:\.\d+)?)([-+]\d{1,3}(?:\.\d+)?)")


class Movie:
    """What an ISO base media file says about its own creation."""

    def __init__(self) -> None:
        self.encoder: str | None = None
        self.make: str | None = None
        self.model: str | None = None
        self.created: str | None = None
        self.coordinates: tuple[float, float] | None = None

    def __bool__(self) -> bool:
        return any((self.encoder, self.make, self.model, self.created, self.coordinates))


def read_movie(path: Path) -> Movie | None:
    movie = Movie()
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            handle.seek(0)
            _walk(handle, 0, size, 0, movie)
    except (OSError, struct.error, ValueError):
        return movie if movie else None
    return movie if movie else None


def _walk(handle: BinaryIO, start: int, end: int, depth: int, movie: Movie) -> None:
    if depth > _MAX_DEPTH:
        return
    offset = start
    atoms = 0

    while offset + 8 <= end and atoms < _MAX_ATOMS:
        atoms += 1
        handle.seek(offset)
        header = handle.read(8)
        if len(header) < 8:
            return
        size, atom = struct.unpack(">I4s", header)
        body = offset + 8

        if size == 1:
            extended = handle.read(8)
            if len(extended) < 8:
                return
            (size,) = struct.unpack(">Q", extended)
            body += 8
        elif size == 0:
            size = end - offset
        if size < 8 or offset + size > end:
            return

        atom_end = offset + size
        if atom == b"meta":
            body += 4  # meta carries a version and flags before its children
        if atom in _CONTAINERS:
            _walk(handle, body, atom_end, depth + 1, movie)
        else:
            handle.seek(body)
            _absorb(atom, handle.read(min(atom_end - body, _MAX_TEXT)), movie)

        offset = atom_end


def _absorb(atom: bytes, payload: bytes, movie: Movie) -> None:
    if atom == b"mvhd" and movie.created is None:
        movie.created = _mvhd_time(payload)
        return

    text = _atom_text(payload)
    if not text:
        return
    if atom in ENCODER_ATOMS and not movie.encoder:
        movie.encoder = text
    elif atom in MAKE_ATOMS and not movie.make:
        movie.make = text
    elif atom in MODEL_ATOMS and not movie.model:
        movie.model = text
    elif atom in DATE_ATOMS and not movie.created:
        movie.created = _normalise(text)
    elif atom in LOCATION_ATOMS and not movie.coordinates:
        movie.coordinates = _iso6709(text)


def _mvhd_time(payload: bytes) -> str | None:
    if len(payload) < 12:
        return None
    version = payload[0]
    try:
        if version == 1 and len(payload) >= 20:
            (seconds,) = struct.unpack_from(">Q", payload, 4)
        else:
            (seconds,) = struct.unpack_from(">I", payload, 4)
    except struct.error:
        return None
    if not seconds:
        return None
    try:
        return _iso(_EPOCH_1904 + timedelta(seconds=seconds))
    except (OverflowError, ValueError):
        return None


def _atom_text(payload: bytes) -> str | None:
    """Decode the text an atom carries, in either of the two layouts.

    QuickTime writes a two-byte length and a language code before the string.
    The iTunes-style metadata that ``ilst`` uses instead nests a ``data`` box
    holding a type and a locale, and reading that as text yields the literal
    word "data" in front of every value.
    """
    body = payload
    if len(body) >= 16 and body[4:8] == b"data":
        (size,) = struct.unpack_from(">I", body, 0)
        end = min(size, len(body)) if size > 16 else len(body)
        body = body[16:end]
    elif len(body) >= 4:
        (declared,) = struct.unpack_from(">H", body, 0)
        if 0 < declared <= len(body) - 4:
            body = body[4 : 4 + declared]

    text = body.decode("utf-8", "replace").strip().strip("\x00").strip()
    return text or None


def _iso6709(text: str) -> tuple[float, float] | None:
    match = _ISO6709.match(text.strip())
    if not match:
        return None
    latitude, longitude = float(match.group(1)), float(match.group(2))
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return None
    return round(latitude, 6), round(longitude, 6)


def _normalise(text: str) -> str | None:
    for pattern in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y"):
        try:
            parsed = datetime.strptime(text.strip(), pattern)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return _iso(parsed)
    return None


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
