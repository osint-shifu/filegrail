from __future__ import annotations

from .archives import inherited_origin, is_archive, list_members, read_contents
from .browser import collect_browser_downloads
from .c2pa import read_c2pa_manifest
from .embedded import read_embedded_metadata
from .fsattrs import read_file_attributes
from .iptc import read_iptc
from .mail import read_mail
from .messenger import read_messenger_name
from .quarantine import collect_quarantine_events, read_quarantine
from .recent import collect_recent_files
from .shell import collect_shell_history
from .shortcut import collect_windows_recent, read_shortcuts
from .sidecar import read_sidecar
from .sync import SyncRoot, collect_sync_roots, read_sync
from .torrent import Torrent, collect_torrents, is_torrent, read_torrent
from .xmp import read_xmp

__all__ = [
    "collect_browser_downloads",
    "read_file_attributes",
    "read_embedded_metadata",
    "read_c2pa_manifest",
    "read_iptc",
    "read_mail",
    "read_messenger_name",
    "read_xmp",
    "collect_shell_history",
    "collect_recent_files",
    "collect_quarantine_events",
    "read_quarantine",
    "collect_windows_recent",
    "read_shortcuts",
    "SyncRoot",
    "collect_sync_roots",
    "read_sync",
    "Torrent",
    "collect_torrents",
    "is_torrent",
    "read_torrent",
    "read_sidecar",
    "is_archive",
    "list_members",
    "read_contents",
    "inherited_origin",
]
