"""PNG textual chunks.

PNG carries free-form key/value text in `tEXt`, `zTXt` and `iTXt` chunks. The
conventional keys name the producing software, and generative image tools have
adopted the same chunks to record the prompt and model that made the picture -
which is provenance of the most direct kind.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SUFFIXES = {".png", ".apng"}

_MAGIC = b"\x89PNG\r\n\x1a\n"
_TEXT_CHUNKS = (b"tEXt", b"zTXt", b"iTXt")
_STOP_CHUNKS = (b"IDAT", b"IEND")
_MAX_CHUNK = 1024 * 1024
_MAX_VALUE = 4096

#: Keys that name the producing tool, most specific first.
SOFTWARE_KEYS = ("Software", "Source", "Creator", "generator")
#: Keys used by generative image tools to record how the picture was made.
GENERATOR_KEYS = ("parameters", "prompt", "Comment", "workflow", "sd-metadata", "Dream")
DATE_KEYS = ("Creation Time", "create-date", "date:create")
AUTHOR_KEYS = ("Author", "Artist", "Copyright")


def read_png_text(path: Path) -> dict[str, str]:
    """Return the decoded text chunks of a PNG, keyed by their keyword."""
    found: dict[str, str] = {}
    try:
        with path.open("rb") as handle:
            if handle.read(8) != _MAGIC:
                return {}
            while True:
                header = handle.read(8)
                if len(header) < 8:
                    return found
                length, chunk_type = struct.unpack(">I4s", header)
                if chunk_type in _STOP_CHUNKS:
                    return found
                if chunk_type in _TEXT_CHUNKS and length <= _MAX_CHUNK:
                    _absorb(chunk_type, handle.read(length), found)
                    handle.read(4)  # CRC
                    continue
                handle.seek(length + 4, 1)
    except (OSError, struct.error, ValueError):
        return found


def _absorb(chunk_type: bytes, payload: bytes, found: dict[str, str]) -> None:
    keyword, separator, rest = payload.partition(b"\x00")
    if not separator:
        return
    key = keyword.decode("latin-1", "replace").strip()
    if not key or key in found:
        return

    try:
        if chunk_type == b"tEXt":
            value = rest.decode("latin-1", "replace")
        elif chunk_type == b"zTXt":
            value = zlib.decompress(rest[1:], bufsize=_MAX_VALUE).decode("latin-1", "replace")
        else:
            value = _decode_itxt(rest)
    except (zlib.error, ValueError, IndexError):
        return

    value = value.strip()
    if value:
        found[key] = value[:_MAX_VALUE]


def _decode_itxt(rest: bytes) -> str:
    """iTXt: compression flag, method, language tag, translated keyword, text."""
    if len(rest) < 2:
        return ""
    compressed, _method = rest[0], rest[1]
    body = rest[2:]
    for _ in range(2):  # skip the language tag and the translated keyword
        _, _, body = body.partition(b"\x00")
    if compressed:
        body = zlib.decompress(body, bufsize=_MAX_VALUE)
    return body.decode("utf-8", "replace")
