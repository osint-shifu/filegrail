"""What this machine can be asked, before anything is asked of it.

`no recorded origin` has two very different meanings. It can mean the evidence
was searched and the file was not in it, which is a finding. Or it can mean the
evidence was never there to search - no browser profile readable, no extended
attributes on this filesystem, a shell that keeps no timestamps - which is not a
finding about the file at all.

The report cannot tell those apart on its own, and a reader who assumes the
first when the second is true has drawn a conclusion the tool never supported.
So this says up front what could be searched, and how far back it reaches.
"""

from __future__ import annotations

import os
import platform
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .sources.browser import (
    CHROMIUM_PROFILE_GLOBS,
    FIREFOX_PROFILE_GLOBS,
    _chromium_downloads,
    _firefox_downloads,
    _profiles,
)
from .sources.quarantine import QUARANTINE_DB, collect_quarantine_events
from .sources.recent import RECENT_FILES, collect_recent_files
from .sources.shell import HISTORY_FILES, _parse_history
from .sources.shortcut import RECENT_LINKS, collect_windows_recent
from .util import birth_time, iso, xattrs_readable


def counted(number: int, noun: str) -> str:
    """`1 shortcut`, `4 shortcuts`. Every noun this file counts is regular."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


AVAILABLE = "available"
UNAVAILABLE = "unavailable"
UNSUPPORTED = "not supported here"
PARTIAL = "partial"

#: Every source that reads a user's home directory, and the checks that report
#: it. Kept as a mapping rather than left implicit, because this file promises
#: to say what could be searched: a source a scan consults and the survey never
#: mentions makes that promise one it keeps only sometimes, which is worse than
#: not making it. A test holds this against `sources` itself.
HOME_SOURCES = {
    "collect_browser_downloads": ("Chromium family downloads", "Firefox downloads"),
    "collect_shell_history": ("Shell history",),
    "collect_recent_files": ("Recent documents",),
    "collect_quarantine_events": ("macOS quarantine database",),
    "collect_windows_recent": ("Windows Recent shortcuts",),
}


@dataclass(slots=True)
class Check:
    name: str
    state: str
    detail: str = ""


@dataclass(slots=True)
class Survey:
    checks: list[Check] = field(default_factory=list)
    horizon: list[Check] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "sources": [
                {"name": c.name, "state": c.state, "detail": c.detail} for c in self.checks
            ],
            "horizon": [{"name": c.name, "detail": c.detail} for c in self.horizon],
        }


def survey(home: Path | None = None) -> Survey:
    home = home or Path.home()
    found = Survey()
    found.checks.extend(_browsers(home, found))
    found.checks.append(_os_origin())
    found.checks.append(_shell(home, found))
    found.checks.append(_recent(home, found))
    found.checks.append(_quarantine(home, found))
    found.checks.append(_shortcuts(home))
    found.checks.append(_birth_times())
    found.checks.append(_c2pa())
    return found


# --- browsers ----------------------------------------------------------------


def _browsers(home: Path, found: Survey) -> list[Check]:
    """Every readable profile, with how far back its records reach.

    The oldest surviving record is the honest limit of what this machine can
    answer. Chromium prunes at about ninety days, so a file older than the
    horizon cannot be resolved however good the tool is.
    """
    checks: list[Check] = []
    readers = (
        ("Chromium family", CHROMIUM_PROFILE_GLOBS, _chromium_downloads),
        ("Firefox", FIREFOX_PROFILE_GLOBS, _firefox_downloads),
    )

    for label, globs, reader in readers:
        profiles = list(_profiles(home, globs))
        if not profiles:
            checks.append(Check(f"{label} downloads", UNAVAILABLE, "no profile found"))
            continue

        records = 0
        readable = 0
        oldest: str | None = None
        for profile in profiles:
            try:
                seen = list(reader(profile))
            except (sqlite3.Error, OSError):
                continue
            readable += 1
            records += len(seen)
            for _target, origin in seen:
                if origin.at and (oldest is None or origin.at < oldest):
                    oldest = origin.at

        state = AVAILABLE if readable else UNAVAILABLE
        if readable and readable < len(profiles):
            state = PARTIAL
        detail = (
            f"{counted(records, 'record')} across {readable} of {counted(len(profiles), 'profile')}"
        )
        checks.append(Check(f"{label} downloads", state, detail))

        if oldest:
            found.horizon.append(Check(f"{label} oldest record", AVAILABLE, oldest[:10]))
    return checks


# --- the rest ----------------------------------------------------------------


def _os_origin() -> Check:
    """Whether this platform's download attribute can be read at all."""
    system = platform.system()

    if system == "Windows":
        return Check("Windows Zone.Identifier", AVAILABLE, "alternate data streams")
    if system == "Darwin":
        state = AVAILABLE if xattrs_readable() else UNAVAILABLE
        return Check("macOS where-from", state, "kMDItemWhereFroms")
    if not xattrs_readable():
        return Check("XDG origin attribute", UNSUPPORTED, "no extended attributes")

    # Reading the attribute needs the filesystem to carry it, which varies per
    # mount rather than per platform, so it is tested rather than assumed.
    try:
        with tempfile.NamedTemporaryFile() as probe:
            os.setxattr(probe.name, "user.filetrail.probe", b"1")
            os.getxattr(probe.name, "user.filetrail.probe")
    except OSError:
        return Check("XDG origin attribute", UNAVAILABLE, "filesystem rejects user xattrs")
    return Check(
        "XDG origin attribute",
        AVAILABLE,
        "written by KDE tools and wget --xattr, but not by Firefox",
    )


