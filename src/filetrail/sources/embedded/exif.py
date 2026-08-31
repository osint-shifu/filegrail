"""TIFF/EXIF metadata, and the containers that carry it.

EXIF is a TIFF header, so one reader serves every container that embeds one:

    JPEG    APP1 segment beginning ``Exif\\x00\\x00``
    TIFF    the file is the TIFF header, including DNG, NEF, CR2 and ARW
    WebP    the ``EXIF`` chunk of the RIFF container
    HEIC    an ``Exif`` item inside the ISO base media container

Beyond the producing device this reads the **GPS IFD**, because where a
photograph was taken is provenance in the strictest sense, and it is routinely
the single most consequential fact a file carries.
"""

from __future__ import annotations

import struct
from pathlib import Path

JPEG_SUFFIXES = {".jpg", ".jpeg", ".jpe"}
TIFF_SUFFIXES = {".tif", ".tiff", ".dng", ".nef", ".cr2", ".arw", ".orf", ".rw2"}
WEBP_SUFFIXES = {".webp"}
HEIF_SUFFIXES = {".heic", ".heif", ".avif"}
SUFFIXES = JPEG_SUFFIXES | TIFF_SUFFIXES | WEBP_SUFFIXES | HEIF_SUFFIXES

# Tags worth reading. Everything else is exposure trivia, not provenance.
MAKE = 0x010F
MODEL = 0x0110
SOFTWARE = 0x0131
DATETIME = 0x0132
ARTIST = 0x013B
COPYRIGHT = 0x8298
EXIF_IFD = 0x8769
GPS_IFD = 0x8825
DATETIME_ORIGINAL = 0x9003
LENS_MODEL = 0xA434

GPS_LATITUDE_REF = 0x0001
GPS_LATITUDE = 0x0002
GPS_LONGITUDE_REF = 0x0003
GPS_LONGITUDE = 0x0004
GPS_ALTITUDE = 0x0006
GPS_DATESTAMP = 0x001D

_ASCII = 2
_RATIONAL = 5
_SRATIONAL = 10

_MAX_ENTRIES = 512
_MAX_STRING = 1024
_HEIF_SCAN_BYTES = 4 * 1024 * 1024


class Exif(dict):
    """Decoded tags, keyed by tag number, with the GPS block kept separate."""

    def __init__(self) -> None:
        super().__init__()
        self.gps: dict[int, object] = {}


def read_exif(path: Path) -> Exif | None:
    """Return the decoded EXIF of `path`, or None when it carries none."""
    suffix = path.suffix.lower()
    try:
        if suffix in JPEG_SUFFIXES:
            raw = _jpeg_exif(path)
        elif suffix in TIFF_SUFFIXES:
            raw = path.read_bytes()
        elif suffix in WEBP_SUFFIXES:
            raw = _webp_chunk(path, b"EXIF")
        elif suffix in HEIF_SUFFIXES:
            raw = _heif_exif(path)
        else:
            return None
    except (OSError, struct.error, ValueError):
        return None

    if not raw:
        return None
    try:
        return _parse_tiff(raw)
    except (struct.error, ValueError):
        return None


# --- containers --------------------------------------------------------------


def _jpeg_exif(path: Path) -> bytes:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return b""
        for marker, payload in _jpeg_segments(handle):
            if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
                return payload[6:]
    return b""


def _jpeg_segments(handle):
    """Yield (marker, payload) for each JPEG segment before the scan starts."""
    while True:
        marker = handle.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return
        if marker[1] in (0xDA, 0xD9):  # start of scan, end of image
            return
        length_bytes = handle.read(2)
        if len(length_bytes) < 2:
            return
        (length,) = struct.unpack(">H", length_bytes)
        if length < 2:
            return
        yield marker[1], handle.read(length - 2)


def _webp_chunk(path: Path, wanted: bytes) -> bytes:
    """Return one chunk of a RIFF/WebP file."""
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
            return b""
        while True:
            entry = handle.read(8)
            if len(entry) < 8:
                return b""
            fourcc, size = struct.unpack("<4sI", entry)
            payload = handle.read(size)
            if fourcc == wanted:
                # Some writers prefix the TIFF header with the JPEG marker.
                return payload[6:] if payload.startswith(b"Exif\x00\x00") else payload
            if size % 2:
                handle.read(1)  # chunks are padded to an even length


