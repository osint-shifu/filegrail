"""The screen a bare `filetrail` prints.

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

USAGE = (
    ("filetrail <path> [options]", ""),
    ("filetrail <command> [options]", ""),
)

#: Ordered as a progression rather than a list: point it somewhere, narrow the
#: view, ask why, then take the answer away with you. Each one is a different
#: job, and none of them restates the flag it uses - a description that only
#: expands the option name is a line the reader can skip, and once they learn
#: they can skip one they skip the rest.
EXAMPLES = (
    ("filetrail ~/Downloads", "everything in a folder"),
    ("filetrail suspicious.pdf", "one file"),
    ("filetrail . --unknown-only", "what nothing accounts for"),
    ("filetrail photos/ --type image", "cameras and phones only"),
    ("filetrail explain suspicious.pdf", "why it concluded that"),
    ("filetrail compare a.jpg b.jpg", "same camera? same route here?"),
    ("filetrail . --identify", "emails, domains, coordinates found"),
    ("filetrail . --timeline", "in the order things happened"),
    ("filetrail . --redact --json", "safe to hand to someone else"),
    ("filetrail doctor", "what this machine can answer at all"),
)

COMMANDS = (
    ("scan", "analyze a file or directory (the default)"),
    ("explain", "why filetrail reached a conclusion about one file"),
    ("compare", "what two files share, and how each arrived"),
    ("doctor", "which evidence sources this machine has"),
    ("menu", "pick a view from a list"),
    ("help", "show help for a command"),
)

OPTIONS = (
    ("-v, --verbose", "show every evidence record"),
    ("-j, --json", "machine-readable output"),
    ("    --brief", "summarise instead of listing every field"),
    ("    --identify", "emails, domains, addresses, coordinates"),
    ("    --type image", "only these kinds of file"),
    ("    --unknown-only", "only files nothing accounts for"),
    ("    --redact", "redact credentials before printing"),
    ("    --no-recurse", "this directory only"),
    ("    --no-color", "disable ANSI colors"),
    ("    --version", "show version"),
)

#: Below this the wordmark and the attributes cannot sit side by side.
_SIDE_BY_SIDE = 78

#: Below this there is no room for a description beside a command.
_MIN_DESCRIPTION = 14

#: The label column, wide enough for the longest section name.
_LABEL = 9


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


def render(theme: Theme | None = None) -> str:
    theme = theme or detect()
    run = invocation()

    lines = ["", *_head(theme), ""]
    if run != "filetrail":
        lines.extend(_install(theme, run))

    # The label column is the spine and stays fixed. The body column is sized
    # per section: forcing a seven-character command into the width of a
    # thirty-character example opens a gutter across half the screen and pushes
    # the descriptions into an ellipsis, which is the one thing this report does
    # not do anywhere else.
    lines.extend(_section(theme, "usage", USAGE))
    lines.extend(_section(theme, "examples", EXAMPLES))
    lines.extend(_section(theme, "commands", COMMANDS, emphasise=True))
    lines.extend(_section(theme, "options", OPTIONS))

    lines.append(_row(theme, "", "filetrail help <command>", "for any of it in detail", 24))
    lines.append("")
    return "\n".join(lines)


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
        _row(theme, "install", "pipx install filetrail", "to get the bare command", 22),
        _row(theme, "", f"alias filetrail='{run}'"),
        "",
    ]


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
