from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

_EPOCH_1601_OFFSET = 11_644_473_600  # seconds between 1601-01-01 and 1970-01-01

#: A drive letter or a UNC prefix: the two ways a path says it is a Windows one.
_WINDOWS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")


def basename(recorded: str) -> str:
    """The file name out of a path that another machine may have written.

    `Path` knows only the separator of the machine reading it, so a Windows
    download record split with `PosixPath` has no directory at all and its
    whole spelling comes back as the name. Under `--home` that is the ordinary
    case rather than a curiosity, and it makes every name match silently fail.

    A backslash counts as a separator only where the path announces itself as a
    Windows one, because a backslash is a legal character in a POSIX file name
    and mangling those would trade one silent failure for another.
    """
    if _WINDOWS_PATH.match(recorded):
        return PureWindowsPath(recorded).name
    return PurePosixPath(recorded).name


def iso(ts: float | None) -> str | None:
    """Format a POSIX timestamp as UTC ISO-8601, or None."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def chrome_time(value: int | None) -> str | None:
    """Chromium stores microseconds since 1601-01-01 UTC."""
    if not value:
        return None
    return iso(value / 1_000_000 - _EPOCH_1601_OFFSET)


def firefox_time(value: int | None) -> str | None:
    """Firefox stores microseconds since the Unix epoch."""
    if not value:
        return None
    return iso(value / 1_000_000)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def birth_time(path: Path) -> float | None:
    """Return the file creation time where the platform exposes one.

    macOS and Windows report it through os.stat. Linux needs statx(2), which
    CPython does not expose, so it is read directly when available.
    """
    try:
        stat = path.stat()
    except OSError:
        return None

    for attribute in ("st_birthtime", "st_ctime"):
        if attribute == "st_birthtime" and hasattr(stat, "st_birthtime"):
            return float(stat.st_birthtime)
        if attribute == "st_ctime" and os.name == "nt":
            return float(stat.st_ctime)

    return _statx_btime(path)


class _StatxTimestamp(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_int64),
        ("tv_nsec", ctypes.c_uint32),
        ("__reserved", ctypes.c_int32),
    ]


class _Statx(ctypes.Structure):
    _fields_ = [
        ("stx_mask", ctypes.c_uint32),
        ("stx_blksize", ctypes.c_uint32),
        ("stx_attributes", ctypes.c_uint64),
        ("stx_nlink", ctypes.c_uint32),
        ("stx_uid", ctypes.c_uint32),
        ("stx_gid", ctypes.c_uint32),
        ("stx_mode", ctypes.c_uint16),
        ("__spare0", ctypes.c_uint16),
        ("stx_ino", ctypes.c_uint64),
        ("stx_size", ctypes.c_uint64),
        ("stx_blocks", ctypes.c_uint64),
        ("stx_attributes_mask", ctypes.c_uint64),
        ("stx_atime", _StatxTimestamp),
        ("stx_btime", _StatxTimestamp),
        ("stx_ctime", _StatxTimestamp),
        ("stx_mtime", _StatxTimestamp),
        ("stx_rdev_major", ctypes.c_uint32),
        ("stx_rdev_minor", ctypes.c_uint32),
        ("stx_dev_major", ctypes.c_uint32),
        ("stx_dev_minor", ctypes.c_uint32),
        ("__spare2", ctypes.c_uint64 * 14),
    ]


_STATX_BTIME = 0x800
_AT_FDCWD = -100


def _statx_btime(path: Path) -> float | None:
    """Read stx_btime via statx(2). Returns None when unsupported."""
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
        statx = libc.statx
    except (OSError, AttributeError):
        return None

    buffer = _Statx()
    result = statx(
        ctypes.c_int(_AT_FDCWD),
        ctypes.c_char_p(os.fsencode(str(path))),
        ctypes.c_int(0),
        ctypes.c_uint(_STATX_BTIME),
        ctypes.byref(buffer),
    )
    if result != 0 or not (buffer.stx_mask & _STATX_BTIME):
        return None
    return buffer.stx_btime.tv_sec + buffer.stx_btime.tv_nsec / 1e9