def _heif_exif(path: Path) -> bytes:
    """Locate the Exif payload in an ISO base media file.

    Resolving it properly means walking `iinf` and `iloc` to find the item and
    its extent. The payload is self-identifying, so it is found by its marker
    instead, which is markedly simpler and works on the files people actually
    have.
    """
    with path.open("rb") as handle:
        data = handle.read(_HEIF_SCAN_BYTES)
    marker = data.find(b"Exif\x00\x00")
    if marker < 0:
        return b""
    return data[marker + 6 :]


# --- TIFF --------------------------------------------------------------------


def _parse_tiff(data: bytes) -> Exif | None:
    if len(data) < 8:
        return None
    if data[:2] == b"II":
        endian = "<"
    elif data[:2] == b"MM":
        endian = ">"
    else:
        return None

    (first_ifd,) = struct.unpack_from(endian + "I", data, 4)
    exif = Exif()
    _read_ifd(data, first_ifd, endian, exif, exif)

    for pointer, target in ((EXIF_IFD, exif), (GPS_IFD, exif.gps)):
        offset = exif.pop(pointer, None)
        if isinstance(offset, int):
            _read_ifd(data, offset, endian, target, exif)

    return exif if (exif or exif.gps) else None


def _read_ifd(data: bytes, offset: int, endian: str, into: dict, exif: Exif) -> None:
    if offset <= 0 or offset + 2 > len(data):
        return
    (count,) = struct.unpack_from(endian + "H", data, offset)

    for index in range(min(count, _MAX_ENTRIES)):
        entry = offset + 2 + index * 12
        if entry + 12 > len(data):
            return
        tag, kind, length = struct.unpack_from(endian + "HHI", data, entry)

        if tag in (EXIF_IFD, GPS_IFD):
            (value,) = struct.unpack_from(endian + "I", data, entry + 8)
            exif[tag] = value
            continue

        value = _read_value(data, entry, endian, kind, length)
        if value is not None:
            into[tag] = value


def _read_value(data: bytes, entry: int, endian: str, kind: int, length: int):
    if kind == _ASCII:
        if length == 0 or length > _MAX_STRING:
            return None
        raw = _payload(data, entry, endian, length)
        if raw is None:
            return None
        text = raw.split(b"\x00")[0].decode("utf-8", "replace").strip()
        return text or None

    if kind in (_RATIONAL, _SRATIONAL):
        if length == 0 or length > 8:
            return None
        raw = _payload(data, entry, endian, length * 8)
        if raw is None or len(raw) < length * 8:
            return None
        fmt = endian + ("ii" if kind == _SRATIONAL else "II")
        values = []
        for index in range(length):
            numerator, denominator = struct.unpack_from(fmt, raw, index * 8)
            values.append(numerator / denominator if denominator else 0.0)
        return values[0] if length == 1 else values

    return None


def _payload(data: bytes, entry: int, endian: str, size: int) -> bytes | None:
    if size <= 4:
        return data[entry + 8 : entry + 8 + size]
    (offset,) = struct.unpack_from(endian + "I", data, entry + 8)
    if offset + size > len(data):
        return None
    return data[offset : offset + size]


# --- interpretation ----------------------------------------------------------


def camera(exif: Exif) -> str | None:
    """The device, as a human would name it, without repeating the maker."""
    make = _text(exif.get(MAKE))
    model = _text(exif.get(MODEL))
    if make and model:
        return model if model.lower().startswith(make.lower()) else f"{make} {model}"
    return make or model


def coordinates(exif: Exif) -> tuple[float, float] | None:
    """Return decimal (latitude, longitude) from the GPS IFD."""
    latitude = _degrees(exif.gps.get(GPS_LATITUDE), _text(exif.gps.get(GPS_LATITUDE_REF)), "S")
    longitude = _degrees(exif.gps.get(GPS_LONGITUDE), _text(exif.gps.get(GPS_LONGITUDE_REF)), "W")
    if latitude is None or longitude is None:
        return None
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return None
    return latitude, longitude


def _degrees(value: object, reference: str | None, negative: str) -> float | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    degrees, minutes, seconds = (float(part) for part in value[:3])
    decimal = degrees + minutes / 60 + seconds / 3600
    if reference and reference.upper().startswith(negative):
        decimal = -decimal
    return round(decimal, 6)


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
