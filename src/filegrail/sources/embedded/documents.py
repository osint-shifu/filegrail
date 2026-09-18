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
from datetime import datetime, timedelta, timezone
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

#: The structure of the document - how many times it was saved, what it
#: attaches, what it runs, who signed it - is spread over the whole file, so
#: the whole file is scanned for it, up to this much. Past the limit only the
#: head and tail windows above are seen, which still hold the trailer.
_PDF_MAX_STRUCTURE = 64 * 1024 * 1024

#: Dictionary keys that mark a structural feature. Anchored on `/S /Name` or
#: `/Type /Name` where the key alone would also match page text.
_PDF_FEATURES: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    # Only an action dictionary written inline. A reference or an array is
    # usually the page the viewer should open on, which every document has.
    ("OpenAction", re.compile(rb"/OpenAction\s*<<")),
    ("JavaScript", re.compile(rb"/S\s*/JavaScript\b|/JS\s*(?:\(|<|\d+\s+\d+\s+R)")),
    ("Launch", re.compile(rb"/S\s*/Launch\b")),
    ("AcroForm", re.compile(rb"/AcroForm\s*(?:<<|\d+\s+\d+\s+R)")),
    ("XFA", re.compile(rb"/XFA\s*(?:\[|\d+\s+\d+\s+R|\()")),
)
_PDF_EMBEDDED = re.compile(rb"/Type\s*/EmbeddedFile\b")
_PDF_FILESPEC = re.compile(rb"/Type\s*/Filespec\b")
_PDF_SIGNATURE = re.compile(rb"/Type\s*/Sig\b")
_PDF_URI = re.compile(rb"/URI\s*\((?P<literal>(?:\\.|[^\\)])*)\)")
_PDF_TRAILER_ID = re.compile(rb"/ID\s*\[\s*<([0-9A-Fa-f\s]*)>\s*<([0-9A-Fa-f\s]*)>\s*\]")
_PDF_EOF = b"%%EOF"
_PDF_MAX_LISTED = 16

#: Keys a dictionary in an object stream may carry that the structure scan
#: reads. A stream holding none of these is page content or a font.
_PDF_STRUCTURE_HINTS = (
    b"/OpenAction",
    b"/JavaScript",
    b"/JS",
    b"/Launch",
    b"/AcroForm",
    b"/XFA",
    b"/EmbeddedFile",
    b"/Filespec",
    b"/Sig",
    b"/URI",
)

#: Values appear either as literal strings, ``/Producer (LibreOffice)``, or as
#: hex strings, ``/Producer<FEFF004C0069...>``, which is what LibreOffice and
#: several other writers actually emit. Both forms have to be read.
_PDF_ENTRY = re.compile(
    rb"/(Producer|Creator|Author|Title|Subject|Keywords|CreationDate|ModDate|Trapped)\s*"
    rb"(?:\((?P<literal>(?:\\.|[^\\)])*)\)|<(?P<hex>[0-9A-Fa-f\s]*)>)"
)
_PDF_INFO_REF = re.compile(rb"/Info\s+(\d+)\s+(\d+)\s+R\b")

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
        size = handle.seek(0, 2)
        handle.seek(0)
        if size <= _PDF_MAX_STRUCTURE:
            whole = handle.read(size)
            head = whole[:_PDF_SCAN_BYTES]
            if size > _PDF_SCAN_BYTES * 2:
                head += whole[-_PDF_SCAN_BYTES:]
        else:
            head = handle.read(_PDF_SCAN_BYTES)
            handle.seek(-_PDF_SCAN_BYTES, 2)
            head += handle.read(_PDF_SCAN_BYTES)
            whole = head

    inflated = _inflated_streams(whole)
    found = _pdf_info_fields(whole, head + inflated)
    reference = _PDF_INFO_REF.findall(whole)

    tool = found.get("Producer") or found.get("Creator")
    if found.get("Producer") and found.get("Creator") not in (None, found.get("Producer")):
        tool = f"{found['Producer']} (created in {found['Creator']})"

    notes = [f"author {found['Author']}"] if found.get("Author") else []
    notes.extend(_pdf_structure(whole, inflated, found))
    record = _origin(
        "pdf-info",
        tool,
        _parse_pdf_date(found.get("CreationDate")),
        "; ".join(notes) or None,
        found,
    )
    if record is not None and reference and found:
        number, generation = reference[-1]
        record.where = {"object": f"{number.decode()} {generation.decode()} R"}
    return record


def _pdf_info_fields(raw: bytes, fallback: bytes) -> dict[str, str]:
    """Decode the current Info object, falling back where it cannot be resolved."""
    candidates = fallback
    references = _PDF_INFO_REF.findall(raw)
    if references:
        number, generation = references[-1]
        object_pattern = re.compile(
            rb"(?:^|[\r\n])\s*"
            + re.escape(number)
            + rb"\s+"
            + re.escape(generation)
            + rb"\s+obj\b(.*?)endobj",
            re.DOTALL,
        )
        objects = object_pattern.findall(raw)
        if objects:
            candidates = objects[-1]

    found: dict[str, str] = {}
    for match in _PDF_ENTRY.finditer(candidates):
        key = match.group(1).decode("ascii")
        if match.group("hex") is not None:
            value = _decode_pdf_hex(match.group("hex"))
        else:
            value = _decode_pdf_string(match.group("literal"))
        # An empty /Producer () is common; do not let it mask a later real one.
        if value and key not in found:
            found[key] = value
    if not found and candidates is not fallback:
        return _pdf_info_fields(b"", fallback)
    return found


