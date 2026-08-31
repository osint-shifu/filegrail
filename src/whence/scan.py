"""Walk a directory and attach every origin claim that can be found for it."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from .models import FileRecord, Origin
from .sources import collect_browser_downloads, collect_shell_history, read_file_attributes
from .util import birth_time, iso, sha256_file

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
    root: Path, *, recursive: bool = True, follow_symlinks: bool = False
) -> Iterator[Path]:
    if root.is_file():
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
            if path.is_file() and (follow_symlinks or not path.is_symlink()):
                yield path
        if not recursive:
            break


def scan(
    root: Path,
    *,
    recursive: bool = True,
    hash_files: bool = False,
    use_shell_history: bool = True,
    home: Path | None = None,
) -> list[FileRecord]:
    """Build a FileRecord for every file under root."""
    root = root.resolve()
    files = list(iter_files(root, recursive=recursive))

    downloads = collect_browser_downloads(home=home)
    # Browsers record the path at download time; index by name too so a file
    # that was later moved into the case directory still resolves.
    downloads_by_name: dict[str, list] = {}
    for target, origins in downloads.items():
        downloads_by_name.setdefault(Path(target).name, []).extend(origins)

    history = (
        collect_shell_history({path.name for path in files}, home=home) if use_shell_history else {}
    )

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
                record.origins.append(_matched_by_name(origin))

        record.origins.extend(read_file_attributes(path))
        record.origins.extend(history.get(path.name, []))
        records.append(record)

    return records


def _matched_by_name(origin: Origin) -> Origin:
    """Copy an origin, recording that it was matched by name and not by path."""
    note = "matched by file name; the file was moved or renamed since download"
    return replace(origin, note=f"{origin.note}; {note}" if origin.note else note)