def _shell(home: Path, found: Survey) -> Check:
    """Which history files exist, and whether any of them kept timestamps."""
    present = [name for name in HISTORY_FILES if (home / name).is_file()]
    if not present:
        return Check("Shell history", UNAVAILABLE, "no history file found")

    timed = False
    oldest: float | None = None
    for name in present:
        try:
            head = (home / name).read_text(encoding="utf-8", errors="replace")[:20000]
        except OSError:
            continue
        if head.lstrip().startswith((": 1", "#1")):
            timed = True
        for when, _command in _parse_history(home / name):
            if when is not None and (oldest is None or when < oldest):
                oldest = when

    # Only where the shell was configured to keep times. Ordering survives
    # without them, but a date does not, and one would have to be invented.
    if oldest is not None:
        stamp = iso(oldest)
        if stamp:
            found.horizon.append(Check("Shell history oldest command", AVAILABLE, stamp[:10]))

    names = ", ".join(Path(name).name for name in present)
    if timed:
        return Check("Shell history", AVAILABLE, f"{names}, with timestamps")
    return Check("Shell history", PARTIAL, f"{names}, without timestamps")


def _recent(home: Path, found: Survey) -> Check:
    """The desktop's record of which application opened which file.

    A scan reads this every time, so a survey that leaves it out understates
    what could be found. It answers a different question from the rest - what
    handled the file here, not how it arrived - and it is the only source of
    that kind, which is why its absence is worth stating rather than implying.
    """
    where = [name for name in RECENT_FILES if (home / name).is_file()]
    if not where:
        return Check("Recent documents", UNAVAILABLE, "no list found")

    opened = collect_recent_files(home)
    if not opened:
        return Check("Recent documents", PARTIAL, "a list is present but nothing could be read")

    oldest: str | None = None
    for origins in opened.values():
        for origin in origins:
            if origin.at and (oldest is None or origin.at < oldest):
                oldest = origin.at
    if oldest:
        found.horizon.append(Check("Recent documents oldest entry", AVAILABLE, oldest[:10]))

    return Check(
        "Recent documents",
        AVAILABLE,
        f"{counted(len(opened), 'file')} in {', '.join(Path(name).name for name in where)}",
    )


def _quarantine(home: Path, found: Survey) -> Check:
    """The LaunchServices record of what was downloaded and from where.

    A home directory rather than a platform: the database is the reason this
    can be asked of a copied macOS profile from anywhere, which is exactly the
    case where saying whether it was there matters most.
    """
    events = collect_quarantine_events(home)
    if not (home / QUARANTINE_DB).is_file():
        return Check("macOS quarantine database", UNAVAILABLE, "no database in this profile")
    if not events.by_uuid and not events.by_name:
        return Check("macOS quarantine database", PARTIAL, "present but nothing could be read")

    moments = sorted(claim.at for claim in events.by_uuid.values() if claim.at)
    if moments:
        found.horizon.append(Check("macOS quarantine oldest download", AVAILABLE, moments[0][:10]))
    return Check("macOS quarantine database", AVAILABLE, counted(len(events.by_uuid), "download"))


def _shortcuts(home: Path) -> Check:
    """The Windows Recent folder, which keeps a shortcut per file opened.

    No horizon: a shortcut is rewritten every time the file is opened, so the
    oldest one says when the least-recently-used file was last touched, which
    is not a limit on what the folder can answer.
    """
    if not (home / RECENT_LINKS).is_dir():
        return Check("Windows Recent shortcuts", UNAVAILABLE, "no Recent folder in this profile")

    found = collect_windows_recent(home)
    if not found:
        return Check(
            "Windows Recent shortcuts", PARTIAL, "a Recent folder with nothing readable in it"
        )
    total = sum(len(claims) for claims in found.values())
    return Check("Windows Recent shortcuts", AVAILABLE, counted(total, "shortcut"))


def _birth_times() -> Check:
    """Creation time is a filesystem feature, not an operating system one."""
    try:
        with tempfile.NamedTemporaryFile() as probe:
            found = birth_time(Path(probe.name))
    except OSError:
        found = None
    if found is None:
        return Check("Creation timestamps", UNAVAILABLE, "filesystem does not record them")
    return Check("Creation timestamps", AVAILABLE, "statx" if sys.platform == "linux" else "stat")


def _c2pa() -> Check:
    return Check(
        "C2PA signature check",
        UNAVAILABLE,
        "manifests are read; validating the certificate chain needs a crypto library",
    )
