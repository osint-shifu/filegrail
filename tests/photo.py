"""A minimal JPEG carrying real EXIF, for tests that need one.

Shared rather than copied, so the one place that knows how an Exif APP1 segment
is laid out stays one place. Every offset is computed from the structure, never
counted by hand.
"""

from __future__ import annotations

import struct
from pathlib import Path


def jpeg_with_exif(path: Path, make: str, model: str, taken: str) -> None:
    """Build a minimal JPEG carrying an Exif APP1 segment with three ASCII tags."""
    entries = [(0x010F, make), (0x0110, model), (0x0132, taken)]

    header = b"MM\x00\x2a" + struct.pack(">I", 8)
    values = b""
    value_base = 8 + 2 + len(entries) * 12 + 4
    directory = struct.pack(">H", len(entries))
    for tag, text in entries:
        raw = text.encode("ascii") + b"\x00"
        directory += struct.pack(">HHI", tag, 2, len(raw))
        directory += struct.pack(">I", value_base + len(values))
        values += raw
    tiff = header + directory + struct.pack(">I", 0) + values

    app1 = b"Exif\x00\x00" + tiff
    path.write_bytes(
        b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"
    )
