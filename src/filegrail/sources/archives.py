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
