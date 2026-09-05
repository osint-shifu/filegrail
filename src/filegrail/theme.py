"""Terminal styling.

Hand-rolled rather than delegated to a library, because the tool takes no
runtime dependencies. Styling is applied only when the output is actually a
terminal that wants it: piping to a file, `NO_COLOR`, `TERM=dumb` and an
explicit `--no-color` all fall back to plain text with the same layout.

The palette is documented in `docs/DESIGN.md`. Its one rule: **colour encodes how the
tool knows, never what it found.** Every colour here names a class of evidence,
so a reader learns five of them once and can then triage a folder by eye.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass

RESET = "\x1b[0m"

#: Colour depth, resolved once from the environment.
TRUECOLOR = 3
ANSI_256 = 2
ANSI_16 = 1
NONE = 0

#: Every colour as (hex, 256-colour code, 16-colour code). Chosen to stay legible
#: on both light and dark backgrounds, which rules out the saturated end.
_PALETTE = {
    # Evidence classes, strongest first.
    "recorded": ("5faf87", 71, 32),
    "inherited": ("5fafaf", 73, 36),
    "credentialed": ("af87af", 139, 35),
    "self-reported": ("5f87af", 68, 34),
    "circumstantial": ("d7af5f", 179, 33),
    # Neutrals.
    "body": ("d0d0d0", 252, 37),
    "muted": ("8a8a8a", 245, 90),
    "faint": ("585858", 240, 90),
    "rail": ("3a3a3a", 237, 90),
    # Reserved for a claim the source itself flagged as incomplete.
    "warning": ("d7875f", 173, 33),
}

#: Which class of evidence each source belongs to. This is the whole colour
#: system: a source is coloured by who is making the claim, not by what it says.
EVIDENCE = {
    "browser-download": "recorded",
    "windows-zone-identifier": "recorded",
    "macos-wherefroms": "recorded",
    "macos-quarantine": "recorded",
    "xdg-xattr": "recorded",
    # A program wrote down where it fetched the bytes, which is the same kind
    # of claim a browser's database makes. How much the pairing to this file is
    # worth is what the rank says, not the colour.
    "ytdlp-sidecar": "recorded",
    # Both are a note another system wrote as the message passed through. How
    # much that system is worth believing is what the rank says, not the colour.
    "email-delivery": "recorded",
    "email-relay": "recorded",
    "archive-member": "inherited",
    "torrent": "inherited",
    "c2pa": "credentialed",
    "device-metadata": "self-reported",
    "xmp": "self-reported",
    "xmp-history": "self-reported",
    "iptc": "self-reported",
    "email-header": "self-reported",
    "document-metadata": "self-reported",
    "archive-content": "self-reported",
    "messenger-name": "circumstantial",
    "shell-history": "circumstantial",
    "recent-documents": "circumstantial",
    "windows-recent": "circumstantial",
    "filesystem": "faint",
}

#: How each class reads as a strength, on the meter line.
#:
#: The number behind it ranks sources against each other and stays in `--json`,
#: but printing `55` in a report invites it to be read as a probability, which
#: it never was. There is no statistical basis for `55`; there is a defensible
#: ordering of how directly a source knows what it claims.
STRENGTH = {
    "recorded": "direct",
    "inherited": "inherited",
    "credentialed": "credentialed",
    "self-reported": "self-reported",
    "circumstantial": "circumstantial",
    "faint": "weak",
}

#: How each class reads as a section heading, in the order the report uses.
EVIDENCE_HEADINGS = [
    ("recorded", "recorded by another system"),
    ("inherited", "inherited from an archive"),
    ("credentialed", "content credentials"),
    ("self-reported", "file metadata"),
    ("circumstantial", "mentioned in shell history"),
    ("faint", "filesystem timestamps only"),
]

#: Kept for callers that still speak in source names.
SOURCE_COLOURS = dict(EVIDENCE)

BAR_FULL = "▰"
BAR_EMPTY = "▱"
BULLET = "●"
ARROW = "←"
RAIL = "│"
BRANCH = "├"
LAST = "└"
FLAG = "!"
RULE = "─"
MIDDOT = "·"
ELLIPSIS = "…"

_ASCII = {
    BAR_FULL: "#",
    BAR_EMPTY: ".",
    BULLET: "*",
    ARROW: "<-",
    RAIL: "|",
    BRANCH: "+",
    LAST: "\\",
    FLAG: "!",
    RULE: "-",
    # Not "|": the rail already claims that glyph, and a separator that looks
    # like a gutter destroys the one alignment cue the ASCII layout has.
    MIDDOT: "-",
    ELLIPSIS: "...",
}


@dataclass(frozen=True, slots=True)
class Theme:
    colour: bool
    unicode: bool
    width: int
    depth: int = ANSI_256

    # -- colour --

    def paint(self, text: str, name: str, *, bold: bool = False) -> str:
        if not self.colour or not text:
            return text
        entry = _PALETTE.get(name)
        if entry is None:
            return text

        hex_value, code_256, code_16 = entry
        if self.depth >= TRUECOLOR:
            red, green, blue = (int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
            sequence = f"\x1b[38;2;{red};{green};{blue}m"
        elif self.depth >= ANSI_256:
            sequence = f"\x1b[38;5;{code_256}m"
        else:
            sequence = f"\x1b[{code_16}m"

        prefix = "\x1b[1m" if bold else ""
        return f"{prefix}{sequence}{text}{RESET}"

    def evidence(self, source: str) -> str:
        """The palette entry for a source, by the class of claim it makes."""
        return EVIDENCE.get(source, "faint")

    def dim(self, text: str) -> str:
        return self.paint(text, "faint")

    def label(self, text: str) -> str:
        return self.paint(text, "muted")

    def rail_glyph(self, symbol: str = RAIL) -> str:
        return self.paint(self.glyph(symbol), "rail")

    def wrap(self, value: str, width: int) -> list[str]:
        """Break `value` into lines no wider than `width`, losing nothing.

        Truncation is not an option here: a provenance report exists to be read,
        and a value cut off at an ellipsis is one the reader now has to fetch
        another way. Words are kept whole where they fit; a single token longer
        than the line - a URL, a hash - is split, because the alternative is a
        line that overflows the terminal.
        """
        collapsed = " ".join(value.split())
        if width < 8:
            width = 8

        lines: list[str] = []
        current = ""
        for word in collapsed.split(" "):
            while len(word) > width:
                if current:
                    lines.append(current)
                    current = ""
                lines.append(word[:width])
                word = word[width:]
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= width:
                current += f" {word}"
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def bold(self, text: str) -> str:
        return f"\x1b[1m{text}{RESET}" if self.colour and text else text

    # -- glyphs --

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

    # -- meters --

    def bar(self, confidence: int, slots: int = 5) -> str:
        """A five-slot meter. Colour carries the source; length carries the trust."""
        filled = max(1, round(confidence / 100 * slots))
        return self.glyph(BAR_FULL) * filled + self.glyph(BAR_EMPTY) * (slots - filled)

    def meter(self, confidence: int, colour: str, slots: int = 5) -> str:
        """`bar`, painted: filled slots carry the class, empty ones stay faint."""
        filled = max(1, round(confidence / 100 * slots))
        return self.paint(self.glyph(BAR_FULL) * filled, colour) + self.dim(
            self.glyph(BAR_EMPTY) * (slots - filled)
        )

    def coverage(self, done: int, total: int, slots: int = 12) -> str:
        """The run's own progress. Body colour, because it is not a claim."""
        filled = round(done / total * slots) if total else 0
        if done and not filled:
            filled = 1
        return self.paint(self.glyph(BAR_FULL) * filled, "body") + self.dim(
            self.glyph(BAR_EMPTY) * (slots - filled)
        )


def detect(stream=None, *, colour: bool | None = None) -> Theme:
    """Choose a theme from the environment, honouring the usual overrides."""
    stream = stream or sys.stdout

    if colour is None:
        colour = _wants_colour(stream)

    encoding = (getattr(stream, "encoding", None) or "").lower()
    unicode_ok = "utf" in encoding or os.environ.get("LANG", "").lower().find("utf") >= 0

    width = shutil.get_terminal_size(fallback=(88, 24)).columns
    return Theme(
        colour=colour,
        unicode=unicode_ok,
        width=max(48, min(width, 110)),
        depth=_depth() if colour else NONE,
    )


def _depth() -> int:
    """How many colours the terminal will honour."""
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return TRUECOLOR
    term = os.environ.get("TERM", "").lower()
    if "256" in term or "truecolor" in term:
        return ANSI_256
    if term in ("dumb", ""):
        return ANSI_16
    return ANSI_256


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
