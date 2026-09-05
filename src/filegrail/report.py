"""Render scan results.

The default rendering is styled for a terminal and degrades to the identical
layout in plain text when the output is piped or colour is unwanted, so the
same command reads well by eye and greps cleanly.

The layout is specified in `docs/DESIGN.md`. Two ideas carry it: a one-character left
gutter groups the lines of an entry without a box, and colour is spent only on
saying which class of source made a claim.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from . import TAGLINE, __version__
from .about import WORDMARK
from .clean import Cleaned
from .cluster import cluster as group_sources
from .explain import conclusion, grouped
from .identify import PLACE, Identifier, extract
from .models import ACQUISITION, INTRINSIC, FileRecord, Origin, kind, label
from .overview import Alert, Inventory, Tally, attention, findings, inventory
from .reconcile import ATTRIBUTION_CONFLICT, CONFLICT, KINDS, PARTIAL, Verdict, reconcile
from .scan import Unsearched

if TYPE_CHECKING:  # both are imported where they are used, to keep startup light
    from .compare import Comparison
    from .doctor import Survey
from .theme import (
    ARROW,
    BRANCH,
    BULLET,
    EVIDENCE_HEADINGS,
    FLAG,
    LAST,
    MIDDOT,
    RAIL,
    STRENGTH,
    Theme,
    detect,
)

#: The version of the machine-readable documents. It is a promise to whatever
#: consumes them, so it changes only when a field changes meaning or leaves -
#: adding one is not a break, and neither is a release.
SCHEMA = 1

#: Sources describing what a file says about itself, rather than where it came from.
SELF_REPORTED = frozenset(
    {"document-metadata", "device-metadata", "c2pa", "xmp", "xmp-history", "iptc"}
)


def shown(moment: str | None) -> str | None:
    """A timestamp as the report prints it: to the second, and no further.

    A source is free to record more. GTK writes microseconds into
    `recently-used.xbel` and a shortcut carries the filesystem's own precision,
    and `--json` keeps every digit of it. On screen those seven characters buy
    nothing, sit beside a dozen stamps that stop at the second, and read as an
    inconsistency rather than as precision.
    """
    if not moment:
        return None
    return f"{moment[:19]}Z" if moment.endswith("Z") else moment[:19]


#: Width of the label column inside an entry, so values line up across labels.
_LABEL = 10

#: Where an entry's text begins: two spaces, the gutter glyph, one space.
_INDENT = 4

#: The widest a field name may be before it stops sharing a line with its value.
#: Past this the column is eating the terminal; a longer name is not truncated,
#: it takes a line of its own.
_FIELD_NAME = 24


def _gutter(theme: Theme) -> int:
    """How wide the gutter column is for this theme.

    Unicode glyphs are all one column, but the ASCII arrow is `<-`, two. Padding
    every glyph to the widest keeps the left edge straight in both, which is the
    whole point of having a gutter.
    """
    return 2 + len(theme.glyph(ARROW)) + 1


def _mark(theme: Theme, symbol: str, colour: str | None = None) -> str:
    """One gutter glyph, padded so every line starts its text in one column."""
    width = len(theme.glyph(ARROW))
    glyph = theme.glyph(symbol).ljust(width)
    return theme.paint(glyph, colour) if colour else theme.paint(glyph, "rail")


def _row(
    theme: Theme,
    prefix: str,
    body: str,
    right: str,
    *,
    paint: Callable[[str], str] | None = None,
    wrap: bool = True,
) -> str:
    """One line carrying a single right-aligned column.

    `prefix` and `right` arrive painted, so only their visible width matters.
    `body` arrives plain and is sized before painting - doing it afterwards
    would cut an escape sequence in half.

    `wrap=False` says the caller has already broken the text and this is one
    piece of it, so it must be left alone.
    """
    room = theme.width - _visible(prefix) - _visible(right) - 2
    if wrap:
        body = theme.clip(body, max(8, room))
    painted = paint(body) if paint else body
    gap = max(1, theme.width - _visible(prefix) - _visible(painted) - _visible(right))
    return f"{prefix}{painted}{' ' * gap}{right}"


def render_text(
    records: list[FileRecord],
    root: Path,
    *,
    verbose: bool = False,
    brief: bool = False,
    limit: int = 0,
    stats: dict[str, int] | None = None,
    theme: Theme | None = None,
    filtered: str = "",
    identify: bool = False,
    cluster: bool = False,
    home: Path | None = None,
    unsearched: Unsearched | None = None,
) -> str:
    theme = theme or detect()
    known = [record for record in records if record.origins]
    unknown = [record for record in records if not record.origins]
    found = extract(records)
    contents = inventory(records)

    lines = _masthead(theme, root, contents, len(known), len(unknown))
    if home:
        lines.extend([*_whose_machine(theme, home, "evidence read from the profile at"), ""])

    # A directory is answered from the top down: what is in it, what was found
    # in it, what wants a second look, and only then one file at a time. A
    # single file has none of those questions - there is nothing to inventory
    # but itself - so it goes straight to the answer.
    if len(records) > 1:
        lines.extend(_inventory(theme, contents))
        lines.extend(_findings(theme, findings(records)))
        lines.extend(_attention(theme, attention(records, found, listed=identify), root))

    lines.extend(_sections(theme, known, root, verbose=verbose, brief=brief))

    if unknown:
        lines.extend(_unknown(theme, unknown, root, limit))

    if identify:
        lines.extend(_identifiers(theme, found))

    if cluster:
        lines.extend(_shared(theme, records))

    lines.extend(_summary(theme, records, known, unknown, stats, filtered, root, unsearched))
    return "\n".join(lines)


#: What each axis is called where the section names it. The word says what the
#: shared value identifies, because the three do not identify equally well and
#: one label for all of them would flatten that away.
_AXIS_LABELS = {"device": "camera body", "model": "camera model", "author": "author"}


def _shared(theme: Theme, records: list[FileRecord]) -> list[str]:
    """The sources more than one scanned file names.

    A group of one is left out: it says a file has an author, which the file
    already said. What this section is for is the second file, and the picture
    of a directory that appears once the repeats are counted.
    """
    groups = [group for group in group_sources(records) if len(group.paths) > 1]
    lines = _heading(theme, "shared sources", len(groups), "source")

    if not groups:
        return [*lines, f"    {theme.dim('no source is shared by more than one file')}", ""]

    # Wide enough for the longest label there is, whichever axes turned up, so
    # the column does not move between one scan and the next. Padding goes in
    # the prefix because `_row` collapses whitespace inside the body.
    width = max(len(name) for name in _AXIS_LABELS.values())
    for group in groups:
        label = _AXIS_LABELS.get(group.axis, group.axis)
        tag = theme.dim(theme.clip(label, width).ljust(width))
        count = theme.dim(_plural(len(group.paths), "file"))
        lines.append(_row(theme, f"    {tag}  ", group.name, count))
    return [*lines, ""]


#: Which evidence class each identifier type is drawn in. A coordinate is the
#: one that becomes a marker on a map, so it keeps the colour the report already
#: uses for a location.
_IDENTIFIER_COLOURS = {
    "geo": "circumstantial",
    "email": "recorded",
    "domain": "inherited",
    "url": "inherited",
    "ipv4": "credentialed",
}


def _identifiers(theme: Theme, found: list[Identifier]) -> list[str]:
    """Every identifier the metadata carried, grouped by type.

    Listed once each with a count rather than once per occurrence: the question
    an analyst asks of this section is "what is in here", and the same author
    address across forty files is one lead, not forty.
    """
    if not found:
        return []

    lines = _heading(theme, "identifiers", len(found), noun="value")
    width = min(max(len(entry.normalized) for entry in found), theme.width - 30)

    for entry in found:
        colour = _IDENTIFIER_COLOURS.get(entry.type, "self-reported")
        kind = theme.dim(entry.type.ljust(7))
        seen = theme.dim(f"{entry.count} in {entry.files}")

        # An identifier is what somebody pivots on next, so it wraps like every
        # other value. Half an address is not a shorter address.
        parts = theme.wrap(entry.normalized, width)
        lines.append(f"    {kind} {theme.paint(parts[0].ljust(width), colour)}  {seen}")
        lines.extend(f"    {' ' * 8}{theme.paint(part, colour)}" for part in parts[1:])
        # The place string carries a middot because that is the form `--json`
        # promises. A terminal that cannot print one gets the ASCII separator
        # this report uses everywhere else.
        where = entry.where[0].replace(PLACE, f" {theme.glyph(MIDDOT)} ")
        lines.extend(
            f"    {' ' * 8}{theme.dim(part)}" for part in theme.wrap(where, theme.width - 14)
        )
    lines.append("")
    return lines


def _plural(count: int, noun: str, plural: str | None = None) -> str:
    """`3 files`, and `2 directories` for the nouns an -s does not pluralise."""
    if count == 1:
        return f"{count} {noun}"
    return f"{count} {plural or noun + 's'}"


def _facts_line(theme: Theme, facts: list[str]) -> str:
    return theme.glyph(MIDDOT).join(f" {fact} " for fact in facts).strip()


#: The label column of the banner, wide enough for the longest of its rows.
_BANNER_LABEL = 8

#: Below this the version cannot sit beside the wordmark and takes its own line.
_VERSION_BESIDE = 52

#: Which line of the wordmark the version sits on. The third, where the mark is
#: at its widest and the eye is already.
_VERSION_LINE = 2


def _masthead(theme: Theme, root: Path, found: Inventory, known: int, unknown: int) -> list[str]:
    """The report's own letterhead: what wrote this, and what it was pointed at.

    A report is redirected to a file more often than it is read on screen, and
    a file that does not say what produced it is a wall of text somebody has to
    identify from memory. The wordmark is the landing screen's, so the two are
    recognisably the same tool; everything that belongs to a front door - the
    repository, the licence, the usage - is not here, because a report is not
    an introduction.

    The scale and the yield are separate rows because they answer separate
    questions: what is in here, and how much of it answered. It used to read
    `73 of 105 traced` over a count of files carrying an origin of any kind,
    and a PDF with an Info dictionary has not been traced anywhere - it has
    described itself.
    """
    stamp = theme.label(f"filegrail {__version__}")
    beside = theme.width >= _VERSION_BESIDE
    gutter = len(WORDMARK[0]) + 5

    lines = [""]
    for index, line in enumerate(WORDMARK):
        mark = f"  {theme.paint(line, 'recorded')}"
        if beside and index == _VERSION_LINE:
            lines.append(f"{mark}{' ' * max(1, gutter - len(line) - 2)}{stamp}".rstrip())
        else:
            lines.append(mark.rstrip())
    if not beside:
        lines.append(f"  {stamp}")

    lines.append("")
    lines.extend(_wrapped(theme, TAGLINE, "  ", theme.dim))
    lines.append("")

    scale = [_plural(found.files, "file")]
    if found.files > 1:
        scale.append(_plural(len(found.types), "type"))
    scale.append(_size(found.size))

    rows = [("target", _display(root)), ("scanned", _facts_line(theme, scale))]
    if found.files > 1:
        rows.append(
            ("findings", _facts_line(theme, [f"{known} files", f"{unknown} without findings"]))
        )
    for name, value in rows:
        lines.extend(_labelled(theme, name, value))

    lines.extend(["", f"  {theme.rule(theme.width - 2)}", ""])
    return lines


def _labelled(theme: Theme, name: str, value: str) -> list[str]:
    """One banner row: a fixed label column, and a value that wraps under it.

    The target wraps rather than clips for the reason every path in this report
    does - half a mount path still looks like a path, and a reader who cannot
    see what was scanned cannot check anything below it.
    """
    head = f"  {theme.label(name.ljust(_BANNER_LABEL))}  "
    room = max(8, theme.width - _BANNER_LABEL - 6)
    parts = theme.wrap(value, room)
    return [
        f"{head if index == 0 else ' ' * (_BANNER_LABEL + 4)}{theme.paint(part, 'body')}"
        for index, part in enumerate(parts)
    ]


def _wrapped(theme: Theme, text: str, indent: str, paint: Callable[[str], str]) -> list[str]:
    """One run of text over as many lines as the terminal needs for all of it."""
    return [f"{indent}{paint(part)}" for part in theme.wrap(text, theme.width - len(indent) - 2)]


def _inventory(theme: Theme, found: Inventory) -> list[str]:
    """Every type present, how many of each, and how much of the scan it is.

    One table rather than two. Counts and sizes answer the same question - what
    is this directory made of - and splitting them makes the reader hold half
    the answer while they find the other half.
    """
    if not found.types:
        return []

    digits = max(len(str(entry.count)) for entry in found.types)
    sizes = {entry.name: _size(entry.size) for entry in found.types}
    span = max(len(value) for value in sizes.values())

    # The name column is bounded by what still leaves a whole cell inside the
    # terminal. An extension wider than that is not shortened - it steps out of
    # the grid and takes lines of its own underneath, because an extension is
    # data and the grid is a layout.
    room = theme.width - _INDENT
    column = min(max(len(entry.name) for entry in found.types), max(4, room - digits - span - 4))
    fits = [entry for entry in found.types if len(entry.name) <= column]
    wide = [entry for entry in found.types if len(entry.name) > column]

    lines = _heading(theme, "inventory", len(found.types), noun="type")
    if fits:
        lines.extend(
            _grid(
                theme,
                [
                    theme.paint(entry.name.ljust(column), "body")
                    + theme.label(str(entry.count).rjust(digits + 2))
                    + theme.dim(sizes[entry.name].rjust(span + 2))
                    for entry in fits
                ],
                column + digits + span + 4,
            )
        )
    for entry in wide:
        lines.extend(
            f"{' ' * _INDENT}{theme.paint(part, 'body')}" for part in theme.wrap(entry.name, room)
        )
        tail = theme.label(str(entry.count).rjust(digits)) + theme.dim(
            sizes[entry.name].rjust(span + 2)
        )
        lines.append(_row(theme, " " * _INDENT, "", tail, wrap=False))

    if found.families:
        width = max(len(family) for family, _ in found.families)
        counts = max(len(str(count)) for _, count in found.families)
        lines.append("")
        lines.extend(
            _grid(
                theme,
                [
                    theme.label(family.ljust(width)) + theme.dim(str(count).rjust(counts + 2))
                    for family, count in found.families
                ],
                width + counts + 2,
            )
        )
    lines.append("")
    return lines


#: Space between the columns of a grid. Wide enough that two cells never read
#: as one, narrow enough to keep a column on an eighty-column terminal.
_GAP = 4


def _grid(theme: Theme, cells: list[str], width: int, indent: int = _INDENT) -> list[str]:
    """Lay equal-width cells across the terminal, as many per row as fit.

    Columns give way one at a time as the terminal narrows, down to one. The
    cells themselves never give way: an inventory that dropped a digit to keep
    four columns would be trading the answer for the layout.

    The cells arrive painted and each one is already `width` columns wide, so
    nothing here has to measure an escape sequence.
    """
    room = theme.width - indent
    columns = max(1, (room + _GAP) // (width + _GAP))
    return [
        " " * indent + (" " * _GAP).join(cells[start : start + columns])
        for start in range(0, len(cells), columns)
    ]


def _findings(theme: Theme, tallies: list[Tally]) -> list[str]:
    """What was found, in the words of what it is rather than what read it.

    `which readers returned results` is a real question and it has its own
    table at the end of the report. It is not this one: an analyst reading down
    a list of parser names still has to work out what any of it means.
    """
    if not tallies:
        return []

    width = max(len(tally.name) for tally in tallies)
    # The digits line up, not the phrases: `1 file` and `66 files` right-aligned
    # as whole phrases puts the 1 under the s of files, which is a column of
    # nothing.
    digits = max(len(str(tally.files)) for tally in tallies)

    lines = _heading(theme, "findings")
    for tally in tallies:
        noun = "file" if tally.files == 1 else "files"
        lines.append(
            f"{' ' * _INDENT}{theme.paint(tally.name.ljust(width), 'body')}"
            f"  {theme.label(str(tally.files).rjust(digits))} {theme.dim(noun)}"
        )
    lines.append("")
    return lines


def _attention(theme: Theme, raised: list[Alert], root: Path) -> list[str]:
    """The few things a long report would otherwise bury.

    Not an alarm panel: coordinates and Content Credentials are findings, not
    problems, and the heading says so. No colour is spent beyond the one the
    palette already has for evidence that disagrees with itself - these lines
    are counts, not claims, and painting a count by how alarming it is would be
    the one thing this interface never does with colour.
    """
    if not raised:
        return []

    lines = _heading(theme, "notable findings")
    for alert in raised:
        colour = "warning" if alert.contested else None
        # `●` means "this is a file" everywhere else in the report, and a count
        # line is not a file. Only the contested flag keeps a glyph; the rest
        # are indented to the same column and left unmarked, which is quieter
        # and does not spend a symbol the gutter is already using.
        glyph = _mark(theme, FLAG, colour) if alert.contested else _mark(theme, " ")
        for index, part in enumerate(theme.wrap(alert.text, theme.width - _gutter(theme) - 2)):
            gutter = glyph if index == 0 else _mark(theme, RAIL)
            lines.append(f"  {gutter} {theme.paint(part, colour or 'body')}")

        for path in alert.files:
            for part in theme.wrap(_relative(path, root), theme.width - _gutter(theme) - 4):
                lines.append(f"  {_mark(theme, RAIL)}   {theme.dim(part)}")
        if alert.hidden:
            more = f"and {alert.hidden} more, each marked in the report below"
            lines.append(f"  {_mark(theme, RAIL)}   {theme.dim(more)}")
    lines.append("")
    return lines


def _sections(
    theme: Theme, known: list[FileRecord], root: Path, *, verbose: bool, brief: bool
) -> list[str]:
    """Group entries by the class of evidence that explains them.

    Strongest class first, always - that ordering is free and it puts the
    trustworthy findings where the eye lands.

    Headings are another matter. One over every entry is not grouping, it is
    relabelling: the colour and the source line already say which class a claim
    belongs to. So they appear only once a class actually collects something,
    which is also the point at which the report is long enough to need them.
    """
    grouped: dict[str, list[FileRecord]] = {}
    for record in known:
        source = record.best.source if record.best else "filesystem"
        grouped.setdefault(theme.evidence(source), []).append(record)

    show_headings = len(grouped) > 1 and max(len(m) for m in grouped.values()) > 1
    lines: list[str] = []

    for key, heading in EVIDENCE_HEADINGS:
        members = grouped.pop(key, None)
        if not members:
            continue
        if show_headings:
            lines.extend(_heading(theme, heading, len(members)))
        for record in members:
            lines.extend(_entry(theme, record, root, verbose=verbose, brief=brief))

    for members in grouped.values():  # any class the table above did not name
        for record in members:
            lines.extend(_entry(theme, record, root, verbose=verbose, brief=brief))
    return lines


def _heading(theme: Theme, text: str, count: int | None = None, noun: str = "file") -> list[str]:
    """A section name and its rule, with what it holds on the right.

    The count is optional: a section whose rows each carry their own count has
    nothing to put up there that is not already below it.
    """
    right = theme.dim(_plural(count, noun)) if count is not None else ""
    return [
        _row(theme, "  ", text, right, paint=theme.label).rstrip(),
        f"  {theme.rule(theme.width - 2)}",
        "",
    ]


def _entry(
    theme: Theme, record: FileRecord, root: Path, *, verbose: bool, brief: bool
) -> list[str]:
    colour = theme.evidence(record.best.source if record.best else "filesystem")
    indent = _gutter(theme)
    bullet = _mark(theme, BULLET, colour)
    size = theme.dim(_size(record.size))
    name = _relative(record.path, root)

    room = theme.width - indent - _visible(size) - 2
    wrapped = theme.wrap(name, room)
    lines = [
        _row(theme, f"  {bullet} ", wrapped[0], size, wrap=False, paint=theme.bold),
        *(f"{' ' * indent}{theme.bold(part)}" for part in wrapped[1:]),
    ]

    # Both halves, always, and never ranked against each other. "How did this
    # get here" and "what does it say about its earlier life" are different
    # questions; letting a download record outrank a camera's EXIF meant a
    # geotagged photograph that had been downloaded reported no GPS at all.
    verdict = reconcile(record)

    if verbose:
        claims: list[Origin | None] = list(record.origins)
    elif verdict.state in (PARTIAL, CONFLICT):
        # A verdict that refers to evidence the report hid is not a verdict, so
        # a disagreement brings every acquisition record on screen with it.
        acquisition = [o for o in record.origins if kind(o) == ACQUISITION and o.url]
        claims = [*acquisition, *_self_descriptions(record, verdict), record.interaction]
    else:
        # Strongest first, and interaction last: it is the weakest of the three
        # and putting it above intrinsic would bury a camera's GPS under the
        # fact that something opened the file.
        claims = [record.acquisition, *_self_descriptions(record, verdict), record.interaction]

    for index, origin in enumerate(claim for claim in claims if claim is not None):
        if index:
            lines.append(f"  {_mark(theme, RAIL)}".rstrip())
        lines.extend(_origin(theme, origin, record, brief=brief))

    if verdict.notable:
        lines.extend(_verdict(theme, verdict))
    lines.extend(_links(theme, record, root))
    lines.append("")
    return lines


def _links(theme: Theme, record: FileRecord, root: Path) -> list[str]:
    """How this file relates to the others that were scanned with it.

    Last in the entry because it is the one part that points outward: everything
    above is about this file, and this says where else to look.
    """
    lines = []
    for link in record.links:
        named = ", ".join(_relative(path, root) for path in link.others)
        said = named or f"{link.count} other files in this scan"
        room = theme.width - _gutter(theme) - len(link.kind) - 4
        wrapped = theme.wrap(said, room)
        lines.append(f"  {_mark(theme, BRANCH)} {theme.dim(link.kind)}  {wrapped[0]}")
        for part in wrapped[1:]:
            lines.append(f"  {_mark(theme, RAIL)}   {' ' * len(link.kind)}{part}")
    return lines


def _self_descriptions(record: FileRecord, verdict: Verdict) -> list[Origin | None]:
    """What the file says about itself: the strongest claim, or all of them when
    they contradict each other.

    A finding that names a source the report did not print is a verdict about
    evidence the reader cannot see - the same reason a conflicting acquisition
    record is brought forward rather than ranked away.
    """
    if any(finding.kind == ATTRIBUTION_CONFLICT for finding in verdict.findings):
        return [origin for origin in record.origins if kind(origin) == INTRINSIC]
    return [record.intrinsic]


def _verdict(theme: Theme, verdict: Verdict) -> list[str]:
    """The reconciliation, in the gutter, so it reads as part of the entry."""
    colour = "warning" if verdict.contested else "recorded"
    indent = _gutter(theme)
    headline = theme.paint(verdict.headline, colour)

    lines = [f"  {_mark(theme, FLAG, colour)} {headline}"]
    for reason in verdict.reasons:
        for part in theme.wrap(reason, theme.width - indent - 2):
            lines.append(f"  {_mark(theme, RAIL)}   {theme.dim(part)}")
    return lines


def _origin(theme: Theme, origin: Origin, record: FileRecord, *, brief: bool = False) -> list[str]:
    colour = theme.evidence(origin.source)
    indent = _gutter(theme)
    arrow = _mark(theme, ARROW, colour)
    rail = _mark(theme, RAIL)

    claim = _headline(origin, record)
    wrapped = theme.wrap(claim, theme.width - indent)
    lines = [f"  {arrow} {theme.paint(wrapped[0], colour)}"]
    lines.extend(f"  {rail} {theme.paint(part, colour)}" for part in wrapped[1:])

    facts = [label(origin)]
    if origin.tool and origin.tool not in claim:
        facts.append(origin.tool)
    stamp = shown(origin.at if origin.source in SELF_REPORTED else (origin.at or record.btime))
    if stamp:
        facts.append(stamp)
    detail = theme.glyph(MIDDOT).join(f" {fact} " for fact in facts).strip()

    # The meter keeps the first line's right edge; anything that does not fit
    # beside it continues underneath rather than being cut off.
    meter = f"{theme.meter(origin.confidence, colour)} {theme.dim(STRENGTH.get(colour, colour))}"
    room = theme.width - indent - _visible(meter) - 2
    for index, part in enumerate(theme.wrap(detail, room)):
        if index == 0:
            lines.append(_row(theme, f"  {rail} ", part, meter, wrap=False, paint=theme.label))
        else:
            lines.append(f"  {rail} {theme.label(part)}")

    for name, value, paint in _facts(origin):
        for index, part in enumerate(theme.wrap(value, theme.width - indent - _LABEL)):
            head = theme.dim(name.ljust(_LABEL)) if index == 0 else " " * _LABEL
            painted = theme.paint(part, paint) if paint else theme.dim(part)
            lines.append(f"  {rail} {head}{painted}")

    if not brief and origin.fields:
        lines.extend(_fields_block(theme, origin.fields, indent))
    return lines


def _fields_block(theme: Theme, fields: dict[str, str], indent: int) -> list[str]:
    """Every decoded field, as a tree hanging off the claim above it.

    Shown by default rather than behind a flag. A report is read to find things
    out, and a reader who has to run the command a second time with `--full` has
    already been told less than the tool knew.

    The label column is sized to the names actually present: EXIF names run to
    seventeen characters and a fixed column would either waste width on every
    other reader or wrap on this one.
    """
    width = min(max(len(name) for name in fields), _FIELD_NAME)
    room = theme.width - indent - width - 2
    items = list(fields.items())

    out = [f"  {_mark(theme, RAIL)}".rstrip()]
    for index, (name, value) in enumerate(items):
        last = index == len(items) - 1
        branch = _mark(theme, LAST if last else BRANCH)
        spacer = " " * len(theme.glyph(ARROW)) if last else _mark(theme, RAIL)

        rows: list[str] = []
        if len(name) > width:
            # A name too long for the column takes lines of its own and the
            # value follows underneath. Cutting it instead left four XMP fields
            # printed as `xmpMM:DerivedFrom/stRef…` - four rows nobody can tell
            # apart, and four values nobody can attribute to a field.
            rows.extend(theme.dim(part) for part in theme.wrap(name, theme.width - indent - 2))
            rows.extend(
                f"{' ' * width}  {theme.paint(part, 'body')}"
                for part in theme.wrap(str(value), room)
            )
        else:
            head = theme.dim(name.ljust(width))
            rows.extend(
                f"{head if line == 0 else ' ' * width}  {theme.paint(part, 'body')}"
                for line, part in enumerate(theme.wrap(str(value), room))
            )

        out.extend(f"  {branch if line == 0 else spacer} {text}" for line, text in enumerate(rows))
    return out


def _facts(origin: Origin) -> list[tuple[str, str, str | None]]:
    """The labelled lines under a claim, in a fixed order."""
    found: list[tuple[str, str, str | None]] = []
    if origin.geo:
        found.append(("geo", origin.geo, "circumstantial"))
    if origin.location:
        found.append(("location", origin.location, "circumstantial"))
    if origin.referrer:
        found.append(("referrer", origin.referrer, None))
    if origin.note:
        found.append(("note", origin.note, None))
    return found


def _headline(origin: Origin, record: FileRecord) -> str:
    if origin.source in SELF_REPORTED:
        # An edit step records what an application did to a file it did not
        # create. "made by Photoshop" would turn a save into an origin, and the
        # action alone would leave the timeline with an event to attribute to
        # nobody, so the line names both.
        if origin.source == "xmp-history":
            if origin.note and origin.tool:
                return f"{origin.note} in {origin.tool}"
            return origin.note or origin.tool or "recorded edit"
        if origin.tool:
            return f"made by {origin.tool}"
        if origin.geo or origin.location:
            return "self-reported location"
        if origin.at:
            same = origin.at == record.mtime
            return "self-reported creation date" + (
                "" if same else ", which the filesystem does not show"
            )
        return "self-reported metadata"
    return origin.url or origin.command or origin.tool or "(no detail)"


def _unknown(theme: Theme, unknown: list[FileRecord], root: Path, limit: int) -> list[str]:
    """Files nothing was found for.

    Not `no recorded origin`, which names a narrower case than this list holds:
    a file here has no acquisition record, no metadata and nothing that touched
    it. It is a list of open questions, not of failures.
    """
    shown = unknown if limit <= 0 else unknown[:limit]
    lines = _heading(theme, "no findings", len(unknown))

    for record in shown:
        when = theme.dim(_moment(record.btime or record.mtime))
        prefix = " " * _INDENT
        beside = max(8, theme.width - _INDENT - _visible(when) - 2)
        name = _relative(record.path, root)

        if len(name) <= beside:
            lines.append(_row(theme, prefix, name, when, wrap=False, paint=theme.dim))
            continue

        # It did not fit beside the timestamp, so it takes the whole width and
        # the timestamp follows it. Splitting `...9B53.xml` into `...9B53.x`
        # and `ml` to keep a timestamp company is the layout winning an
        # argument it should not have had.
        parts = theme.wrap(name, theme.width - _INDENT - 2)
        lines.extend(f"{prefix}{theme.dim(part)}" for part in parts[:-1])
        if len(parts[-1]) <= beside:
            lines.append(_row(theme, prefix, parts[-1], when, wrap=False, paint=theme.dim))
        else:
            lines.append(f"{prefix}{theme.dim(parts[-1])}")
            lines.append(_row(theme, prefix, "", when, wrap=False))

    if len(shown) < len(unknown):
        hidden = len(unknown) - len(shown)
        note = f"... and {hidden} more (--limit 0 for all, --json for each)"
        if _INDENT + len(note) > theme.width:
            note = f"... and {hidden} more (--limit 0)"
        lines.append(theme.dim(f"{' ' * _INDENT}{note}"))
    lines.append("")
    return lines


def _summary(
    theme: Theme,
    records: list[FileRecord],
    known: list[FileRecord],
    unknown: list[FileRecord],
    stats: dict[str, int] | None,
    filtered: str = "",
    root: Path | None = None,
    unsearched: Unsearched | None = None,
) -> list[str]:
    """Which readers produced results, and the one line that closes the report.

    This table answers a technical question - what ran and what came back - so
    it sits at the end, after the evidence it is describing. It is not the
    findings section and must not stand in for it: a reader working down a list
    of parser names still has to work out what any of it meant.
    """
    # Tallied by the name the entries above were printed under, not by the
    # source behind it: one report calling the same claim `PDF Info` in the body
    # and `document metadata` in the summary reads as two kinds of evidence.
    counts: dict[str, int] = {}
    behind: dict[str, tuple[str, int]] = {}
    for record in known:
        if record.best:
            name = label(record.best)
            counts[name] = counts.get(name, 0) + 1
            behind[name] = (record.best.source, record.best.confidence)

    lines: list[str] = []
    if counts:
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        widest = max(len(name) for name, _ in ordered)
        digits = max(len(str(count)) for _, count in ordered)
        lines.extend(_heading(theme, "metadata sources", len(ordered), noun="source"))
        for name, count in ordered:
            source, confidence = behind[name]
            colour = theme.evidence(source)
            painted = theme.paint(name.ljust(widest), colour)
            meter = theme.meter(confidence, colour)
            lines.append(f"    {painted}  {meter}  {theme.dim(str(count).rjust(digits))}")
        lines.append("")

    lines.append(f"  {theme.rule(theme.width - 2)}")

    closing = _facts_line(
        theme,
        [
            f"{_plural(len(records), 'file')} analyzed",
            f"{len(known)} with findings",
            f"{len(unknown)} with no findings",
        ],
    )
    lines.extend(_wrapped(theme, closing, " " * _INDENT, theme.bold))

    if unsearched:
        lines.extend(_unsearched(theme, unsearched, root))

    if filtered:
        # An empty report after a filter has to name the filter. Otherwise it
        # reads as "this folder holds nothing", which is a different finding.
        scope = "No file matched" if not records else "Limited to"
        lines.append("")
        lines.append(theme.dim(f"    {scope} {theme.clip(filtered, theme.width - 24)}."))
    elif not known and records:
        lines.extend(explain_empty_result(stats, theme))
    lines.append("")
    return lines


#: How many directories are named before the rest become a count. A tree of
#: source repositories can hold hundreds of skipped names, and a report that
#: spends a page on them buries what it found.
_NAMED_DIRECTORIES = 8


def _unsearched(theme: Theme, missed: Unsearched, root: Path | None) -> list[str]:
    """The directories nothing in this report is about.

    Kept in two groups because they answer differently. One could not be read,
    which is a hole in the evidence and the thing this tool exists to be honest
    about; the other was skipped on purpose, which is a default the reader can
    turn off. Reported in that order: the hole first.
    """
    lines: list[str] = []
    for paths, sentence in (
        (
            missed.unreadable,
            "{count} could not be read. Nothing in this report is about {them}.",
        ),
        (missed.by_name, "{count} skipped by name; --no-skip reads {them} too."),
    ):
        if not paths:
            continue
        said = sentence.format(
            count=_plural(len(paths), "directory", "directories"),
            them="it" if len(paths) == 1 else "them",
        )
        lines.append("")
        lines.extend(_wrapped(theme, said, " " * _INDENT, theme.dim))
        for path in paths[:_NAMED_DIRECTORIES]:
            shown = _relative(path, root) if root else path
            lines.append(f"{' ' * (_INDENT + 2)}{theme.dim(shown)}")
        hidden = len(paths) - _NAMED_DIRECTORIES
        if hidden > 0:
            lines.append(
                f"{' ' * (_INDENT + 2)}{theme.dim(f'... and {hidden} more (--json for each)')}"
            )
    return lines


def explain_empty_result(stats: dict[str, int] | None, theme: Theme | None = None) -> list[str]:
    """Say why nothing matched, so zero does not read as a malfunction."""
    theme = theme or detect()
    if stats is None:
        return []

    profiles = stats.get("browser_profiles", 0)
    downloads = stats.get("browser_records", 0)

    if profiles == 0:
        return [
            "",
            theme.dim("    No browser profile was readable, so the strongest source"),
            theme.dim("    was unavailable."),
        ]

    return [
        "",
        theme.dim(
            f"    There was little to match against: {downloads} download "
            f"{'record' if downloads == 1 else 'records'} across {profiles} browser "
            f"{'profile' if profiles == 1 else 'profiles'}."
        ),
        theme.dim("    Browsers prune download history (Chromium keeps about 90 days by"),
        theme.dim("    default) and clearing history or migrating a profile discards it,"),
        theme.dim("    so files older than the surviving history cannot be resolved."),
    ]


def _file_json(record: FileRecord) -> dict[str, object]:
    """One file, with the reconciliation attached when it says anything."""
    data = record.to_dict()
    verdict = reconcile(record)
    if verdict.notable:
        data["reconciliation"] = verdict.to_dict()
    return data


def render_doctor(found: Survey, theme: Theme | None = None, home: Path | None = None) -> str:
    """What could be searched, and how far back it reaches."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    width = max(len(check.name) for check in found.checks)

    lines = ["", f"  {theme.bold('filegrail')}  {theme.dim('evidence sources')}", rule, ""]
    if home:
        lines.extend([*_whose_machine(theme, home, "surveying the profile at"), ""])

    for check in found.checks:
        colour = {
            "available": "recorded",
            "partial": "circumstantial",
        }.get(check.state, "warning")
        painted = theme.paint(check.name.ljust(width), "body")
        state = theme.paint(check.state, colour)
        lines.append(f"  {painted}  {state}")
        for part in theme.wrap(check.detail, theme.width - width - 8):
            lines.append(f"  {' ' * width}    {theme.dim(part)}")

    if found.horizon:
        lines.extend(["", rule, "", f"  {theme.label('how far back the records reach')}", ""])
        edge = max(len(check.name) for check in found.horizon)
        for check in found.horizon:
            lines.append(
                f"  {theme.paint(check.name.ljust(edge), 'body')}  {theme.dim(check.detail)}"
            )
        lines.append("")
        lines.append(
            _note_line(
                theme, "A file older than a source's oldest record cannot be resolved from it."
            )
        )

    lines.append("")
    return "\n".join(lines)


