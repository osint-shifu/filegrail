"""The screen a bare `filegrail` prints.

Typing a tool's name and having it silently start work on the current directory
is a surprise, and in a home directory an expensive one. So a run with no
arguments introduces the tool and says how to point it somewhere.

The shape below the wordmark is the one every modern command-line tool uses -
usage, examples, commands, options - because a reader who has used any of them
already knows how to read it in a second, and a landing screen's job is to get
someone to the right command rather than to be memorable.

What is deliberately *not* here any more: the table of evidence sources. It is a
good table and it belongs in `doctor`, where a reader is asking what this machine
can answer. On the front door it answered a question nobody had asked yet.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import LICENSE, REPOSITORY, TAGLINE, __version__
from .theme import MIDDOT, Theme, detect

#: Plain ASCII, so the wordmark survives a terminal that cannot print box
#: drawing and never needs a second variant.
WORDMARK = (
    r"  __ _ _                   _ _ ",
    r" / _(_) |___ __ _ _ _ __ _(_) |",
    r"|  _| | / -_) _` | '_/ _` | | |",
    r"|_| |_|_\___\__, |_| \__,_|_|_|",
    r"            |___/              ",
)

#: The three things the tool is for, and enough of what is under each one that
#: a reader recognises their own case instead of having to infer it. Not a
#: feature list: three lines, one per area, and the option table stays in
#: `filegrail help`.
AREAS = (
    ("metadata", ("EXIF", "XMP", "IPTC", "C2PA", "PDF", "Office", "media", "email")),
    ("provenance", ("browser history", "OS origin", "archives", "shell history")),
    ("analysis", ("conflicts", "timelines", "related files", "identifiers")),
)

USAGE = (
    ("filegrail <path> [options]", ""),
    ("filegrail <command> [options]", ""),
)

#: Six ways in, ordered as a progression: one file, a directory, the two views
#: that turn a scan into leads, the reasoning behind a finding, and what this
#: machine can answer at all. Not eleven examples and not the whole option
#: table - a landing screen exists to get somebody to their first command, and
#: a reader who has to choose from eleven has been given the choosing to do.
START = (
    ("filegrail suspicious.pdf", "analyze one file"),
    ("filegrail ~/Downloads", "analyze a directory"),
    ("filegrail . --identify", "extract investigation pivots"),
    ("filegrail . --timeline", "reconstruct recorded events"),
    ("filegrail explain file.pdf", "inspect evidence behind findings"),
    ("filegrail doctor", "check available local sources"),
)

#: Named rather than described. What each one does is a sentence away in
#: `filegrail help <command>`, and six sentences here would double the screen.
#: `help` is not in the list because it is the line underneath it.
COMMANDS = ("scan", "explain", "compare", "doctor", "menu", "clean")

#: Below this the wordmark and the attributes cannot sit side by side.
_SIDE_BY_SIDE = 78

#: Below this there is no room for a description beside a command.
_MIN_DESCRIPTION = 14

#: The label column, wide enough for the longest section name.
_LABEL = 11


def invocation() -> str:
    """The command that will actually work in the caller's shell.

    Someone running from a checkout has no `filegrail` on their PATH. Printing
    it at them anyway is the difference between a screen that helps and one that
    is immediately proved wrong.
    """
    if Path(sys.argv[0]).stem == "filegrail" or shutil.which("filegrail"):
        return "filegrail"

    prefix = "PYTHONPATH=src " if "src" in os.environ.get("PYTHONPATH", "") else ""
    return f"{prefix}{Path(sys.executable).name} -m filegrail.cli"


def render(theme: Theme | None = None) -> str:
    theme = theme or detect()
    run = invocation()

    lines = ["", *_head(theme), ""]
    if run != "filegrail":
        lines.extend(_install(theme, run))

    # The label column is the spine and stays fixed. The body column is sized
    # per section: forcing a seven-character command into the width of a
    # thirty-character example opens a gutter across half the screen and pushes
    # the descriptions into an ellipsis, which is the one thing this report does
    # not do anywhere else.
    lines.extend(_areas(theme))
    lines.extend(_section(theme, "usage", USAGE))
    lines.extend(_section(theme, "start", START))
    lines.extend(_listed(theme, "commands", COMMANDS))

    lines.append(_row(theme, "help", "filegrail help <command>"))
    lines.append("")
    return "\n".join(lines)


def _areas(theme: Theme) -> list[str]:
    """The three lines that say what this is, before any command appears."""
    lines = []
    for label, parts in AREAS:
        said = f" {theme.glyph(MIDDOT)} ".join(parts)
        lines.extend(_wrapped(theme, label, said))
    lines.append("")
    return lines


def _listed(theme: Theme, label: str, names: tuple[str, ...]) -> list[str]:
    """One labelled line naming things, rather than a row for each of them."""
    return [*_wrapped(theme, label, f" {theme.glyph(MIDDOT)} ".join(names)), ""]


def _wrapped(theme: Theme, label: str, body: str) -> list[str]:
    """A labelled run of text over as many lines as the terminal needs.

    It wraps rather than clips because there is nowhere else to read it: the
    option table has `filegrail help`, but nothing repeats these three lines.
    """
    room = max(12, theme.width - _LABEL - 5)
    parts = theme.wrap(body, room)
    return [
        f"  {theme.label((label if index == 0 else '').ljust(_LABEL))} {theme.paint(part, 'body')}"
        for index, part in enumerate(parts)
    ]


# --- the body ----------------------------------------------------------------


def _row(
    theme: Theme,
    label: str,
    body: str,
    detail: str = "",
    column: int = 0,
    *,
    emphasise: bool = False,
) -> str:
    """One line of the two-column spine that runs the length of the screen."""
    prefix = f"  {theme.label(label.ljust(_LABEL))} "
    room = theme.width - _LABEL - 5

    if not detail or len(body) > column:
        return f"{prefix}{theme.paint(theme.clip(body, room), 'body')}"

    text = theme.bold(body.ljust(column)) if emphasise else theme.paint(body.ljust(column), "body")
    return f"{prefix}{text}  {theme.dim(theme.clip(detail, room - column - 2))}"


def _section(
    theme: Theme,
    label: str,
    rows: tuple[tuple[str, str], ...],
    *,
    emphasise: bool = False,
) -> list[str]:
    """A labelled block, with the label beside its first line rather than above.

    Above would cost a line and a blank one per section, and the label column is
    already carrying that job everywhere else on the screen.
    """
    column = max(len(body) for body, _ in rows)

    # On a narrow terminal the description gives way rather than the command:
    # a command you cannot read is useless, a command with no gloss beside it
    # is merely terse.
    room = theme.width - _LABEL - 7 - column
    lines = [
        _row(
            theme,
            label if index == 0 else "",
            body,
            detail if room >= _MIN_DESCRIPTION else "",
            column,
            emphasise=emphasise,
        )
        for index, (body, detail) in enumerate(rows)
    ]
    lines.append("")
    return lines


def _install(theme: Theme, run: str) -> list[str]:
    """What makes the examples below work, said once and never repeated."""
    return [
        _row(theme, "install", "pipx install filegrail", "to get the bare command", 22),
        _row(theme, "", f"alias filegrail='{run}'"),
        "",
    ]


def _rows() -> tuple[tuple[str, str], ...]:
    return (
        ("repo", REPOSITORY.split("//", 1)[-1]),
        ("license", LICENSE),
        ("version", __version__),
    )


def _head(theme: Theme) -> list[str]:
    """Wordmark with the tagline under it, and the attributes beside it.

    The tagline sits where the trail motif used to. The trail said something
    true about the notation, but a landing screen has one line in which to say
    what the tool is for, and that line was spending itself on decoration.
    """
    mark = [theme.paint(line, "recorded") for line in WORDMARK]
    tagline = f"  {theme.dim(theme.clip(TAGLINE, theme.width - 4))}"
    rows = _rows()
    width = max(len(name) for name, _ in rows)

    if theme.width < _SIDE_BY_SIDE:
        room = theme.width - width - 6
        return [
            *(f"  {line}".rstrip() for line in mark),
            tagline,
            "",
            *(
                f"  {theme.dim(name.ljust(width))}  {theme.paint(theme.clip(v, room), 'body')}"
                for name, v in rows
            ),
        ]

    gutter = len(WORDMARK[0]) + 5
    room = theme.width - gutter - width - 2

    right = [
        "",
        *(
            f"{theme.dim(name.ljust(width))}  {theme.paint(theme.clip(value, room), 'body')}"
            for name, value in rows
        ),
    ]
    left = [*(f"  {line}".rstrip() for line in mark), tagline]

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
