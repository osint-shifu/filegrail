"""Metadata a file carries about its own creation.

A download record says where a file came from. Embedded metadata answers the
neighbouring question - what produced it, who authored it, when, and for a
photograph or a video *where* - and it is frequently the only answer available,
because it survives copying, renaming, moving between machines and the expiry of
every browser history on the system.

Each reader lives in its own module and knows one family of containers. This
module chooses between them and turns whatever they find into an `EvidenceRecord`.
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ElementTree
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ...models import EvidenceRecord
from . import (
    containers,
    documents,
    exif,
    id3,
    isobmff,
    jpeg,
    matroska,
    ole,
    photoshop,
    png,
    riff,
    vorbis,
    web,
)

#: A malformed container is ordinary: truncated downloads, Office lock files and
#: files with a misleading extension all land here, and none is an error.
_RECOVERABLE = (
    OSError,
    ValueError,
    struct.error,
    zipfile.BadZipFile,
    ElementTree.ParseError,
    KeyError,
    # A package may name a compression method this interpreter cannot undo, and
    # `zipfile` says so with `NotImplementedError` - two patched bytes per
    # member, and none of the types above describes it.
    NotImplementedError,
)

#: Every suffix any reader here claims. Used to skip files quickly.
SUFFIXES = (
    documents.PDF_SUFFIXES
    | documents.OOXML_SUFFIXES
    | exif.SUFFIXES
    | png.SUFFIXES
    | isobmff.SUFFIXES
    | containers.SUFFIXES
    | id3.SUFFIXES
    | riff.SUFFIXES
    | matroska.SUFFIXES
    | vorbis.SUFFIXES
    | ole.SUFFIXES
    | photoshop.SUFFIXES
    | web.SUFFIXES
)


def read_embedded_metadata(path: Path) -> EvidenceRecord | None:
    """Return what the file says about its own creation, if anything."""
    suffix = path.suffix.lower()
    if suffix not in SUFFIXES:
        return None

    for reader in (
        _from_documents,
        _from_web,
        _from_exif,
        _from_photoshop,
        _from_movie,
        _from_png,
        _from_container,
        _from_compound,
        _from_riff,
        _from_matroska,
        _from_vorbis,
        _from_audio,
    ):
        try:
            origin = reader(path, suffix)
        except _RECOVERABLE:
            continue  # one unreadable container must not end the scan
        if origin is not None:
            return origin
    return None


# --- per family --------------------------------------------------------------


def _from_documents(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix in documents.PDF_SUFFIXES:
        return documents.read_pdf(path)
    if suffix in documents.OOXML_SUFFIXES:
        return documents.read_ooxml(path)
    return None


def _from_web(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in web.SUFFIXES:
        return None
    found = web.read_web_document(path)
    if not found:
        return None

    fields = found.fields
    author = _first(
        fields,
        (
            "author",
            "article:author",
            "citation_author",
            "dc.creator",
            "dcterms.creator",
            "jsonld:author",
        ),
    )
    publisher = _first(fields, ("publisher", "og:site_name", "jsonld:publisher"))
    title = _first(fields, ("title", "og:title", "twitter:title", "jsonld:headline", "jsonld:name"))
    canonical = _first(fields, ("canonical", "og:url", "jsonld:url"))
    published = _first(
        fields,
        (
            "datePublished",
            "article:published_time",
            "citation_publication_date",
            "dcterms.issued",
            "dcterms.date",
            "date",
            "jsonld:datePublished",
        ),
    )

    notes = []
    if author:
        notes.append(f"author {_clip(author, 80)}")
    if publisher:
        notes.append(f"publisher {_clip(publisher, 80)}")
    if title:
        notes.append(f"title {_clip(title, 80)}")
    if not notes and canonical:
        notes.append(f"canonical {_clip(canonical, 120)}")

    # An image or URL declared by the page is useful as a pivot even when the
    # page omitted title and authorship.  A language or description by itself
    # is not enough to create a provenance record at the top of the report.
    if not notes and any(
        name in fields
        for name in (
            "og:image",
            "og:video",
            "og:audio",
            "twitter:image",
            "twitter:player",
            "jsonld:image",
            "jsonld:video",
            "jsonld:audio",
            "jsonld:contentUrl",
            "jsonld:embedUrl",
        )
    ):
        notes.append("linked media recorded")

    return _origin(
        "document-metadata",
        block="web-document",
        tool=_first(fields, ("generator", "application-name")),
        at=_normalise(published),
        note="; ".join(notes) or None,
        fields=dict(fields),
    )


def _from_exif(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in exif.SUFFIXES:
        return None
    tags = exif.read_exif(path)
    jpeg_metadata = jpeg.read_jpeg_metadata(path) if suffix in jpeg.SUFFIXES else None
    photoshop_metadata = (
        photoshop.read_photoshop_metadata(path)
        if suffix in photoshop.JPEG_SUFFIXES | photoshop.TIFF_SUFFIXES
        else None
    )
    if not tags and not jpeg_metadata and not photoshop_metadata:
        return None
    tags = tags or exif.Exif()

    device = exif.camera(tags)
    software = _string(tags.get(exif.SOFTWARE))
    tool = device or software or (photoshop_metadata.tool if photoshop_metadata else None)
    if device and software and software.lower() not in device.lower():
        tool = f"{device} (processed with {software})"

    taken = _exif_time(tags.get(exif.DATETIME_ORIGINAL) or tags.get(exif.DATETIME))
    location = _coordinates(exif.coordinates(tags))

    notes = []
    artist = _string(tags.get(exif.ARTIST))
    if artist:
        notes.append(f"artist {artist}")
    lens = _string(tags.get(exif.LENS_MODEL))
    if lens and device:
        notes.append(f"lens {lens}")
    if jpeg_metadata and jpeg_metadata.icc_description and jpeg_metadata.icc_evidence:
        notes.append(f"ICC profile {_clip(jpeg_metadata.icc_description, 80)}")
    elif jpeg_metadata and jpeg_metadata.icc_evidence:
        notes.append("ICC profile recorded")
    if jpeg_metadata and jpeg_metadata.jfxx_thumbnail:
        notes.append("JFXX thumbnail present")
    if photoshop_metadata and photoshop_metadata.note:
        notes.append(photoshop_metadata.note)

    fields = _exif_fields(tags)
    if jpeg_metadata:
        fields.update(jpeg_metadata.fields)
    if photoshop_metadata:
        fields.update(photoshop_metadata.fields)

    return _origin(
        "device-metadata" if device else "document-metadata",
        block="exif" if tags or jpeg_metadata else "photoshop-irb",
        tool=tool,
        at=taken,
        geo=location,
        note="; ".join(notes) or None,
        fields=fields,
    )


def _from_photoshop(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in photoshop.DOCUMENT_SUFFIXES:
        return None
    found = photoshop.read_photoshop_metadata(path)
    if not found:
        return None
    return _origin(
        "document-metadata",
        block="photoshop-irb",
        tool=found.tool,
        note=found.note,
        fields=dict(found.fields),
    )


def _exif_fields(tags: exif.Exif) -> dict[str, str]:
    """Every decoded tag, named where the name is known.

    Unnamed tags keep their hex code rather than being dropped. They are mostly
    camera settings, but "mostly" is not a basis for discarding evidence, and a
    reader who does not recognise `0x9c9b` can still look it up.

    Maker notes are the one thing genuinely not reachable here: they are
    vendor-specific, undocumented and would need a parser per manufacturer.
    """
    found: dict[str, str] = {}
    for names, source in ((exif.TAG_NAMES, tags), (exif.GPS_TAG_NAMES, tags.gps)):
        for tag, value in source.items():
            found[names.get(tag, f"0x{tag:04x}")] = _plain(value)
    return found


def _plain(value: object) -> str:
    """A tag value as text, without float noise like 4.699999999999999."""
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(_plain(item) for item in value)
    return str(value)


def _from_movie(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in isobmff.SUFFIXES:
        return None
    movie = isobmff.read_movie(path)
    if not movie:
        return None

    device = " ".join(part for part in (movie.make, movie.model) if part) or None
    tool = device or movie.encoder
    if device and movie.encoder:
        tool = f"{device} (encoded with {movie.encoder})"

    return _origin(
        "device-metadata" if device else "document-metadata",
        block="isobmff",
        tool=tool,
        at=movie.created,
        geo=_coordinates(movie.coordinates),
        fields={
            name: str(value)
            for name, value in (
                ("Encoder", movie.encoder),
                ("Make", movie.make),
                ("Model", movie.model),
                ("CreationTime", movie.created),
                ("Location", _coordinates(movie.coordinates)),
            )
            if value
        },
    )


def _from_png(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in png.SUFFIXES:
        return None
    text = png.read_png_text(path)
    if not text:
        return None

    tool = _first(text, png.SOFTWARE_KEYS)
    created = _first(text, png.DATE_KEYS)
    author = _first(text, png.AUTHOR_KEYS)

    notes = []
    if author:
        notes.append(f"author {author}")
    generation = _first(text, png.GENERATOR_KEYS)
    if generation:
        notes.append(f"generation parameters recorded: {_clip(generation)}")

    # The XMP packet is decoded by its own reader into named properties. Left
    # here it would be a second copy of the same evidence, clipped mid-element
    # and unreadable as either markup or a value.
    fields = {name: value for name, value in text.items() if name != png.XMP_KEYWORD}

    return _origin(
        "document-metadata",
        block="png-text",
        tool=tool,
        at=created,
        note="; ".join(notes) or None,
        fields=fields,
    )


def _from_container(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in containers.SUFFIXES:
        return None
    found = containers.read_container(path)
    if not found:
        return None

    notes = []
    if found.author:
        notes.append(f"author {found.author}")
    if found.title:
        notes.append(f"title {_clip(found.title, 80)}")

    return _origin(
        "document-metadata",
        block=found.block,
        tool=found.tool,
        at=_normalise(found.created),
        note="; ".join(notes) or None,
        fields=dict(found.fields),
    )


def _from_compound(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in ole.SUFFIXES:
        return None
    found = ole.read_ole(path)
    if not found:
        return None

    notes = []
    if found.author:
        notes.append(f"author {found.author}")
    if found.last_author and found.last_author != found.author:
        notes.append(f"last edited by {found.last_author}")
    if found.company:
        notes.append(f"company {found.company}")
    if found.title:
        notes.append(f"title {_clip(found.title, 80)}")
    if found.storages:
        notes.append(f"storage metadata {len(found.storages)}")
    if found.vba_storage:
        notes.append("VBA storage present")
    if found.xlm_macro_sheets:
        notes.append(f"XLM macro sheets {found.xlm_macro_sheets}")
    if found.native_streams:
        notes.append(f"embedded object streams {found.native_streams}")
    if found.orphaned_entries:
        notes.append(f"orphaned directory entries {len(found.orphaned_entries)}")
    if found.root_clsid and not notes:
        notes.append("root CLSID recorded")

    fields = {
        name: value
        for name, value in (
            ("Application", found.tool),
            ("Author", found.author),
            ("LastAuthor", found.last_author),
            ("Company", found.company),
            ("Title", found.title),
            ("Created", found.created),
            ("RootCLSID", found.root_clsid),
            ("VBAStorage", "present" if found.vba_storage else None),
            (
                "XLMMacroSheets",
                str(found.xlm_macro_sheets) if found.xlm_macro_sheets else None,
            ),
            ("Ole10NativeStreams", str(found.native_streams) if found.native_streams else None),
        )
        if value
    }
    for index, storage in enumerate(found.storages, 1):
        for name, value in (
            ("Name", storage.name),
            ("CLSID", storage.clsid),
            ("Created", storage.created),
            ("Modified", storage.modified),
        ):
            if value:
                fields[f"Storage[{index}]:{name}"] = value
    for index, embedded in enumerate(found.embedded_objects, 1):
        for name, value in (
            ("Filename", embedded.filename),
            ("SourcePath", embedded.source_path),
            ("TempPath", embedded.temp_path),
            ("Size", str(embedded.size)),
        ):
            if value:
                fields[f"EmbeddedObject[{index}]:{name}"] = value
    for index, orphaned in enumerate(found.orphaned_entries, 1):
        for name, value in (
            ("Name", orphaned.name),
            ("Type", orphaned.kind),
            ("CLSID", orphaned.clsid),
            ("Created", orphaned.created),
            ("Modified", orphaned.modified),
            ("Size", str(orphaned.size)),
        ):
            if value:
                fields[f"OrphanedEntry[{index}]:{name}"] = value

    return _origin(
        "document-metadata",
        block="ole-summary",
        tool=found.tool,
        at=_normalise(found.created),
        note="; ".join(notes) or None,
        fields=fields,
    )


def _from_riff(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in riff.SUFFIXES:
        return None
    found = riff.read_riff(path)
    if not found:
        return None

    # One machine captured the sound and another wrote the file out. Naming
    # only the second hands back the studio and loses the field.
    recorder = found.broadcast.get("Originator")
    editor = found.info.get("Software") or found.frames.get("encoder")
    tool = recorder or editor
    if recorder and editor and editor.lower() not in recorder.lower():
        tool = f"{recorder} (edited with {editor})"

    notes = []
    for label, value in (
        ("description", found.broadcast.get("Description")),
        ("artist", found.info.get("Artist") or found.frames.get("artist")),
        ("title", found.info.get("Title") or found.frames.get("title")),
        ("engineer", found.info.get("Engineer")),
        ("copyright", found.info.get("Copyright")),
    ):
        if value:
            notes.append(f"{label} {_clip(value, 80)}")

    return _origin(
        "document-metadata",
        block="riff",
        tool=tool,
        # When the recording started beats when the file was written out.
        at=_normalise(found.originated)
        or _normalise(found.info.get("DateCreated") or found.frames.get("date")),
        note="; ".join(notes) or None,
        # Each standard keeps its own names. The three can disagree, and one
        # merged dictionary would silently hide whichever was written last.
        fields=dict(found.info)
        | {f"bext:{name}": value for name, value in found.broadcast.items()}
        | {f"id3:{name}": value for name, value in found.frames.items()},
    )


def _from_matroska(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in matroska.SUFFIXES:
        return None
    found = matroska.read_matroska(path)
    if not found:
        return None

    # The library that muxed the file and the application a person used are two
    # different answers, and ffmpeg writes its own name into both - so they are
    # only named separately when they are actually different.
    writing = found.fields.get("WritingApp")
    muxing = found.fields.get("MuxingApp")
    tool = writing or muxing
    if writing and muxing and muxing.lower() != writing.lower():
        tool = f"{writing} (muxed with {muxing})"

    title = found.fields.get("Title")
    return _origin(
        "document-metadata",
        block="matroska",
        tool=tool,
        at=found.at,
        note=f"title {_clip(title, 80)}" if title else None,
        fields=dict(found.fields),
    )


def _from_vorbis(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in vorbis.SUFFIXES:
        return None
    found = vorbis.read_comments(path)
    if not found:
        return None

    # The specification calls these names case-insensitive and ffmpeg takes it
    # at its word, writing every one in lower case - so they are looked up that
    # way and kept in the record exactly as the writer wrote them.
    notes = []
    for label, name in (("artist", "ARTIST"), ("title", "TITLE"), ("engineer", "ENGINEER")):
        if value := _first(found, (name,)):
            notes.append(f"{label} {_clip(value, 80)}")

    return _origin(
        "document-metadata",
        block="vorbis-comment",
        # The vendor string is written by whatever produced the file, so it is
        # the weaker answer of the two and never the wrong one.
        tool=_first(found, ("ENCODER", "Vendor")),
        at=_normalise(_first(found, ("DATE",))),
        note="; ".join(notes) or None,
        fields=dict(found),
    )


def _from_audio(path: Path, suffix: str) -> EvidenceRecord | None:
    if suffix not in id3.SUFFIXES:
        return None
    frames = id3.read_id3(path)
    if not frames:
        return None

    notes = []
    for key, label in (("artist", "artist"), ("title", "title")):
        if frames.get(key):
            notes.append(f"{label} {_clip(frames[key], 80)}")

    return _origin(
        "document-metadata",
        block="id3",
        tool=frames.get("encoder"),
        at=_normalise(frames.get("date")),
        note="; ".join(notes) or None,
    )


# --- shared ------------------------------------------------------------------


def _origin(
    source: str,
    *,
    block: str | None,
    tool: str | None = None,
    at: str | None = None,
    geo: str | None = None,
    note: str | None = None,
    fields: dict[str, str] | None = None,
) -> EvidenceRecord | None:
    """Build a claim, or None when the reader found nothing worth reporting.

    `fields` alone is not enough: a file whose only decoded tags are resolution
    and colour space has said nothing about where it came from, and inventing a
    claim for it would put noise at the top of a provenance report.
    """
    if not any((tool, at, geo, note)):
        return None
    return EvidenceRecord(
        source=source, block=block, tool=tool, at=at, geo=geo, note=note, fields=fields or {}
    )


def _coordinates(value: tuple[float, float] | None) -> str | None:
    return f"{value[0]}, {value[1]}" if value else None


def _exif_time(value: object) -> str | None:
    """EXIF writes 'YYYY:MM:DD HH:MM:SS' with no zone; it is read as UTC."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value.strip().strip("\x00"), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise(value: str | None) -> str | None:
    if not value:
        return None
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y"):
        try:
            parsed = datetime.strptime(value.strip()[: len(pattern) + 6].rstrip("Z"), pattern)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _first(values: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for candidate, value in values.items():
            if candidate.lower() == key.lower() and value.strip():
                return value.strip()
    return None


def _clip(value: str, limit: int = 160) -> str:
    collapsed = " ".join(value.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


def _string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
