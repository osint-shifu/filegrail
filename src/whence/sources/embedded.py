"""Origin evidence carried inside the file itself.

A download record says where a file came from. Embedded metadata answers a
different question - what produced it, who authored it and when - and it is
often the only answer available, because it survives copying, renaming, moving
between machines and the expiry of every browser history on the system.

Three containers are read, all with the standard library so the tool keeps no
runtime dependencies:

    PDF     the Info dictionary: Producer, Creator, Author, CreationDate
    OOXML   docProps/core.xml and app.xml: creator, lastModifiedBy, Company
    JPEG    the TIFF header: Make, Model, Software, DateTimeOriginal

This never reports a URL, so it does not compete with a download record. It
fills the gap underneath one.
"""

from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ElementTree
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ..models import Origin

PDF_SUFFIXES = {".pdf"}
OOXML_SUFFIXES = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm"}
JPEG_SUFFIXES = {".jpg", ".jpeg"}

# Only the head of a PDF trailer is scanned; the Info dictionary lives near the
# start or the end, and reading whole multi-gigabyte files would be pointless.
_PDF_SCAN_BYTES = 512 * 1024

_PDF_FIELDS = ("Producer", "Creator", "Author", "CreationDate", "ModDate")
_PDF_ENTRY = re.compile(
    rb"/(Producer|Creator|Author|CreationDate|ModDate)\s*\((?P<value>(?:\\.|[^\\)])*)\)"
)

_DC = "http://purl.org/dc/elements/1.1/"
_DCTERMS = "http://purl.org/dc/terms/"
_COREPROPS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_EXTPROPS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

# TIFF tags worth reading. Anything else is camera trivia, not provenance.
_TIFF_MAKE = 0x010F
_TIFF_MODEL = 0x0110
_TIFF_SOFTWARE = 0x0131
_TIFF_DATETIME = 0x0132
_TIFF_EXIF_IFD = 0x8769
_EXIF_DATETIME_ORIGINAL = 0x9003
_TIFF_ASCII = 2


def read_embedded_metadata(path: Path) -> Origin | None:
    """Return what the file says about its own creation, if anything."""
    suffix = path.suffix.lower()
    try:
        if suffix in PDF_SUFFIXES:
            return _read_pdf(path)
        if suffix in OOXML_SUFFIXES:
            return _read_ooxml(path)
        if suffix in JPEG_SUFFIXES:
            return _read_jpeg(path)
    except (OSError, ValueError, struct.error, zipfile.BadZipFile, ElementTree.ParseError):
        return None
    return None


def _origin(tool: str | None, at: str | None, note: str | None) -> Origin | None:
    if not tool and not at and not note:
        return None
    return Origin(source="document-metadata", tool=tool, at=at, note=note)


def _read_pdf(path: Path) -> Origin | None:
    with path.open("rb") as handle:
        head = handle.read(_PDF_SCAN_BYTES)
        if handle.seek(0, 2) > _PDF_SCAN_BYTES * 2:
            handle.seek(-_PDF_SCAN_BYTES, 2)
            head += handle.read(_PDF_SCAN_BYTES)

    found: dict[str, str] = {}
    for match in _PDF_ENTRY.finditer(head):
        key = match.group(1).decode("ascii")
        if key not in found:
            found[key] = _decode_pdf_string(match.group("value"))

    tool = found.get("Producer") or found.get("Creator")
    if found.get("Producer") and found.get("Creator") not in (None, found.get("Producer")):
        tool = f"{found['Producer']} (created in {found['Creator']})"

    notes = [f"author {found['Author']}"] if found.get("Author") else []
    return _origin(tool, _parse_pdf_date(found.get("CreationDate")), "; ".join(notes) or None)


def _decode_pdf_string(raw: bytes) -> str:
    value = re.sub(rb"\\([()\\])", rb"\1", raw)
    if value.startswith(b"\xfe\xff"):
        return value.decode("utf-16-be", "replace").strip("\x00").strip()
    return value.decode("latin-1", "replace").strip()


