"""Metadata a file carries about its own creation.

A download record says where a file came from. Embedded metadata answers the
neighbouring question - what produced it, who authored it, when, and for a
photograph or a video *where* - and it is frequently the only answer available,
because it survives copying, renaming, moving between machines and the expiry of
every browser history on the system.

Each reader lives in its own module and knows one family of containers. This
module chooses between them and turns whatever they find into an `Origin`.
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ElementTree
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ...models import Origin
from . import containers, documents, exif, id3, isobmff, png

#: A malformed container is ordinary: truncated downloads, Office lock files and
#: files with a misleading extension all land here, and none is an error.
_RECOVERABLE = (
    OSError,
    ValueError,
    struct.error,
    zipfile.BadZipFile,
    ElementTree.ParseError,
    KeyError,
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
)


def read_embedded_metadata(path: Path) -> Origin | None:
    """Return what the file says about its own creation, if anything."""
    suffix = path.suffix.lower()
    if suffix not in SUFFIXES:
        return None

    for reader in (
        _from_documents,
        _from_exif,
        _from_movie,
        _from_png,
        _from_container,
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


def _from_documents(path: Path, suffix: str) -> Origin | None:
    if suffix in documents.PDF_SUFFIXES:
        return documents.read_pdf(path)
    if suffix in documents.OOXML_SUFFIXES:
        return documents.read_ooxml(path)
    return None


def _from_exif(path: Path, suffix: str) -> Origin | None:
    if suffix not in exif.SUFFIXES:
        return None
    tags = exif.read_exif(path)
    if not tags:
        return None

    device = exif.camera(tags)
    software = _string(tags.get(exif.SOFTWARE))
    tool = device or software
    if device and software and software.lower() not in device.lower():
        tool = f"{device} (processed with {software})"

    taken = _exif_time(tags.get(exif.DATETIME_ORIGINAL) or tags.get(exif.DATETIME))

    notes = []
    artist = _string(tags.get(exif.ARTIST))
    if artist:
        notes.append(f"artist {artist}")
    lens = _string(tags.get(exif.LENS_MODEL))
    if lens and device:
        notes.append(f"lens {lens}")

    return _origin(
        "device-metadata" if device else "document-metadata",
        tool=tool,
        at=taken,
        location=_coordinates(exif.coordinates(tags)),
        note="; ".join(notes) or None,
    )


def _from_movie(path: Path, suffix: str) -> Origin | None:
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
        tool=tool,
        at=movie.created,
        location=_coordinates(movie.coordinates),
    )


def _from_png(path: Path, suffix: str) -> Origin | None:
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

    return _origin("document-metadata", tool=tool, at=created, note="; ".join(notes) or None)


def _from_container(path: Path, suffix: str) -> Origin | None:
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
        tool=found.tool,
        at=_normalise(found.created),
        note="; ".join(notes) or None,
    )


def _from_audio(path: Path, suffix: str) -> Origin | None:
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
        tool=frames.get("encoder"),
        at=_normalise(frames.get("date")),
        note="; ".join(notes) or None,
    )


# --- shared ------------------------------------------------------------------


def _origin(
    source: str,
    *,
    tool: str | None = None,
    at: str | None = None,
    location: str | None = None,
    note: str | None = None,
) -> Origin | None:
    if not any((tool, at, location, note)):
        return None
    return Origin(source=source, tool=tool, at=at, location=location, note=note)


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