def _note_line(theme: Theme, text: str) -> str:
    return f"  {theme.dim(theme.clip(text, theme.width - 4))}"


def _whose_machine(theme: Theme, home: Path | None, said: str) -> list[str]:
    """Say whose traces these are, when they are not this machine's.

    Wrapped rather than clipped. A reader who cannot see which profile was read
    cannot check the finding, and half a mount path is worse than none - it
    looks like a path.
    """
    if not home:
        return []
    return [f"  {theme.dim(part)}" for part in theme.wrap(f"{said} {home}", theme.width - 4)]


def render_explain(record: FileRecord, theme: Theme | None = None, home: Path | None = None) -> str:
    """Every source for one file, grouped by the question it answers."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    verdict = reconcile(record)

    name = Path(record.path).name
    lines = ["", f"  {theme.bold('filegrail')}  {theme.dim('explain')}  {theme.bold(name)}", rule]
    if home:
        lines.extend(["", *_whose_machine(theme, home, "evidence read from the profile at")])

    for name_of_kind, question, claims in grouped(record, home):
        head = f"  {theme.label(name_of_kind)}"
        room = theme.width - len(name_of_kind) - 6
        if room >= 12:
            head += f"  {theme.dim(theme.clip(question, room))}"
        lines.extend(["", head, ""])
        for origin in claims:
            lines.extend(_explained(theme, origin))

    lines.extend(
        ["", rule, "", f"  {theme.label('reconciliation')}  {theme.dim(verdict.headline)}", ""]
    )
    # Wide enough for the longest kind there is. Clipping it would leave two
    # findings sharing a prefix and no way to tell which is which - and this
    # report does not truncate what it was asked to show.
    tag_width = max(len(kind) for kind in KINDS)
    for finding in verdict.findings:
        for index, part in enumerate(theme.wrap(finding.text, theme.width - 6 - tag_width)):
            tag = theme.dim(theme.clip(finding.kind, tag_width).ljust(tag_width))
            lines.append(
                f"    {tag if index == 0 else ' ' * tag_width} {theme.paint(part, 'body')}"
            )
    if not verdict.findings:
        lines.append(f"    {theme.dim('nothing to reconcile')}")

    lines.extend(["", rule, "", f"  {theme.label('conclusion')}", ""])
    for sentence in conclusion(record, verdict, home):
        for part in theme.wrap(sentence, theme.width - 6):
            lines.append(f"    {theme.paint(part, 'body')}")
        lines.append("")
    return "\n".join(lines)


def _explained(theme: Theme, origin: Origin) -> list[str]:
    """One claim: what it says, then the detail underneath.

    The label column and the strength both give way on a narrow terminal, in
    that order, because what the record actually says is the part worth keeping.
    """
    colour = theme.evidence(origin.source)
    name = label(origin)
    word = STRENGTH.get(colour, colour)
    said = origin.url or origin.command or origin.tool or origin.note or "(no detail)"

    column = min(20, max(10, theme.width // 3))
    room = theme.width - 4 - column - 2 - len(word)
    show_strength = room >= 12
    if not show_strength:
        room = theme.width - 4 - column

    lines = []
    for index, part in enumerate(theme.wrap(said, room)):
        head = theme.paint(theme.clip(name, column).ljust(column), colour)
        if index:
            head = " " * column
        tail = f"  {theme.dim(word)}" if index == 0 and show_strength else ""
        lines.append(f"    {head}{theme.paint(part.ljust(room), 'body')}{tail}".rstrip())

    # Whatever became the headline must not be repeated underneath it.
    detail = [
        value
        for value in (origin.tool, shown(origin.at), origin.geo, origin.location)
        if value and value != said
    ]
    if origin.note and origin.note != said:
        detail.append(origin.note)
    if detail:
        text = theme.glyph(MIDDOT).join(f" {value} " for value in detail).strip()
        for part in theme.wrap(text, theme.width - 6 - column):
            lines.append(f"    {' ' * column}{theme.dim(part)}")
    lines.append("")
    return lines


def render_compare(
    left: FileRecord, right: FileRecord, found: Comparison, theme: Theme | None = None
) -> str:
    """What two files share, where they differ, and how each one arrived."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    names = [Path(record.path).name for record in (left, right)]

    lines = [
        "",
        f"  {theme.bold('filegrail')}  {theme.dim('compare')}  "
        f"{theme.bold(names[0])} {theme.dim(theme.glyph(MIDDOT))} {theme.bold(names[1])}",
        rule,
    ]

    width = max(
        [len(name) for name, _ in found.shared]
        + [len(name) for name, _, _ in found.differing]
        + [len(name) for name, _ in found.acquisition]
        + [8]
    )

    if found.shared:
        lines.extend(["", f"  {theme.label('identical')}", ""])
        for name, value in found.shared:
            lines.extend(_pair(theme, name, value, width, "recorded"))

    if found.differing:
        lines.extend(["", f"  {theme.label('differing')}", ""])
        for name, one, other in found.differing:
            lines.extend(_pair(theme, name, f"{one}  vs  {other}", width, "warning"))

    lines.extend(["", f"  {theme.label('arrived by')}", ""])
    for name, route in found.acquisition:
        lines.extend(_pair(theme, name, route, width, "inherited"))

    if found.interval:
        lines.extend(["", f"  {theme.label('created')}", ""])
        lines.extend(_pair(theme, "apart", found.interval, width, "body"))

    lines.extend(["", rule, "", f"  {theme.label('assessment')}", ""])
    for part in theme.wrap(found.assessment, theme.width - 6):
        lines.append(f"    {theme.paint(part, 'body')}")
    lines.append("")
    return "\n".join(lines)


