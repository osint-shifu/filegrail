"""Write a copy of a file with its metadata taken out.

This is the only part of `filegrail` that produces a file, and it works under
the rule the rest of the tool rests on: **the original is never touched**. A
cleaned copy is written somewhere else and the source is left exactly as it was
found, which is what keeps the tool safe to point at evidence.

Removal is claimed only where it can be shown. Every stripper here is held
against the same readers that find metadata in the first place, and the caller
can re-read the copy to see whether anything survived - a claim of "cleaned"
that nobody checks is worth less than no claim at all, because somebody will
publish a file on the strength of it.

What this is not: an anonymiser. Pixels carry sensor noise, an encoder leaves
its own fingerprints, a scanner leaves its dust, and none of that is metadata.
Removing the fields is removing the fields.
"""

from __future__ import annotations

import io
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .sources.c2pa import read_c2pa_manifest
from .sources.embedded import read_embedded_metadata
from .sources.iptc import read_iptc
from .sources.xmp import read_xmp

#: JPEG markers that carry metadata rather than image data. `APP1` holds Exif
#: and XMP, `APP13` the Photoshop resource block IPTC lives in, `APP11` the
#: JUMBF box a C2PA manifest sits in, and `COM` is a free-text comment.
#: Everything else - the frame, the tables, the scan, and `APP2`'s colour
#: profile - is what makes the file an image, and is kept.
_JPEG_STRIPPED = {0xE1: "exif", 0xED: "iptc", 0xEB: "c2pa", 0xFE: "comment"}

#: `APP1` carries two different things and announces which in its first bytes,
#: so the segment is asked rather than guessed at. Naming the wrong block in a
#: report of what was removed is a small lie that is easy to avoid.
_APP1_KINDS = ((b"Exif\x00\x00", "exif"), (b"http://ns.adobe.com/xap/", "xmp"))

#: Markers that stand alone: they carry no length word after them.
_JPEG_STANDALONE = {0xD8, *range(0xD0, 0xD8), 0x01}

#: The scan, after which the entropy-coded image data runs to the end.
_JPEG_SCAN = 0xDA

#: End of image. Anything after it is outside the format, and encoders and
#: editors do append there. It is copied through rather than discarded - what
#: is not understood is not deleted - and the check afterwards is what says
#: whether something readable survived in it.
_JPEG_END = 0xD9


@dataclass(slots=True)
class Cleaned:
    """What one file gave up, and where the copy went."""

    path: Path

    #: Where the cleaned copy was written, or None when nothing was written -
    #: either because the format is not handled or because there was nothing
    #: in it to remove.
    written: Path | None = None

    #: What came out, named the way the report names metadata blocks.
    removed: list[str] = field(default_factory=list)

    #: What the readers can still see in the copy. Empty is the ordinary
    #: answer; anything in it is a warning, because a stripper is written per
    #: format and a format can carry a block somewhere the stripper does not
    #: reach - a packet appended after a JPEG's end marker, say. Somebody about
    #: to publish a file on the strength of the word "cleaned" is exactly who
    #: this is for.
    remaining: list[str] = field(default_factory=list)

    #: Why nothing was written, where that needs saying.
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        found: dict[str, object] = {"path": str(self.path), "removed": self.removed}
        if self.written:
            found["written"] = str(self.written)
        if self.note:
            found["note"] = self.note
        if self.remaining:
            found["remaining"] = self.remaining
        return found


def _under(path: Path, below: Path | None) -> Path:
    """Where the copy of `path` belongs, relative to the destination directory.

    Mirroring the tree is what keeps two files that share a name apart. A path
    that is not under `below` has no relative form and keeps its own name,
    which is also what a single file cleaned on its own gets.
    """
    if below is not None:
        try:
            return path.relative_to(below)
        except ValueError:
            pass
    return Path(path.name)


def clean_file(
    path: Path,
    destination: Path,
    *,
    below: Path | None = None,
    overwrite: bool = False,
) -> Cleaned:
    """Write `path` under `destination` without its metadata.

    `below` is the root the copies mirror: a file at `below/a/photo.jpg` is
    written to `destination/a/photo.jpg`. Without it the copy goes directly
    into `destination` under its own name, which is right for one file and
    wrong for a tree - two folders holding a `photo.jpg` would write one copy
    over the other.

    A name already taken is a refusal, not a replacement. This is the one
    command in the project that writes a file, and the destination is a
    directory the user chose, which may hold work of their own; removing
    something nobody asked about would be a worse failure than declining to
    write. `overwrite` says to go ahead.
    """
    suffix = path.suffix.lower()
    if suffix not in _STRIPPERS:
        return Cleaned(path, note="no stripper for this format")

    try:
        raw = path.read_bytes()
    except OSError as problem:
        return Cleaned(path, note=f"unreadable: {problem.strerror or problem}")

    try:
        body, removed = _STRIPPERS[suffix](raw)
    except (ValueError, struct.error):
        return Cleaned(path, note="the file could not be taken apart safely")

    if not removed:
        return Cleaned(path, note="nothing to remove")

    target = destination / _under(path, below)
    if target.exists() and not overwrite:
        return Cleaned(path, note="a file is already there; --overwrite replaces it")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    except OSError as problem:
        return Cleaned(path, note=f"could not be written: {problem.strerror or problem}")
    return Cleaned(
        path,
        written=target,
        removed=sorted(set(removed)),
        remaining=survivors(target),
    )


