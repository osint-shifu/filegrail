"""Propagate an archive's origin to the files extracted from it.

Extracting a download breaks the chain: the archive carries a browser record,
the files inside carry nothing. Matching archive members against files on disk
restores the link, which is often the difference between a directory with no
recorded origin and a complete answer.

Members are matched on name and uncompressed size. That is deliberately strict
enough to avoid claiming an origin for an unrelated file with a common name,
and the resulting origin is reported below a direct download.

An archive may hold several members sharing a base name at different sizes -
a top-level README.md and a second one under examples/, say - so every size
seen for a name is kept, not just the last.
"""

from __future__ import annotations

import tarfile
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from ..models import Origin
from .c2pa import read_c2pa_manifest
from .embedded import SUFFIXES, read_embedded_metadata
from .iptc import read_iptc
from .xmp import read_xmp

ARCHIVE_SUFFIXES = {".zip", ".whl", ".jar", ".tar", ".tgz", ".gz", ".bz2", ".xz"}

# Cap the work done on a single archive; a member list is cheap, but a
# deliberately hostile archive should not be able to stall a scan.
_MAX_MEMBERS = 50_000


def is_archive(path: Path) -> bool:
    return path.suffix.lower() in ARCHIVE_SUFFIXES


def list_members(path: Path) -> dict[str, set[int]]:
    """Return {member base name: every uncompressed size seen for it}."""
    members: dict[str, set[int]] = {}

    def record(name: str, size: int) -> None:
        members.setdefault(Path(name).name, set()).add(size)

    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist()[:_MAX_MEMBERS]:
                    if not info.is_dir():
                        record(info.filename, info.file_size)
            return members

        if tarfile.is_tarfile(path):
            with tarfile.open(path) as archive:
                for count, info in enumerate(archive):
                    if count >= _MAX_MEMBERS:
                        break
                    if info.isfile():
                        record(info.name, info.size)
            return members
    except (OSError, zipfile.BadZipFile, tarfile.TarError, EOFError, ValueError):
        return {}

    return members


#: How many members of one archive are opened for their metadata. An archive
#: of ten thousand photographs is not read ten thousand times: the section
#: exists to say what kind of thing is in there, and the first few answer that.
_MAX_READ = 25

#: A member larger than this is not copied out to be read. The readers all seek
#: rather than slurp, but the copy that precedes them does not.
_MAX_MEMBER_BYTES = 64 * 1024 * 1024


def read_contents(path: Path) -> list[Origin]:
    """Metadata from the files inside the archive, without unpacking it.

    Each member a reader claims is copied out one at a time and read exactly as
    it would be on disk, so nothing here re-implements a format. What differs
    is the claim that comes back: it is about the archive, not about the member,
    which is why the moment and the coordinates the member carried do not
    survive into it. A photograph taken in 2008 inside a zip written last week
    does not date the zip, and its fix is not the zip's location; both stay in
    the fields, where they say whose they are.
    """
    found: list[Origin] = []
    try:
        with _opened(path) as archive:
            if archive is None:
                return []
            for name, extract in archive:
                if len(found) >= _MAX_READ:
                    break
                found.extend(_read_member(name, extract))
    except (OSError, zipfile.BadZipFile, tarfile.TarError, EOFError, ValueError):
        return found
    return found


@contextmanager
def _opened(path: Path) -> Iterator[Iterator[tuple[str, Callable[[], bytes]]] | None]:
    """Yield (member name, a callable returning its bytes) for each real file."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:

            def entries() -> Iterator[tuple[str, Callable[[], bytes]]]:
                for info in archive.infolist()[:_MAX_MEMBERS]:
                    if not info.is_dir() and info.file_size <= _MAX_MEMBER_BYTES:
                        yield info.filename, lambda i=info: archive.read(i)

            yield entries()
        return

    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:

            def entries() -> Iterator[tuple[str, Callable[[], bytes]]]:
                for count, info in enumerate(archive):
                    if count >= _MAX_MEMBERS:
                        break
                    if info.isfile() and info.size <= _MAX_MEMBER_BYTES:
                        yield info.name, lambda i=info: (archive.extractfile(i) or _EMPTY).read()

            yield entries()
        return

    yield None


class _EMPTY:
    @staticmethod
    def read() -> bytes:
        return b""


def _read_member(name: str, extract: Callable[[], bytes]) -> list[Origin]:
    """Run the ordinary readers over one member, copied out to a temporary file."""
    suffix = Path(name).suffix.lower()
    if suffix not in SUFFIXES:
        return []

    with tempfile.TemporaryDirectory(prefix="filegrail-") as room:
        copy = Path(room) / f"member{suffix}"
        try:
            copy.write_bytes(extract())
        except (OSError, zipfile.BadZipFile, tarfile.TarError, EOFError, ValueError):
            return []

        found = []
        for reader in (read_c2pa_manifest, read_embedded_metadata, read_iptc):
            claim = reader(copy)
            if claim is not None:
                found.append(claim)
        found.extend(read_xmp(copy))
        return [_about_the_archive(claim, name) for claim in found]


def _about_the_archive(origin: Origin, member: str) -> Origin:
    """Restate a member's claim as one about the archive that holds it."""
    fields = dict(origin.fields)
    if origin.geo:
        fields.setdefault("location", origin.geo)
    said = f"{member}: {origin.note}" if origin.note else member
    return replace(
        origin,
        source="archive-content",
        at=None,
        geo=None,
        bytes=None,
        sha256=None,
        note=said,
        fields=fields,
    )


def inherited_origin(origin: Origin, archive_name: str) -> Origin:
    """Rewrite an archive's origin as an origin for one of its members."""
    note = f"extracted from {archive_name}"
    return replace(
        origin,
        source="archive-member",
        bytes=None,
        mime=None,
        sha256=None,
        note=f"{origin.note}; {note}" if origin.note else note,
    )