def _pair(theme: Theme, name: str, value: str, width: int, colour: str) -> list[str]:
    room = theme.width - 6 - width
    lines = []
    for index, part in enumerate(theme.wrap(value, room)):
        head = theme.dim(name.ljust(width)) if index == 0 else " " * width
        lines.append(f"    {head}  {theme.paint(part, colour)}")
    return lines


def document(shape: str, payload: dict[str, object]) -> str:
    """Render one machine-readable document, stamped with what it is.

    The stamp goes first so that reading the head of a piped document is enough
    to identify it, and it is two fields because they answer two questions. The
    schema says how to read what follows; the version says which build wrote
    it, which is what a bug report needs.

    The schema number is a contract rather than a build number, so it moves
    only when a field changes meaning or leaves - never merely because the
    release did.
    """
    stamped: dict[str, object] = {
        "schema": f"filegrail.{shape}/{SCHEMA}",
        "filegrail_version": __version__,
    }
    stamped.update(payload)
    return json.dumps(stamped, ensure_ascii=False, indent=2)


def _whose(home: Path | None) -> dict[str, object]:
    """Name the profile the evidence came from, when it is not this machine's.

    Absent by default, because a key that is always there says nothing. Present
    means these claims describe another machine, which a consumer has to know
    before it files them against the one it is running on.
    """
    return {"home": str(home)} if home else {}


