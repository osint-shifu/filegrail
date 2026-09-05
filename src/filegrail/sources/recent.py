"""The desktop's list of recently used files.

Every GTK application writes to `~/.local/share/recently-used.xbel` when it
opens or saves a file, and the entry records which application it was, when, and
how many times. It is the graphical equivalent of shell history, and it answers
the same kind of question at the same kind of strength: something on this
machine handled this file at this time.

It is not a download record. An application opening a file proves contact, not
acquisition - the file may have been opened after arriving by any route at all -
so it is ranked below shell history, which at least sometimes carries the
command that fetched the bytes.

The format is the freedesktop Desktop Bookmark Specification: XBEL with a
bookmark per file. Plain XML, so no dependency and no guessing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..models import Origin

RECENT_FILES = [
    ".local/share/recently-used.xbel",
    ".recently-used.xbel",
]

_BOOKMARK_NS = "http://www.freedesktop.org/standards/desktop-bookmarks"

#: A list this long is a desktop that has been in use for years; reading all of
#: it is cheap, but building an index of everything is not what this is for.
_MAX_BOOKMARKS = 20_000


def collect_recent_files(home: Path | None = None) -> dict[str, list[Origin]]:
    """Map absolute path -> what the desktop recorded about opening it."""
    home = home or Path.home()
    found: dict[str, list[Origin]] = {}

    for relative in RECENT_FILES:
        path = home / relative
        if not path.is_file():
            continue
        try:
            root = ElementTree.fromstring(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ElementTree.ParseError):
            continue

        for index, bookmark in enumerate(root.iter("bookmark")):
            if index >= _MAX_BOOKMARKS:
                break
            target = _path(bookmark.get("href"))
            if target is None:
                continue
            origin = _origin(bookmark)
            if origin is not None:
                found.setdefault(target, []).append(origin)
    return found


def _path(href: str | None) -> str | None:
    if not href or not href.startswith("file://"):
        return None
    return unquote(urlparse(href).path) or None


def _origin(bookmark: ElementTree.Element) -> Origin | None:
    applications = [
        name
        for element in bookmark.iter(f"{{{_BOOKMARK_NS}}}application")
        if (name := element.get("name"))
    ]
    added = _timestamp(bookmark.get("added") or bookmark.get("visited"))

    if not applications and not added:
        return None

    who = ", ".join(dict.fromkeys(applications)) or "an application"
    return Origin(
        source="recent-documents",
        tool=applications[0] if applications else None,
        at=added,
        note=f"opened by {who}",
    )


def _timestamp(value: str | None) -> str | None:
    """The spec says ISO 8601; older writers used a bare Unix time."""
    if not value:
        return None
    if value.isdigit():
        from ..util import iso

        return iso(float(value))
    return value if value.endswith("Z") else f"{value.rstrip('Z')}Z"