def _parse_pdf_date(value: str | None) -> str | None:
    """Parse a PDF date string, D:YYYYMMDDHHmmSS with an optional offset."""
    if not value:
        return None
    match = re.match(r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", value.strip())
    if not match or not match.group(1):
        return None
    defaults = (0, 1, 1, 0, 0, 0)
    year, month, day, hour, minute, second = (
        int(group) if group else default
        for group, default in zip(match.groups(), defaults, strict=True)
    )
    try:
        stamp = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except ValueError:
        return None
    return stamp.isoformat().replace("+00:00", "Z")


def _read_ooxml(path: Path) -> Origin | None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        core = _parse_xml(archive, names, "docProps/core.xml")
        app = _parse_xml(archive, names, "docProps/app.xml")

    author = _text(core, f"{{{_DC}}}creator")
    last_editor = _text(core, f"{{{_COREPROPS}}}lastModifiedBy")
    created = _text(core, f"{{{_DCTERMS}}}created")
    application = _text(app, f"{{{_EXTPROPS}}}Application")
    version = _text(app, f"{{{_EXTPROPS}}}AppVersion")
    company = _text(app, f"{{{_EXTPROPS}}}Company")

    tool = f"{application} {version}".strip() if application else None

    notes = []
    if author:
        notes.append(f"author {author}")
    if last_editor and last_editor != author:
        notes.append(f"last edited by {last_editor}")
    if company:
        notes.append(f"company {company}")

    return _origin(tool, _normalise_timestamp(created), "; ".join(notes) or None)


def _parse_xml(
    archive: zipfile.ZipFile, names: set[str], member: str
) -> ElementTree.Element | None:
    if member not in names:
        return None
    try:
        return ElementTree.fromstring(archive.read(member))
    except ElementTree.ParseError:
        return None


def _text(root: ElementTree.Element | None, tag: str) -> str | None:
    if root is None:
        return None
    value = root.findtext(tag)
    return value.strip() if value and value.strip() else None


def _normalise_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_jpeg(path: Path) -> Origin | None:
    tags = _read_exif_tags(path)
    if not tags:
        return None

    make = tags.get(_TIFF_MAKE)
    model = tags.get(_TIFF_MODEL)
    camera = " ".join(part for part in (make, model) if part) or None
    software = tags.get(_TIFF_SOFTWARE)

    tool = camera or software
    if camera and software:
        tool = f"{camera} (processed with {software})"

    taken = tags.get(_EXIF_DATETIME_ORIGINAL) or tags.get(_TIFF_DATETIME)
    return _origin(tool, _parse_exif_date(taken), None)


def _parse_exif_date(value: str | None) -> str | None:
    """EXIF stores 'YYYY:MM:DD HH:MM:SS' with no zone; treat it as UTC."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip().strip("\x00"), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _read_exif_tags(path: Path) -> dict[int, str]:
    """Minimal TIFF/EXIF reader for the handful of provenance tags."""
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return {}
        exif = _find_app1(handle)
    if exif is None or len(exif) < 8:
        return {}

    byte_order = exif[:2]
    if byte_order == b"II":
        endian = "<"
    elif byte_order == b"MM":
        endian = ">"
    else:
        return {}

    (first_ifd,) = struct.unpack_from(endian + "I", exif, 4)
    tags: dict[int, str] = {}
    _read_ifd(exif, first_ifd, endian, tags)

    if _TIFF_EXIF_IFD in tags:
        try:
            _read_ifd(exif, int(tags.pop(_TIFF_EXIF_IFD)), endian, tags)
        except (ValueError, struct.error):
            pass
    return tags


def _find_app1(handle) -> bytes | None:
    """Walk JPEG segments until the Exif APP1 marker, then return its payload."""
    while True:
        marker = handle.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        if marker[1] in (0xDA, 0xD9):  # start of scan, end of image
            return None
        length_bytes = handle.read(2)
        if len(length_bytes) < 2:
            return None
        (length,) = struct.unpack(">H", length_bytes)
        payload = handle.read(length - 2)
        if marker[1] == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return payload[6:]


def _read_ifd(data: bytes, offset: int, endian: str, tags: dict[int, str]) -> None:
    if offset <= 0 or offset + 2 > len(data):
        return
    (count,) = struct.unpack_from(endian + "H", data, offset)
    for index in range(min(count, 512)):
        entry = offset + 2 + index * 12
        if entry + 12 > len(data):
            return
        tag, kind, length = struct.unpack_from(endian + "HHI", data, entry)
        if tag == _TIFF_EXIF_IFD:
            (value,) = struct.unpack_from(endian + "I", data, entry + 8)
            tags[tag] = str(value)
            continue
        if kind != _TIFF_ASCII or length == 0 or length > 1024:
            continue
        if length <= 4:
            raw = data[entry + 8 : entry + 8 + length]
        else:
            (value_offset,) = struct.unpack_from(endian + "I", data, entry + 8)
            raw = data[value_offset : value_offset + length]
        text = raw.split(b"\x00")[0].decode("utf-8", "replace").strip()
        if text:
            tags[tag] = text