def render_json_doctor(found: Survey, home: Path | None = None) -> str:
    return document("doctor", {**_whose(home), **found.to_dict()})


def render_json_explain(record: FileRecord, home: Path | None = None) -> str:
    verdict = reconcile(record)
    return document(
        "explain",
        {
            **_whose(home),
            "file": record.to_dict(),
            "reconciliation": verdict.to_dict(),
            "conclusion": conclusion(record, verdict, home),
        },
    )


def render_json_compare(left: FileRecord, right: FileRecord, home: Path | None = None) -> str:
    from .compare import compare

    return document("compare", {**_whose(home), **compare(left, right).to_dict()})


def render_json(
    records: list[FileRecord],
    root: Path,
    *,
    identify: bool = False,
    cluster: bool = False,
    home: Path | None = None,
    unsearched: Unsearched | None = None,
) -> str:
    payload: dict[str, object] = {
        "root": str(root),
        **_whose(home),
        "files": [_file_json(record) for record in records],
        "summary": {
            "total": len(records),
            "with_origin": sum(1 for record in records if record.origins),
        },
    }
    payload["unsearched"] = (unsearched or Unsearched()).to_dict()
    if identify:
        payload["identifiers"] = [entry.to_dict() for entry in extract(records)]
    if cluster:
        payload["shared_sources"] = [group.to_dict() for group in group_sources(records)]

    return document("scan", payload)


