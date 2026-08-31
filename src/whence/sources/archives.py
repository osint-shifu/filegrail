"""Propagate an archive's origin to the files extracted from it.

Extracting a download breaks the chain: the archive carries a browser record,
the files inside carry nothing. Matching archive members against files on disk
restores the link, which is often the difference between a directory with no
recorded origin and a complete answer.

Members are matched on name and uncompressed size. That is deliberately strict
enough to avoid claiming an origin for an unrelated file with a common name,
and the resulting origin is reported below a direct download.
"""

from __future__ import annotations

import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path

from ..models import Origin

ARCHIVE_SUFFIXES = {".zip", ".whl", ".jar", ".tar", ".tgz", ".gz", ".bz2", ".xz"}

# Cap the work done on a single archive; a member list is cheap, but a
# deliberately hostile archive should not be able to stall a scan.
_MAX_MEMBERS = 50_000


def is_archive(path: Path) -> bool:
    return path.suffix.lower() in ARCHIVE_SUFFIXES


def list_members(path: Path) -> dict[str, int]:
    """Return {member name: uncompressed size} without extracting anything."""
    members: dict[str, int] = {}
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist()[:_MAX_MEMBERS]:
                    if not info.is_dir():
                        members[Path(info.filename).name] = info.file_size
            return members

        if tarfile.is_tarfile(path):
            with tarfile.open(path) as archive:
                for count, info in enumerate(archive):
                    if count >= _MAX_MEMBERS:
                        break
                    if info.isfile():
                        members[Path(info.name).name] = info.size
            return members
    except (OSError, zipfile.BadZipFile, tarfile.TarError, EOFError, ValueError):
        return {}

    return members


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
