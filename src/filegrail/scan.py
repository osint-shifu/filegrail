"""Walk a directory and attach every origin claim that can be found for it."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path

from .lineage import attach_lineage
from .models import FileRecord, Origin
from .sources import (
    collect_browser_downloads,
    collect_quarantine_events,
    collect_recent_files,
    collect_shell_history,
    collect_sync_roots,
    collect_torrents,
    collect_windows_recent,
    inherited_origin,
    is_archive,
    is_torrent,
    list_members,
    read_c2pa_manifest,
    read_contents,
    read_embedded_metadata,
    read_file_attributes,
    read_iptc,
    read_mail,
    read_messenger_name,
    read_quarantine,
    read_shortcuts,
    read_sidecar,
    read_sync,
    read_torrent,
    read_xmp,
)
from .util import basename, birth_time, iso, sha256_file

#: Directory names a scan does not descend into. They hold build output, caches
#: and vendored copies - thousands of files that say nothing about how anything
#: reached this machine, and whose presence would bury the report.
#:
#: It is a default and not a claim about what evidence is. An evidence directory
#: may perfectly well be called `build`, so every skip is named in the report
#: rather than made silently, and `--no-skip` turns the list off.
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


@dataclass(slots=True)
class Unsearched:
    """The directories the walk did not look inside, and which kind of not.

    Two answers a report must not merge. A directory skipped for its name is a
    choice this tool made and can be told not to make; a directory that could
    not be read is a hole in the evidence. `no findings` is a claim about files
    that were looked at, and neither of these produced any.
    """

    unreadable: list[str] = field(default_factory=list)
    by_name: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.unreadable or self.by_name)

    def to_dict(self) -> dict[str, list[str]]:
        return {"unreadable": self.unreadable, "skipped_by_name": self.by_name}


def iter_files(
    root: Path,
    *,
    recursive: bool = True,
    follow_symlinks: bool = False,
    suffixes: set[str] | None = None,
    skip_names: bool = True,
    unsearched: Unsearched | None = None,
) -> Iterator[Path]:
    """Yield the files a scan should consider.

    `suffixes` narrows by extension. It is applied here rather than after the
    walk so an excluded file is never opened, never hashed and never parsed.
    """

    def wanted(path: Path) -> bool:
        return suffixes is None or path.suffix.lower() in suffixes

    def note_unreadable(error: OSError) -> None:
        """`os.walk` swallows these by default, and a swallowed one is a hole."""
        if unsearched is not None and error.filename:
            unsearched.unreadable.append(str(error.filename))

    if root.is_file():
        if wanted(root):
            yield root
        return

    for directory, subdirectories, filenames in os.walk(
        root, followlinks=follow_symlinks, onerror=note_unreadable
    ):
        keep = []
        for name in sorted(subdirectories):
            if skip_names and (name in SKIP_DIRECTORIES or name.endswith(".repro")):
                if unsearched is not None:
                    unsearched.by_name.append(str(Path(directory) / name))
                continue
            keep.append(name)
        subdirectories[:] = keep
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
    skip_names: bool = True,
    unsearched: Unsearched | None = None,
) -> list[FileRecord]:
    """Build a FileRecord for every file under root.

    When `stats` is given it collects how much source material was available,
    which lets the caller explain a result of zero rather than leave the user
    guessing whether the tool failed.
    """
    root = root.resolve()
    files = list(
        iter_files(
            root,
            recursive=recursive,
            suffixes=suffixes,
            skip_names=skip_names,
            unsearched=unsearched,
        )
    )

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
    quarantined = collect_quarantine_events(home=home)
    shortcuts = collect_windows_recent(home=home)
    synced = collect_sync_roots(home=home)

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
        record.origins.extend(read_quarantine(path, quarantined))
        if sidecar := read_sidecar(path):
            record.origins.append(sidecar)
        if named := read_messenger_name(path):
            record.origins.append(named)
        if in_sync := read_sync(path, synced):
            record.origins.append(in_sync)
        # A block found by sweeping an archive's raw bytes is a member's, not
        # the container's: a zip is not made by Photoshop because a photograph
        # inside it was. The members are read under their own names instead.
        if is_archive(path):
            if follow_archives:
                record.origins.extend(read_contents(path))
        else:
            for reader in (read_c2pa_manifest, read_embedded_metadata, read_iptc):
                claim = reader(path)
                if claim is not None:
                    record.origins.append(claim)
            record.origins.extend(read_xmp(path))
        record.origins.extend(read_mail(path))
        record.origins.extend(history.get(path.name, []))
        record.origins.extend(recent.get(str(path), []))
        record.origins.extend(read_shortcuts(path, stat.st_size, shortcuts))
        records.append(record)

    if follow_archives:
        _attach_archive_origins(records, downloads, downloads_by_name)
    _attach_torrent_origins(records, files, home)
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


def _attach_torrent_origins(
    records: list[FileRecord], files: list[Path], home: Path | None = None
) -> None:
    """Give a file the torrent that lists it, where one was scanned beside it.

    A torrent is paired the way an archive member is - base name and exact size
    together - because a name alone matches far too much and a size alone
    matches more. What differs is that a torrent carries an origin of its own
    rather than one to inherit, so every matching record gets it, including the
    ones that already know something about themselves: a photograph with EXIF
    is no less interesting for also having been in a torrent.
    """
    by_signature: dict[tuple[str, int], list[FileRecord]] = {}
    for record in records:
        by_signature.setdefault((Path(record.path).name, record.size), []).append(record)

    scanned = (read_torrent(path) for path in files if is_torrent(path))
    for torrent in [*(t for t in scanned if t is not None), *collect_torrents(home=home)]:
        for name, sizes in torrent.members.items():
            for size in sizes:
                for record in by_signature.get((name, size), []):
                    record.origins.append(torrent.origin)


#: Why a name match was needed, for a source that recorded where the file was
#: saved. A match on the name means it is no longer there.
MOVED = "the file was moved or renamed since download"


def matched_by_name(origin: Origin, size: int, because: str = MOVED) -> Origin:
    """Copy an origin, recording that it was matched by name and not by path.

    A name match is made on purpose: it survives the file being moved or
    renamed, which is exactly when a path match fails. But it also matches a
    different file that happens to share the name, so where the record kept a
    byte count it is checked - a size that agrees is corroboration the name
    alone cannot give, and one that disagrees very likely means this is not the
    file the record is about.

    Why the name was all there was differs by source, so the caller says, and
    a caller whose own note has already said it passes nothing. A download
    record keeps the path the file was saved to, and a name match there really
    does mean it has moved; a quarantine row keeps the URL and no path at all,
    and saying it moved would describe a disagreement between two things where
    only one of them exists.
    """
    reason = f"; {because}" if because else ""
    note = f"matched by file name{reason}"
    if origin.bytes:
        if origin.bytes == size:
            note = f"matched by file name and size{reason}"
        else:
            note = (
                f"matched by file name, but the recorded size differs "
                f"({origin.bytes} bytes recorded, {size} on disk)"
            )
    return replace(origin, note=f"{origin.note}; {note}" if origin.note else note)