def render_timeline(
    records: list[FileRecord], root: Path, *, theme: Theme | None = None, home: Path | None = None
) -> str:
    theme = theme or detect()
    events: list[tuple[str, str, str, str]] = []

    for record in records:
        name = _relative(record.path, root)
        for origin in record.origins:
            when = origin.at or record.btime or record.mtime
            if when:
                events.append((when, name, _headline(origin, record), origin.source))
        if not record.origins:
            when = record.btime or record.mtime
            if when:
                events.append((when, name, "(nothing found)", "filesystem"))

    if not events:
        return "No datable events found."

    stamp_width = 21
    rail = theme.rail_glyph()
    # Only when there is one, so anything already reading a line per event from
    # a scan of this machine sees exactly what it saw before.
    lines = [*_whose_machine(theme, home, "evidence read from the profile at"), ""] if home else []
    for when, name, detail, source in sorted(events):
        colour = theme.evidence(source)
        moment = theme.dim(when[:19].replace("T", " "))
        under = " " * (stamp_width - 2)

        for index, part in enumerate(theme.wrap(name, theme.width - stamp_width - 4)):
            head = f"  {moment}  " if index == 0 else f"  {under}  "
            lines.append(f"{head}{theme.bold(part)}")
        for part in theme.wrap(detail, theme.width - stamp_width - 6):
            lines.append(f"  {under}{rail} {theme.paint(part, colour)}")
    return "\n".join(lines)


