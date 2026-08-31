from __future__ import annotations

from .archives import inherited_origin, is_archive, list_members
from .browser import collect_browser_downloads
from .c2pa import read_c2pa_manifest
from .embedded import read_embedded_metadata
from .fsattrs import read_file_attributes
from .iptc import read_iptc
from .recent import collect_recent_files
from .shell import collect_shell_history
from .xmp import read_xmp

__all__ = [
    "collect_browser_downloads",
    "read_file_attributes",
    "read_embedded_metadata",
    "read_c2pa_manifest",
    "read_iptc",
    "read_xmp",
    "collect_shell_history",
    "collect_recent_files",
    "is_archive",
    "list_members",
    "inherited_origin",
]
