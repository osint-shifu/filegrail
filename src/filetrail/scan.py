"""Walk a directory and attach every origin claim that can be found for it."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from .lineage import attach_lineage
from .models import FileRecord, Origin
from .sources import (
    collect_browser_downloads,
    collect_recent_files,
    collect_shell_history,
    inherited_origin,
    is_archive,
    list_members,
    read_c2pa_manifest,
    read_embedded_metadata,
    read_file_attributes,
    read_iptc,
    read_mail,
    read_xmp,
)
from .util import basename, birth_time, iso, sha256_file

SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "target",
    "dist",
    "build",
    ".cache",
}


def iter_files(
    root: Path,
    *,
    recursive: bool = True,
    follow_symlinks: bool = False,
    suffixes: set[str] | None = None,
) -> Iterator[Path]:
    """Yield the files a scan should consider.

    `suffixes` narrows by extension. It is applied here rather than after the
    walk so an excluded file is never opened, never hashed and never parsed.
    """

    def wanted(path: Path) -> bool:
        return suffixes is None or path.suffix.lower() in suffixes

    if root.is_file():
        if wanted(root):
            yield root
        return

    for directory, subdirectories, filenames in os.walk(root, followlinks=follow_symlinks):
        subdirectories[:] = [
            name
            for name in subdirectories
            if name not in SKIP_DIRECTORIES and not name.endswith(".repro")
        ]
        for name in sorted(filenames):
            path = Path(directory) / name
            if path.is_file() and wanted(path) and (follow_symlinks or not path.is_symlink()):
                yield path
        if not recursive:
            break


def scan(
    root: Path,
    *,
    recursive: bool = True,
    hash_files: bool = False,
    use_shell_history: bool = True,
    follow_archives: bool = True,
    suffixes: set[str] | None = None,
    home: Path | None = None,
    stats: dict[str, int] | None = None,
) -> list[FileRecord]:
    """Build a FileRecord for every file under root.

    When `stats` is given it collects how much source material was available,
    which lets the caller explain a result of zero rather than leave the user
    guessing whether the tool failed.
    """
    root = root.resolve()
    files = list(iter_files(root, recursive=recursive, suffixes=suffixes))

    downloads = collect_browser_downloads(home=home, stats=stats)
    # Browsers record the path at download time; index by name too so a file
    # that was later moved into the case directory still resolves. The record
    # keeps the path as its own operating system spelled it, which is why the
    # name is taken with `basename` and not with `Path`.
    downloads_by_name: dict[str, list] = {}
    for target, origins in downloads.items():
        downloads_by_name.setdefault(basename(target), []).extend(origins)

    history = (
        collect_shell_history({path.name for path in files}, home=home) if use_shell_history else {}
    )
    recent = collect_recent_files(home=home)

    records: list[FileRecord] = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue

        record = FileRecord(
            path=str(path),
            size=stat.st_size,
            mtime=iso(stat.st_mtime) or "",
            btime=iso(birth_time(path)),
            sha256=sha256_file(path) if hash_files else None,
        )

        exact = downloads.get(str(path), [])
        record.origins.extend(exact)
        if not exact:
            for origin in downloads_by_name.get(path.name, []):
                record.origins.append(matched_by_name(origin, stat.st_size))

        record.origins.extend(read_file_attributes(path))
        for reader in (read_c2pa_manifest, read_embedded_metadata, read_iptc):
            claim = reader(path)
            if claim is not None:
                record.origins.append(claim)
        record.origins.extend(read_xmp(path))
        record.origins.extend(read_mail(path))
        record.origins.extend(history.get(path.name, []))
        record.origins.extend(recent.get(str(path), []))
        records.append(record)

    if follow_archives:
        _attach_archive_origins(records, downloads, downloads_by_name)
    attach_lineage(records)

    return records


def _attach_archive_origins(
    records: list[FileRecord],
    downloads: dict[str, list[Origin]],
    downloads_by_name: dict[str, list[Origin]],
) -> None:
    """Give files their origin from the archive they were extracted from.

    Archives are considered whether or not they are inside the scanned tree:
    a case directory is often the *result* of unpacking a download that lives
    somewhere else entirely.
    """
    candidates: dict[str, list[Origin]] = {}
    for record in records:
        path = Path(record.path)
        if is_archive(path) and record.origins:
            candidates[str(path)] = record.origins

    for target, origins in downloads.items():
        path = Path(target)
        if is_archive(path) and path.is_file():
            candidates.setdefault(str(path), origins)

    if not candidates:
        return

    by_signature: dict[tuple[str, int], list[FileRecord]] = {}
    for record in records:
        if not record.origins:
            by_signature.setdefault((Path(record.path).name, record.size), []).append(record)
    if not by_signature:
        return

    for archive_path, origins in candidates.items():
        members = list_members(Path(archive_path))
        if not members:
            continue
        best = max(origins, key=lambda origin: origin.confidence)
        archive_name = Path(archive_path).name
        for name, sizes in members.items():
            for size in sizes:
                for record in by_signature.get((name, size), []):
                    record.origins.append(inherited_origin(best, archive_name))


def matched_by_name(origin: Origin, size: int) -> Origin:
    """Copy an origin, recording that it was matched by name and not by path.

    A name match is made on purpose: it survives the file being moved or
    renamed, which is exactly when a path match fails. But it also matches a
    different file that happens to share the name, so where the record kept a
    byte count it is checked - a size that agrees is corroboration the name
    alone cannot give, and one that disagrees very likely means this is not the
    file the record is about.
    """
    note = "matched by file name; the file was moved or renamed since download"
    if origin.bytes:
        if origin.bytes == size:
            note = "matched by file name and size; the file was moved or renamed since download"
        else:
            note = (
                f"matched by file name, but the recorded size differs "
                f"({origin.bytes} bytes recorded, {size} on disk)"
            )
    return replace(origin, note=f"{origin.note}; {note}" if origin.note else note)