# --- shared ------------------------------------------------------------------


def _relative(path: str, root: Path) -> str:
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return path


def _display(root: Path) -> str:
    try:
        return "~/" + str(root.relative_to(Path.home()))
    except ValueError:
        return str(root)


def _moment(value: str | None) -> str:
    """A timestamp trimmed to the second.

    Filesystem times carry microseconds, which are noise in a column meant to be
    compared by eye and never precise enough to be evidence on their own.
    """
    if not value:
        return ""
    head = value[:19]
    return f"{head}Z" if value.endswith("Z") else head


def _size(value: int) -> str:
    for unit, threshold in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if value >= threshold:
            return f"{value / threshold:.1f} {unit}"
    return f"{value} B"


def _visible(text: str) -> int:
    """Length of `text` as printed, ignoring escape sequences."""
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


# --- clean -------------------------------------------------------------------


def render_clean(
    results: list[Cleaned],
    source: Path,
    destination: Path | None,
    *,
    theme: Theme | None = None,
    check: bool = False,
) -> str:
    """What each file gave up, and what it did not.

    Under `check` nothing was written, so nothing is said to have been: the
    same rows, in the conditional. A destination is optional there and may be
    None, because a check can be asked without one.
    """
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    # What came out is the discriminator rather than where the copy went. In a
    # run that writes the two agree; in a check there is no copy to point at,
    # and a summary that counted those would report nothing done at all.
    cleaned = [item for item in results if item.removed]
    survived = [item for item in cleaned if item.remaining]

    lines = [
        "",
        f"  {theme.bold('filegrail')}  {theme.dim('clean')}  {theme.bold(str(source))}",
        rule,
        "",
        f"  {_destination(theme, destination, check)}",
        "",
    ]

    for item in results:
        name = _relative(str(item.path), source)
        said = ", ".join(item.removed) if item.removed else theme.dim(item.note or "nothing")
        colour = "recorded" if item.removed else "faint"
        lines.append(_row(theme, f"  {_mark(theme, BULLET, colour)} ", name, theme.dim(said)))

    lines.extend(["", rule])
    lines.append(
        f"    {len(results)} files {MIDDOT} {len(cleaned)} "
        f"{'would be cleaned' if check else 'cleaned'} {MIDDOT} "
        f"{len(results) - len(cleaned)} left alone"
    )

    if survived:
        # The whole point of reading the copies back. A file reported as
        # cleaned that is not cleaned is worse than one nobody touched.
        seen = "readable in the copies"
        warning = f"would still be {seen}" if check else f"still {seen}"
        lines.extend(["", f"  {theme.paint(warning, 'conflict')}"])
        for item in survived:
            # A written copy is named where it lies, since that is the file
            # somebody would publish. A check has no copy, so it names the
            # original, which is the only thing it can point at.
            where = (
                _relative(str(item.path), source)
                if item.written is None
                else _relative(str(item.written), destination or source)
            )
            lines.append(f"    {where}  {theme.dim(', '.join(item.remaining))}")
        lines.append(
            f"  {theme.dim('a stripper is written per format, and a format can carry a block')}"
        )
        lines.append(f"  {theme.dim('somewhere it does not reach. Do not publish these.')}")

    lines.append("")
    return "\n".join(lines)


def _destination(theme: Theme, destination: Path | None, check: bool) -> str:
    """Where the copies went, or the fact that none did."""
    if not check:
        return f"{theme.dim('copies written to')}  {theme.paint(str(destination), 'body')}"
    if destination is None:
        return theme.dim("nothing written")
    return (
        f"{theme.dim('nothing written; copies would go to')}  "
        f"{theme.paint(str(destination), 'body')}"
    )


def render_json_clean(
    results: list[Cleaned], source: Path, destination: Path | None, *, check: bool = False
) -> str:
    found: dict[str, object] = {"root": str(source)}
    if check:
        # Said outright rather than left to be inferred from an absent
        # `written`: every count below is in the conditional, and a reader that
        # takes them for a record of what happened has been misled.
        found["checked"] = True
    if destination is not None:
        found["destination"] = str(destination)
    found["files"] = [item.to_dict() for item in results]
    found["summary"] = {
        "total": len(results),
        "cleaned": sum(1 for item in results if item.removed),
        "still_readable": sum(1 for item in results if item.remaining),
    }
    return document("clean", found)