def _pdf_structure(raw: bytes, inflated: bytes, fields: dict[str, str]) -> list[str]:
    """What the file's structure says about its history and its contents.

    None of this is in the Info dictionary. A document saved with incremental
    updates keeps every earlier version inside itself; an attachment, an
    action that runs on opening and a signature are each a fact about the file
    that the producer string does not mention.
    """
    notes: list[str] = []
    data = raw + inflated

    saves = raw.count(_PDF_EOF)
    if b"/Linearized" in raw[:1024]:
        saves -= 1  # a linearized file writes two cross-reference sections
    if saves > 1:
        fields["IncrementalUpdates"] = str(saves - 1)
        notes.append(f"{saves - 1} incremental update{'s' if saves > 2 else ''}")

    ids = _PDF_TRAILER_ID.findall(raw)
    if ids:
        permanent, changing = (bytes(part).translate(None, delete=b" \t\r\n") for part in ids[-1])
        if permanent:
            fields["PermanentID"] = permanent.decode("ascii").lower()
        if changing:
            fields["ChangingID"] = changing.decode("ascii").lower()

    if re.search(rb"/Encrypt\s*(?:<<|\d+\s+\d+\s+R)", raw):
        fields["Encrypted"] = "yes"
        notes.append("encrypted")

    names = _pdf_filespec_names(data)
    embedded = len(_PDF_EMBEDDED.findall(data))
    if embedded or names:
        count = max(embedded, len(names))
        fields["EmbeddedFiles"] = str(count)
        for index, name in enumerate(names[:_PDF_MAX_LISTED], 1):
            fields[f"EmbeddedFile[{index}]"] = name
        notes.append(f"{count} embedded file{'s' if count > 1 else ''}")

    signatures = [
        found
        for match in _PDF_SIGNATURE.finditer(data)
        if (found := _pdf_signature(data, match.end())) is not None
    ][:_PDF_MAX_LISTED]
    if signatures:
        fields["Signatures"] = str(len(signatures))
        for index, signature in enumerate(signatures, 1):
            for name, value in signature.items():
                fields[f"Signature[{index}]:{name}"] = value
        signer = signatures[0].get("Name")
        notes.append(f"signed by {signer}" if signer else "signed")

    for name, pattern in _PDF_FEATURES:
        if pattern.search(data):
            fields[name] = "present"
            if name in ("JavaScript", "Launch"):
                notes.append(name)

    uris = list(
        dict.fromkeys(
            text
            for match in _PDF_URI.finditer(data)
            if (text := _decode_pdf_string(match.group("literal")))
        )
    )
    if uris:
        fields["URIs"] = str(len(uris))
        for index, uri in enumerate(uris[:_PDF_MAX_LISTED], 1):
            fields[f"URI[{index}]"] = uri
    return notes


def _pdf_filespec_names(data: bytes) -> list[str]:
    names: list[str] = []
    for match in _PDF_FILESPEC.finditer(data):
        window = data[max(0, match.start() - 512) : match.end() + 512]
        name = _pdf_string(window, b"UF") or _pdf_string(window, b"F")
        if name and name not in names:
            names.append(name)
    return names


def _pdf_signature(data: bytes, start: int) -> dict[str, str] | None:
    window = data[max(0, start - 1024) : start + 1024]
    found = {
        key: value
        for key in ("Name", "M", "Reason", "Location", "ContactInfo", "SubFilter")
        if (value := _pdf_string(window, key.encode("ascii")))
    }
    if "M" in found:
        found["M"] = _parse_pdf_date(found["M"]) or found["M"]
    return found or None


def _pdf_string(window: bytes, key: bytes) -> str | None:
    """The value of one string or name entry in a dictionary window."""
    match = re.search(
        rb"/"
        + key
        + rb"\s*(?:\((?P<literal>(?:\\.|[^\\)])*)\)"
        + rb"|<(?P<hex>[0-9A-Fa-f\s]*)>"
        + rb"|/(?P<name>[^\s/<>\[\]()]+))",
        window,
    )
    if not match:
        return None
    if match.group("hex") is not None:
        return _decode_pdf_hex(match.group("hex")) or None
    if match.group("name") is not None:
        return match.group("name").decode("latin-1")
    return _decode_pdf_string(match.group("literal")) or None


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
        if (
            b"/Producer" in inflated
            or b"/Creator" in inflated
            or b"/CreationDate" in inflated
            or any(hint in inflated for hint in _PDF_STRUCTURE_HINTS)
        ):
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
    """Parse a PDF date string, D:YYYYMMDDHHmmSS with an optional offset, into UTC.

    The clock is local time and the offset says whose: `-07'00'` is seven hours
    behind Greenwich, so the same instant in UTC is seven hours later. A date
    with no offset is read as UTC, which is the reading that invents the least.
    """
    if not value:
        return None
    match = re.match(
        r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?(?:Z|([+-])(\d{2})'?(\d{2})?)?",
        value.strip(),
    )
    if not match or not match.group(1):
        return None
    defaults = (0, 1, 1, 0, 0, 0)
    year, month, day, hour, minute, second = (
        int(group) if group else default
        for group, default in zip(match.groups()[:6], defaults, strict=True)
    )
    sign, hours, minutes = match.groups()[6:]
    try:
        stamp = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        if sign:
            offset = timedelta(hours=int(hours), minutes=int(minutes or 0))
            stamp = stamp - offset if sign == "+" else stamp + offset
    except (ValueError, OverflowError):
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

    record = _origin(
        "ooxml-properties", tool, _normalise_timestamp(created), "; ".join(notes) or None, fields
    )
    if record is not None:
        parts = [
            part
            for part, tree in (("docProps/core.xml", core), ("docProps/app.xml", app))
            if tree is not None
        ]
        if parts:
            record.where = {"member": ", ".join(parts)}
    return record


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
