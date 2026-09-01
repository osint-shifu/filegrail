"""Per-file origin metadata written by the operating system.

Three platforms solve the same problem in three ways:

    Windows   Zone.Identifier alternate data stream (HostUrl, ReferrerUrl)
    macOS     com.apple.metadata:kMDItemWhereFroms (binary plist: [url, referrer])
    Linux     user.xdg.origin.url / user.xdg.referrer.url extended attributes

Coverage is uneven. Windows tags essentially every browser download. macOS tags
Safari and Chrome downloads. On Linux the attribute is written only by some
desktop tools and by wget/curl when explicitly asked, so it is frequently
absent - which is why the browser history is the primary source, not this.
"""

from __future__ import annotations

import configparser
import os
import plistlib
from pathlib import Path

from ..models import Origin
from ..util import read_xattr

_LINUX_ORIGIN = "user.xdg.origin.url"
_LINUX_REFERRER = "user.xdg.referrer.url"
_MACOS_WHEREFROMS = "com.apple.metadata:kMDItemWhereFroms"


def read_file_attributes(path: Path) -> list[Origin]:
    """Return origin claims carried by the file itself."""
    origins: list[Origin] = []
    for reader in (_read_zone_identifier, _read_macos_wherefroms, _read_xdg_xattrs):
        try:
            origin = reader(path)
        except (OSError, ValueError):
            continue
        if origin is not None:
            origins.append(origin)
    return origins


def _read_zone_identifier(path: Path) -> Origin | None:
    """Read the NTFS Zone.Identifier alternate data stream."""
    if os.name != "nt":
        return None

    stream = Path(f"{path}:Zone.Identifier")
    try:
        raw = stream.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(raw)
    except configparser.Error:
        return None

    if not parser.has_section("ZoneTransfer"):
        return None
    section = parser["ZoneTransfer"]
    host = section.get("HostUrl") or None
    referrer = section.get("ReferrerUrl") or None
    if not host and not referrer:
        return None

    zone = section.get("ZoneId")
    return Origin(
        source="windows-zone-identifier",
        url=host,
        referrer=referrer,
        note=f"ZoneId={zone}" if zone else None,
    )


def _read_macos_wherefroms(path: Path) -> Origin | None:
    """Read the macOS 'where from' metadata attribute.

    Under its own name on macOS, and under the `user.` namespace where a copy
    carries it onto a system that has no other namespace to put it in.
    """
    raw = read_xattr(path, _MACOS_WHEREFROMS) or read_xattr(path, f"user.{_MACOS_WHEREFROMS}")
    if raw is None:
        return None

    values = plistlib.loads(raw)
    if not isinstance(values, list) or not values:
        return None

    url = values[0] or None
    referrer = values[1] if len(values) > 1 and values[1] else None
    return Origin(source="macos-wherefroms", url=url, referrer=referrer)


def _read_xdg_xattrs(path: Path) -> Origin | None:
    """Read the freedesktop.org origin extended attributes."""

    def get(name: str) -> str | None:
        raw = read_xattr(path, name)
        return raw.decode("utf-8", "replace") or None if raw is not None else None

    url = get(_LINUX_ORIGIN)
    referrer = get(_LINUX_REFERRER)
    if not url and not referrer:
        return None
    return Origin(source="xdg-xattr", url=url, referrer=referrer)
