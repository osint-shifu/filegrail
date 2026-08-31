"""The screen a bare `filetrail` prints.

Typing a tool's name and having it silently start work on the current directory
is a surprise, and in a home directory an expensive one - tens of thousands of
files, minutes of scanning, nothing asked for. So a run with no arguments
introduces the tool and says how to point it somewhere.

The shape is the one `neofetch` made familiar: a wordmark on the left, the
attributes beside it, then what you can actually type. Under the wordmark runs a
trail, read right to left - the same direction the report's `←` reads.

Two things it has to get right. It is a landing screen, not a menu, so nothing
waits for input and it works piped or in a script. And **every command it prints
must run in the shell that printed it**: suggesting `filetrail` to someone who
has not installed it is how a landing screen loses their trust on the first
thing they try.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import LICENSE, REPOSITORY, __version__
from .theme import ARROW, Theme, detect

#: Plain ASCII, so the wordmark survives a terminal that cannot print box
#: drawing and never needs a second variant.
WORDMARK = (
    r"  __ _ _     _           _ _  ",
    r" / _(_) |___| |_ _ _ __ _(_) |",
    r"|  _| | / -_)  _| '_/ _` | | |",
    r"|_| |_|_\___|\__|_| \__,_|_|_|",
)

#: Read the way the report reads: right to left, back towards a source.
TRAIL = "file {arrow} zip {arrow} download {arrow} web"

#: Below this the wordmark and the attributes cannot sit side by side.
_SIDE_BY_SIDE = 78

#: Below this there is no room for a description beside a command.
_MIN_DESCRIPTION = 14

#: Source, what it gives, confidence, and the evidence class that colours it.
SOURCES = (
    ("browser downloads", "URL, referrer, timestamp", 90, "recorded"),
    ("OS origin metadata", "Windows zone, macOS where-from", 85, "recorded"),
    ("archive membership", "the origin of the archive", 70, "inherited"),
    ("content credentials", "C2PA, signature unverified", 60, "credentialed"),
    ("embedded metadata", "EXIF/GPS, PDF, Office, video", 50, "self-reported"),
    ("shell history", "the command that named the file", 40, "circumstantial"),
)


def invocation() -> str:
    """The command that will actually work in the caller's shell.

    Someone running from a checkout has no `filetrail` on their PATH. Printing
    it at them anyway is the difference between a screen that helps and one that
    is immediately proved wrong.
    """
    if Path(sys.argv[0]).stem == "filetrail" or shutil.which("filetrail"):
        return "filetrail"

    prefix = "PYTHONPATH=src " if "src" in os.environ.get("PYTHONPATH", "") else ""
    return f"{prefix}{Path(sys.executable).name} -m filetrail.cli"


#: Examples always read `filetrail`. Repeating a long checkout invocation on
#: every line buries the descriptions and makes the screen unreadable; the one
#: line that makes `filetrail` work is printed once instead.
START = (
    ("filetrail .", "scan the folder you are standing in"),
    ("filetrail ~/Downloads", "scan any folder, recursively"),
    ("filetrail report.pdf", "one file"),
    ("filetrail --menu", "pick a view from a list"),
)

VIEWS = (
    ("filetrail . --unknown-only", "only files nothing accounts for"),
    ("filetrail . --full", "every metadata field decoded"),
    ("filetrail . --timeline", "chronological, one line per event"),
    ("filetrail . --json", "machine-readable, for piping onward"),
    ("filetrail . --redact", "strip credentials before sharing"),
)


#: Every section below the wordmark hangs off one label column, the same shape
#: the attributes use. That is the whole structure - no rules, no boxes. A
#: horizontal line between two aligned lists separates nothing that the blank
#: line above it had not already separated.
_LABEL = 9

#: Flags are shown as flags. Repeating `filetrail . ` in front of each one costs
#: twelve columns on every line and teaches nothing after the first.
COMMANDS = (
    ("filetrail .", "scan the folder you are standing in"),
    ("filetrail ~/Downloads", "any folder, recursively"),
    ("filetrail report.pdf", "one file"),
    ("filetrail --menu", "pick a view from a list"),
)

FLAGS = (
    ("--unknown-only", "only files nothing accounts for"),
    ("--brief", "summarise instead of listing every field"),
    ("--timeline", "chronological, one line per event"),
    ("--json", "machine-readable, for piping onward"),
    ("--redact", "strip credentials before sharing"),
    ("--type image", "only images; also video, audio, document, archive"),
    ("--ext jpg,pdf", "only these extensions"),
    ("--identify", "emails, domains, addresses, coordinates"),
)


def render(theme: Theme | None = None) -> str:
    theme = theme or detect()
    run = invocation()

    # One body-column width for the whole screen, so every description starts on
    # the same vertical line. Computing it per section is what makes a layout
    # look almost aligned, which reads worse than not aligning it at all.
    described = [*COMMANDS, *FLAGS, ("filetrail <path> [options]", "-")]
    column = min(max(len(body) for body, _ in described), theme.width - _LABEL - 22)

    lines = ["", *_head(theme), ""]
    if run != "filetrail":
        lines.extend(_install(theme, run, column))
    lines.extend(_usage(theme, column))
    lines.extend(_sources(theme))
    lines.append(_row(theme, "help", "filetrail --help", "every flag and what it does", column))
    lines.append("")
    return "\n".join(lines)


def _row(theme: Theme, label: str, body: str, detail: str = "", column: int = 0) -> str:
    """One line of the two-column spine that runs the length of the screen."""
    prefix = f"  {theme.label(label.ljust(_LABEL))} "
    room = theme.width - _LABEL - 5

    # A body longer than the shared column keeps its full length and gives up its
    # description, rather than being cut in half to protect the alignment.
    if not detail or len(body) > column:
        return f"{prefix}{theme.paint(theme.clip(body, room), 'body')}"

    text = theme.paint(body.ljust(column), "body")
    return f"{prefix}{text}  {theme.dim(theme.clip(detail, room - column - 2))}"


def _install(theme: Theme, run: str, column: int) -> list[str]:
    """What makes the examples below work, said once and never repeated.

    Without it the screen prints commands the reader's shell rejects, which is
    the fastest way to make everything else on it look untrustworthy.
    """
    return [
        _row(theme, "install", "pipx install filetrail", "to get the bare command", column),
        _row(theme, "", f"alias filetrail='{run}'"),
        "",
    ]


def _usage(theme: Theme, column: int) -> list[str]:
    lines = [
        _row(theme, "usage", "filetrail <path> [options]", "there is no default path", column),
        "",
    ]
    lines.extend(_row(theme, "", command, detail, column) for command, detail in COMMANDS)
    lines.append("")
    lines.extend(_row(theme, "", flag, detail, column) for flag, detail in FLAGS)
    lines.append("")
    return lines


# --- the head ----------------------------------------------------------------


def _rows() -> tuple[tuple[str, str], ...]:
    return (
        ("repository", REPOSITORY.split("//", 1)[-1]),
        ("license", LICENSE),
        ("version", __version__),
    )


def _head(theme: Theme) -> list[str]:
    """Wordmark with its trail, and the attributes beside it.

    The trail belongs under the mark: it reads right to left, the direction the
    report's `←` reads, so the screen teaches the notation before the first
    report uses it.
    """
    mark = [theme.paint(line, "recorded") for line in WORDMARK]
    trail = f"  {theme.dim(TRAIL.format(arrow=theme.glyph(ARROW)))}"
    rows = _rows()
    width = max(len(name) for name, _ in rows)

    if theme.width < _SIDE_BY_SIDE:
        room = theme.width - width - 6
        return [
            *(f"  {line}" for line in mark),
            trail,
            "",
            *(
                f"  {theme.dim(name.ljust(width))}  {theme.paint(theme.clip(v, room), 'body')}"
                for name, v in rows
            ),
        ]

    gutter = len(WORDMARK[0]) + 4
    room = theme.width - gutter - width - 2

    right = [
        "",
        *(
            f"{theme.dim(name.ljust(width))}  {theme.paint(theme.clip(value, room), 'body')}"
            for name, value in rows
        ),
    ]
    left = [*(f"  {line}" for line in mark), trail]

    out = []
    for index in range(max(len(left), len(right))):
        prefix = left[index] if index < len(left) else ""
        pad = max(1, gutter - _visible(prefix))
        column = right[index] if index < len(right) else ""
        out.append((f"{prefix}{' ' * pad}{column}").rstrip())
    return out


# --- blocks ------------------------------------------------------------------


def _block(theme: Theme, rule: str, heading: str, rows: tuple[tuple[str, str], ...]) -> list[str]:
    lines = [rule, "", f"  {theme.label(heading)}", ""]

    width = max(len(command) for command, _ in rows)
    room = theme.width - 4 - width - 2

    for command, description in rows:
        text = theme.paint(command.ljust(width) if room >= _MIN_DESCRIPTION else command, "body")
        if room < _MIN_DESCRIPTION:
            lines.append(f"    {text}")
            continue
        lines.append(f"    {text}  {theme.dim(theme.clip(description, room))}")
    lines.append("")
    return lines


def _sources(theme: Theme) -> list[str]:
    """What the tool reads, coloured by evidence class.

    The colour code is the one thing a reader has to learn to use the report at
    speed, so the landing screen teaches it here rather than leaving it to be
    inferred from a folder of results.

    Paired two to a line: six full-width rows would be half a screen of legend,
    and the meters are what carry the meaning, not the horizontal space.
    """
    width = max(len(name) for name, _, _, _ in SOURCES)
    cell = width + 7  # label, gap, five-slot meter
    paired = theme.width - 2 - _LABEL - 1 >= cell * 2 + 4

    def draw(entry: tuple[str, str, int, str]) -> str:
        name, _, confidence, evidence = entry
        return f"{theme.paint(name.ljust(width), evidence)}  {theme.meter(confidence, evidence)}"

    lines = []
    step = 2 if paired else 1
    for index in range(0, len(SOURCES), step):
        label = "reads" if index == 0 else ""
        row = "    ".join(draw(entry) for entry in SOURCES[index : index + step])
        prefix = f"  {theme.label(label.ljust(_LABEL))} "
        lines.append(f"{prefix}{row}")
    lines.append("")
    return lines


def _note(theme: Theme, text: str) -> str:
    return f"    {theme.dim(theme.clip(text, theme.width - 4))}"


def _visible(text: str) -> int:
    length = 0
    index = 0
    while index < len(text):
        if text[index] == "\x1b":
            terminator = text.find("m", index)
            index = len(text) if terminator < 0 else terminator + 1
            continue
        length += 1
        index += 1
    return length