def survivors(path: Path) -> list[str]:
    """Which metadata blocks a reader can still find in this file.

    The same readers the rest of the tool uses, pointed at the copy. Checking
    the work with the code that does the looking is the only way the word
    "cleaned" means anything here.
    """
    found: list[str] = []
    for reader in (read_c2pa_manifest, read_embedded_metadata, read_iptc):
        claim = reader(path)
        if claim is not None:
            found.append(claim.block or claim.source)
    found.extend(origin.block or origin.source for origin in read_xmp(path))
    return sorted(set(found))


# --- JPEG --------------------------------------------------------------------


def _strip_jpeg(raw: bytes) -> tuple[bytes, list[str]]:
    """Rebuild the segment stream without the ones that carry metadata.

    A JPEG is a sequence of marker segments, and the metadata ones can simply
    be left out: nothing else refers to them by offset, so removing them shifts
    only what follows and breaks nothing.
    """
    if not raw.startswith(b"\xff\xd8"):
        raise ValueError("not a JPEG")

    kept = [b"\xff\xd8"]
    removed: list[str] = []
    offset = 2

    while offset < len(raw):
        if raw[offset] != 0xFF:
            raise ValueError("lost the marker stream")
        marker = raw[offset + 1]

        if marker in _JPEG_STANDALONE:
            kept.append(raw[offset : offset + 2])
            offset += 2
            continue
        if marker in (_JPEG_SCAN, _JPEG_END):
            # The scan runs to the end of the image, and whatever follows the
            # end marker is not ours to interpret. Both are copied verbatim.
            kept.append(raw[offset:])
            break

        (length,) = struct.unpack(">H", raw[offset + 2 : offset + 4])
        end = offset + 2 + length
        if length < 2 or end > len(raw):
            raise ValueError("a segment longer than the file")

        if marker in _JPEG_STRIPPED:
            removed.append(_jpeg_block(marker, raw[offset + 4 : end]))
        else:
            kept.append(raw[offset:end])
        offset = end

    return b"".join(kept), removed


def _jpeg_block(marker: int, payload: bytes) -> str:
    """What the segment actually holds, where the marker alone does not say."""
    if marker == 0xE1:
        for prefix, name in _APP1_KINDS:
            if payload.startswith(prefix):
                return name
        return "app1"
    return _JPEG_STRIPPED[marker]


# --- PNG ---------------------------------------------------------------------

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

#: PNG chunks that carry metadata. The three text chunks hold whatever a
#: generator wrote there, `eXIf` an Exif block, and `tIME` the last-modified
#: moment. Everything else - the header, the palette, the image data, the
#: transparency and colour chunks - is the picture.
_PNG_STRIPPED = {
    b"tEXt": "png-text",
    b"zTXt": "png-text",
    b"iTXt": "png-text",
    b"eXIf": "exif",
    b"tIME": "modification time",
}


def _strip_png(raw: bytes) -> tuple[bytes, list[str]]:
    """Rebuild the chunk stream without the ones that carry metadata.

    A PNG chunk carries its own length and CRC and nothing refers to another by
    offset, so a chunk can be dropped whole and what remains is still a PNG.
    """
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError("not a PNG")

    kept = [_PNG_MAGIC]
    removed: list[str] = []
    offset = len(_PNG_MAGIC)

    while offset + 8 <= len(raw):
        (length,) = struct.unpack(">I", raw[offset : offset + 4])
        kind = raw[offset + 4 : offset + 8]
        end = offset + 12 + length  # length, type, payload, CRC
        if end > len(raw):
            raise ValueError("a chunk longer than the file")

        if kind in _PNG_STRIPPED:
            removed.append(_PNG_STRIPPED[kind])
        else:
            kept.append(raw[offset:end])
        offset = end
        if kind == b"IEND":
            break

    return b"".join(kept), removed


# --- ISO base media: MP4, MOV and their relatives ----------------------------

#: Atoms whose children can hold metadata, walked into rather than past.
_ISOBMFF_CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl"}

