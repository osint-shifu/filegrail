"""Metadata the file carries inside itself.

A download record says where a file came from. Embedded metadata answers a
different question - what produced it, who authored it and when - and it is
often the only answer available, because it survives copying, renaming, moving
between machines and the expiry of every browser history on the system.

Two containers are read here with the standard library, so the tool keeps no
runtime dependencies:

    PDF     the Info dictionary: Producer, Creator, Author, CreationDate
    OOXML   docProps/core.xml and app.xml: creator, lastModifiedBy, Company

Neither reports a URL, so neither competes with a download record. They fill the
gap underneath one.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

from ...models import EvidenceRecord
from .parts import read_part

PDF_SUFFIXES = {".pdf"}
OOXML_SUFFIXES = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm", ".dotx", ".xltx"}

# Only the head of a PDF trailer is scanned; the Info dictionary lives near the
# start or the end, and reading whole multi-gigabyte files would be pointless.
_PDF_SCAN_BYTES = 512 * 1024

#: Since PDF 1.5 the Info dictionary is often inside a Flate-compressed object
#: stream, where a scan of the raw bytes cannot see it. WeasyPrint, pandoc and
#: most modern writers do this, so the compressed streams are decompressed too.
_PDF_STREAM = re.compile(rb"stream\r?\n(.*?)endstream", re.DOTALL)
_PDF_MAX_STREAMS = 64
_PDF_MAX_INFLATED = 4 * 1024 * 1024

#: Values appear either as literal strings, ``/Producer (LibreOffice)``, or as
#: hex strings, ``/Producer<FEFF004C0069...>``, which is what LibreOffice and
#: several other writers actually emit. Both forms have to be read.
_PDF_ENTRY = re.compile(
    rb"/(Producer|Creator|Author|Title|Subject|Keywords|CreationDate|ModDate|Trapped)\s*"
    rb"(?:\((?P<literal>(?:\\.|[^\\)])*)\)|<(?P<hex>[0-9A-Fa-f\s]*)>)"
)

_DC = "http://purl.org/dc/elements/1.1/"
_DCTERMS = "http://purl.org/dc/terms/"
_COREPROPS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_EXTPROPS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"


def read_pdf(path: Path) -> EvidenceRecord | None:
    """Return what a PDF says about its own creation."""
    return _read_pdf(path)


def read_ooxml(path: Path) -> EvidenceRecord | None:
    """Return what an Office Open XML document says about its own creation."""
    return _read_ooxml(path)


def _origin(
    block: str,
    tool: str | None,
    at: str | None,
    note: str | None,
    fields: dict[str, str] | None = None,
) -> EvidenceRecord | None:
    if not tool and not at and not note:
        return None
    return EvidenceRecord(
        source="document-metadata",
        block=block,
        tool=tool,
        at=at,
        note=note,
        fields=fields or {},
    )


def _read_pdf(path: Path) -> EvidenceRecord | None:
    with path.open("rb") as handle:
        head = handle.read(_PDF_SCAN_BYTES)
        if handle.seek(0, 2) > _PDF_SCAN_BYTES * 2:
            handle.seek(-_PDF_SCAN_BYTES, 2)
            head += handle.read(_PDF_SCAN_BYTES)

    found: dict[str, str] = {}
    for match in _PDF_ENTRY.finditer(head + _inflated_streams(head)):
        key = match.group(1).decode("ascii")
        if match.group("hex") is not None:
            value = _decode_pdf_hex(match.group("hex"))
        else:
            value = _decode_pdf_string(match.group("literal"))
        # An empty /Producer () is common; do not let it mask a later real one.
        if value and key not in found:
            found[key] = value

    tool = found.get("Producer") or found.get("Creator")
    if found.get("Producer") and found.get("Creator") not in (None, found.get("Producer")):
        tool = f"{found['Producer']} (created in {found['Creator']})"

    notes = [f"author {found['Author']}"] if found.get("Author") else []
    return _origin(
        "pdf-info",
        tool,
        _parse_pdf_date(found.get("CreationDate")),
        "; ".join(notes) or None,
        found,
    )


def _inflated_streams(data: bytes) -> bytes:
    """Return the concatenated contents of the Flate streams in `data`.

    Failures are ignored on purpose: most streams are page content or fonts and
    are of no interest, and a stream that will not inflate is not an error.
    """
    parts: list[bytes] = []
    budget = _PDF_MAX_INFLATED

    for index, match in enumerate(_PDF_STREAM.finditer(data)):
        if index >= _PDF_MAX_STREAMS or budget <= 0:
            break
        try:
            inflated = zlib.decompressobj().decompress(match.group(1), budget)
        except zlib.error:
            continue
        if b"/Producer" in inflated or b"/Creator" in inflated or b"/CreationDate" in inflated:
            parts.append(inflated)
            budget -= len(inflated)

    return b"".join(parts)


def _decode_pdf_hex(raw: bytes) -> str:
    """Decode a PDF hex string, ``<FEFF004C...>``, honouring the BOM if present."""
    digits = bytes(raw).translate(None, delete=b" \t\r\n")
    if len(digits) % 2:
        digits += b"0"  # the specification pads an odd final digit with zero
    try:
        data = bytes.fromhex(digits.decode("ascii"))
    except ValueError:
        return ""
    if data.startswith(b"\xfe\xff"):
        text = data[2:].decode("utf-16-be", "replace")
    else:
        text = data.decode("latin-1", "replace")
    return text.replace("\ufeff", "").strip("\x00").strip()


def _decode_pdf_string(raw: bytes) -> str:
    value = re.sub(rb"\\([()\\])", rb"\1", raw)
    if value.startswith(b"\xfe\xff"):
        text = value[2:].decode("utf-16-be", "replace")
    else:
        text = value.decode("latin-1", "replace")
    return text.replace("\ufeff", "").strip("\x00").strip()


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


def _read_ooxml(path: Path) -> EvidenceRecord | None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        core = _parse_xml(archive, names, "docProps/core.xml")
        app = _parse_xml(archive, names, "docProps/app.xml")

    fields = _ooxml_properties(core, app)

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

    return _origin(
        "ooxml-properties", tool, _normalise_timestamp(created), "; ".join(notes) or None, fields
    )


def _ooxml_properties(
    core: ElementTree.Element | None, app: ElementTree.Element | None
) -> dict[str, str]:
    """Every property either docProps part declares.

    Taken wholesale rather than by a list of interesting names. `Revision` and
    `TotalTime` are the sort of thing that turns out to matter - how many times a
    document was saved, and how long it was open - and no fixed list anticipates
    which of them an investigation will want.
    """
    found: dict[str, str] = {}
    for element in (core, app):
        if element is None:
            continue
        for child in element:
            name = child.tag.rsplit("}", 1)[-1]
            value = (child.text or "").strip()
            if value and name not in found:
                found[name] = value
    return found


def _parse_xml(
    archive: zipfile.ZipFile, names: set[str], member: str
) -> ElementTree.Element | None:
    if member not in names:
        return None
    part = read_part(archive, member)
    if part is None:
        return None
    try:
        return ElementTree.fromstring(part)
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
