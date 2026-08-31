"""Terminal styling.

Hand-rolled rather than delegated to a library, because the tool takes no
runtime dependencies. Styling is applied only when the output is actually a
terminal that wants it: piping to a file, `NO_COLOR`, `TERM=dumb` and an
explicit `--no-color` all fall back to plain text with the same layout.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass

RESET = "\x1b[0m"

# 256-colour codes, chosen to stay legible on both light and dark backgrounds.
_FG = {
    "green": 71,
    "cyan": 73,
    "blue": 68,
    "magenta": 139,
    "yellow": 179,
    "red": 167,
    "grey": 245,
    "faint": 240,
    "white": 252,
}

#: Each source gets a colour, ordered roughly by how much it is trusted.
SOURCE_COLOURS = {
    "browser-download": "green",
    "windows-zone-identifier": "green",
    "macos-wherefroms": "green",
    "xdg-xattr": "green",
    "archive-member": "cyan",
    "c2pa": "magenta",
    "device-metadata": "blue",
    "document-metadata": "blue",
    "shell-history": "yellow",
    "filesystem": "faint",
}

BAR_FULL = "▰"
BAR_EMPTY = "▱"
BULLET = "●"
ARROW = "←"
RULE = "─"
MIDDOT = "·"
ELLIPSIS = "…"

_ASCII = {
    BAR_FULL: "#",
    BAR_EMPTY: ".",
    BULLET: "*",
    ARROW: "<-",
    RULE: "-",
    MIDDOT: "|",
    ELLIPSIS: "...",
}


@dataclass(frozen=True, slots=True)
class Theme:
    colour: bool
    unicode: bool
    width: int

    def paint(self, text: str, name: str, *, bold: bool = False) -> str:
        if not self.colour or not text:
            return text
        code = _FG.get(name)
        if code is None:
            return text
        prefix = "\x1b[1m" if bold else ""
        return f"{prefix}\x1b[38;5;{code}m{text}{RESET}"

    def dim(self, text: str) -> str:
        return self.paint(text, "faint")

    def bold(self, text: str) -> str:
        return f"\x1b[1m{text}{RESET}" if self.colour and text else text

    def glyph(self, symbol: str) -> str:
        return symbol if self.unicode else _ASCII.get(symbol, symbol)

    def clip(self, value: str, limit: int) -> str:
        """Collapse whitespace and truncate, with an ellipsis this theme can print."""
        collapsed = " ".join(value.split())
        if limit < 8 or len(collapsed) <= limit:
            return collapsed
        mark = self.glyph(ELLIPSIS)
        return collapsed[: limit - len(mark)] + mark

    def rule(self, width: int | None = None) -> str:
        return self.dim(self.glyph(RULE) * (width or self.width))

    def bar(self, confidence: int, slots: int = 5) -> str:
        """A five-slot meter. Colour carries the source; length carries the trust."""
        filled = max(1, round(confidence / 100 * slots))
        return self.glyph(BAR_FULL) * filled + self.glyph(BAR_EMPTY) * (slots - filled)


def detect(stream=None, *, colour: bool | None = None) -> Theme:
    """Choose a theme from the environment, honouring the usual overrides."""
    stream = stream or sys.stdout

    if colour is None:
        colour = _wants_colour(stream)

    encoding = (getattr(stream, "encoding", None) or "").lower()
    unicode_ok = "utf" in encoding or os.environ.get("LANG", "").lower().find("utf") >= 0

    width = shutil.get_terminal_size(fallback=(88, 24)).columns
    return Theme(colour=colour, unicode=unicode_ok, width=max(48, min(width, 110)))


def _wants_colour(stream) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "").lower() in ("dumb", ""):
        return bool(os.environ.get("FORCE_COLOR"))
    if os.environ.get("FORCE_COLOR"):
        return True
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False