#: Atoms that hold nothing but metadata, and are overwritten whole.
_ISOBMFF_STRIPPED = {b"udta": "movie metadata", b"meta": "movie metadata"}

#: A movie's sample tables address its media by absolute offset, so removing
#: bytes from the header would leave every one of them pointing somewhere else.
#: The atom keeps its length and becomes a `free` box - which is exactly what
#: the format defines for space that means nothing - and its payload is
#: overwritten, so the values are gone rather than merely unreferenced.
_ISOBMFF_FREE = b"free"


def _strip_isobmff(raw: bytes) -> tuple[bytes, list[str]]:
    body = bytearray(raw)
    removed: list[str] = []
    _walk_atoms(body, 0, len(body), 0, removed)
    return bytes(body), removed


def _walk_atoms(body: bytearray, offset: int, end: int, depth: int, removed: list[str]) -> None:
    if depth > 8:
        return
    while offset + 8 <= end:
        (length,) = struct.unpack_from(">I", body, offset)
        kind = bytes(body[offset + 4 : offset + 8])
        payload = offset + 8
        if length == 1:  # a 64-bit length follows the type
            if payload + 8 > end:
                return
            (length,) = struct.unpack_from(">Q", body, payload)
            payload += 8
        elif length == 0:
            length = end - offset
        if length < 8 or offset + length > end:
            return

        if kind in _ISOBMFF_STRIPPED:
            body[offset + 4 : offset + 8] = _ISOBMFF_FREE
            body[payload : offset + length] = bytes(offset + length - payload)
            removed.append(_ISOBMFF_STRIPPED[kind])
        elif kind == b"mvhd":
            if _blank_mvhd_times(body, payload, offset + length):
                removed.append("movie timestamps")
        elif kind in _ISOBMFF_CONTAINERS:
            _walk_atoms(body, payload, offset + length, depth + 1, removed)

        offset += length


def _blank_mvhd_times(body: bytearray, start: int, end: int) -> bool:
    """Zero the creation and modification moments the movie header carries.

    The header cannot be removed - it holds the timescale and the duration -
    but the two timestamps at the front of it are metadata like any other, and
    they sit at a fixed offset, so they can be blanked without disturbing what
    follows.
    """
    if end - start < 12:
        return False
    width = 8 if body[start] == 1 else 4
    stop = start + 4 + width * 2
    if stop > end or not any(body[start + 4 : stop]):
        return False
    body[start + 4 : stop] = bytes(width * 2)
    return True


# --- the zip-based document formats ------------------------------------------

#: Parts that hold nothing but properties, and what to leave in their place.
#: They are emptied rather than deleted: these are named in the package
#: relationships, and a part that is named and then missing is a broken
#: document rather than a clean one.
_ZIP_EMPTIED = {
    "docProps/core.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
        'metadata/core-properties"/>'
    ),
    "docProps/app.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        'extended-properties"/>'
    ),
    "docProps/custom.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        'custom-properties"/>'
    ),
    "meta.xml": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' office:version="1.3"><office:meta/></office:document-meta>'
    ),
}


def _strip_zip(raw: bytes) -> tuple[bytes, list[str]]:
    """Rewrite the package with its property parts emptied."""
    removed: list[str] = []
    source = io.BytesIO(raw)
    written = io.BytesIO()

    with (
        zipfile.ZipFile(source) as bundle,
        zipfile.ZipFile(written, "w", zipfile.ZIP_DEFLATED) as clean,
    ):
        for info in bundle.infolist():
            if info.is_dir():
                continue
            replacement = _ZIP_EMPTIED.get(info.filename)
            if replacement is not None and bundle.read(info.filename).strip():
                clean.writestr(info.filename, replacement)
                removed.append("document properties")
            else:
                clean.writestr(info.filename, bundle.read(info.filename))

    return written.getvalue(), removed


_STRIPPERS = {
    ".png": _strip_png,
    ".apng": _strip_png,
    ".jpg": _strip_jpeg,
    ".jpeg": _strip_jpeg,
    ".jpe": _strip_jpeg,
    ".mp4": _strip_isobmff,
    ".m4v": _strip_isobmff,
    ".m4a": _strip_isobmff,
    ".mov": _strip_isobmff,
    ".qt": _strip_isobmff,
    ".3gp": _strip_isobmff,
    ".docx": _strip_zip,
    ".docm": _strip_zip,
    ".dotx": _strip_zip,
    ".xlsx": _strip_zip,
    ".xlsm": _strip_zip,
    ".xltx": _strip_zip,
    ".pptx": _strip_zip,
    ".pptm": _strip_zip,
    ".odt": _strip_zip,
    ".ods": _strip_zip,
    ".odp": _strip_zip,
    ".odg": _strip_zip,
    ".ott": _strip_zip,
    ".otp": _strip_zip,
}
