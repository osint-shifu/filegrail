"""Render scan results.

The default rendering is styled for a terminal and degrades to the identical
layout in plain text when the output is piped or colour is unwanted, so the
same command reads well by eye and greps cleanly.

The layout is specified in `DESIGN.md`. Two ideas carry it: a one-character left
gutter groups the lines of an entry without a box, and colour is spent only on
saying which class of source made a claim.
"""

from __future__ import annotations

import json
from pathlib import Path

from .explain import conclusion, grouped
from .identify import Identifier, extract
from .models import ACQUISITION, INTRINSIC, SOURCE_LABELS, FileRecord, Origin, kind
from .reconcile import ATTRIBUTION_CONFLICT, CONFLICT, KINDS, PARTIAL, Verdict, reconcile
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

#: Sources describing what a file says about itself, rather than where it came from.
SELF_REPORTED = frozenset(
    {"document-metadata", "device-metadata", "c2pa", "xmp", "xmp-history", "iptc"}
)

#: Width of the label column inside an entry, so values line up across labels.
_LABEL = 10

#: Where an entry's text begins: two spaces, the gutter glyph, one space.
_INDENT = 4


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


def _row(theme: Theme, prefix: str, body: str, right: str, *, paint=None, wrap: bool = True) -> str:
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
    limit: int = 25,
    stats: dict[str, int] | None = None,
    theme: Theme | None = None,
    filtered: str = "",
    identify: bool = False,
) -> str:
    theme = theme or detect()
    known = [record for record in records if record.origins]
    unknown = [record for record in records if not record.origins]

    lines = _masthead(theme, root, len(records), len(known))
    lines.extend(_sections(theme, known, root, verbose=verbose, brief=brief))

    if unknown:
        lines.extend(_unknown(theme, unknown, root, limit))

    if identify:
        lines.extend(_identifiers(theme, extract(records)))

    lines.extend(_summary(theme, records, known, stats, filtered))
    return "\n".join(lines)


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
        value = theme.paint(theme.clip(entry.normalized, width).ljust(width), colour)
        kind = theme.dim(entry.type.ljust(7))
        seen = theme.dim(f"{entry.count} in {entry.files}")
        lines.append(f"    {kind} {value}  {seen}")
        lines.append(f"    {' ' * 8}{theme.dim(theme.clip(entry.where[0], theme.width - 14))}")
    lines.append("")
    return lines


def _masthead(theme: Theme, root: Path, total: int, traced: int) -> list[str]:
    prefix = f"  {theme.bold('filetrail')}  "
    count = theme.label(f"{traced} of {total} traced")

    # The meter is decoration and the count is the information, so on a narrow
    # terminal the meter goes first rather than the path being clipped to nothing.
    right = f"{theme.coverage(traced, total)}  {count}"
    if _visible(prefix) + _visible(right) + 12 > theme.width:
        right = count

    return [
        "",
        _row(theme, prefix, _display(root), right, paint=theme.dim),
        f"  {theme.rule(theme.width - 2)}",
        "",
    ]


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


def _heading(theme: Theme, text: str, count: int, noun: str = "file") -> list[str]:
    right = theme.dim(f"{count} {noun}" + ("" if count == 1 else "s"))
    return [
        _row(theme, "  ", text, right, paint=theme.label),
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
        claims = list(record.origins)
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
    lines.append("")
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
    label = theme.paint(verdict.headline, colour)

    lines = [f"  {_mark(theme, FLAG, colour)} {label}"]
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

    facts = [SOURCE_LABELS.get(origin.source, origin.source)]
    if origin.tool and origin.tool not in claim:
        facts.append(origin.tool)
    stamp = origin.at if origin.source in SELF_REPORTED else (origin.at or record.btime)
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

    for label, value, paint in _facts(origin):
        for index, part in enumerate(theme.wrap(value, theme.width - indent - _LABEL)):
            head = theme.dim(label.ljust(_LABEL)) if index == 0 else " " * _LABEL
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
    width = min(max(len(name) for name in fields), 24)
    room = theme.width - indent - width - 2
    items = list(fields.items())

    out = [f"  {_mark(theme, RAIL)}".rstrip()]
    for index, (name, value) in enumerate(items):
        last = index == len(items) - 1
        branch = _mark(theme, LAST if last else BRANCH)
        label = theme.dim(theme.clip(name, width).ljust(width))
        spacer = " " * len(theme.glyph(ARROW)) if last else _mark(theme, RAIL)

        for line, part in enumerate(theme.wrap(str(value), room)):
            gutter = branch if line == 0 else spacer
            head = label if line == 0 else " " * width
            out.append(f"  {gutter} {head}  {theme.paint(part, 'body')}")
    return out


def _facts(origin: Origin) -> list[tuple[str, str, str | None]]:
    """The labelled lines under a claim, in a fixed order."""
    found = []
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
    shown = unknown if limit <= 0 else unknown[:limit]
    lines = _heading(theme, "no recorded origin", len(unknown))

    for record in shown:
        when = theme.dim(_moment(record.btime or record.mtime))
        prefix = " " * _INDENT
        lines.append(_row(theme, prefix, _relative(record.path, root), when, paint=theme.dim))

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
    stats: dict[str, int] | None,
    filtered: str = "",
) -> list[str]:
    counts: dict[str, int] = {}
    confidence: dict[str, int] = {}
    for record in known:
        if record.best:
            counts[record.best.source] = counts.get(record.best.source, 0) + 1
            confidence[record.best.source] = record.best.confidence

    lines = [f"  {theme.rule(theme.width - 2)}"]

    if counts:
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        widest = max(len(SOURCE_LABELS.get(source, source)) for source, _ in ordered)
        digits = max(len(str(count)) for _, count in ordered)
        for source, count in ordered:
            colour = theme.evidence(source)
            label = theme.paint(SOURCE_LABELS.get(source, source).ljust(widest), colour)
            meter = theme.meter(confidence[source], colour)
            lines.append(f"    {label}  {meter}  {theme.dim(str(count).rjust(digits))}")
        lines.append("")

    total = theme.bold(f"{len(known)} of {len(records)}")
    lines.append(f"    {total} files have a recorded origin.")

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


def render_doctor(found, theme: Theme | None = None) -> str:
    """What could be searched on this machine, and how far back it reaches."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    width = max(len(check.name) for check in found.checks)

    lines = ["", f"  {theme.bold('filetrail')}  {theme.dim('evidence sources')}", rule, ""]

    for check in found.checks:
        colour = {
            "available": "recorded",
            "partial": "circumstantial",
        }.get(check.state, "warning")
        label = theme.paint(check.name.ljust(width), "body")
        state = theme.paint(check.state, colour)
        lines.append(f"  {label}  {state}")
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
            _note_line(theme, "A file older than this cannot be resolved from browser history.")
        )

    lines.append("")
    return "\n".join(lines)


def _note_line(theme: Theme, text: str) -> str:
    return f"  {theme.dim(theme.clip(text, theme.width - 4))}"


def render_explain(record: FileRecord, theme: Theme | None = None) -> str:
    """Every source for one file, grouped by the question it answers."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    verdict = reconcile(record)

    name = Path(record.path).name
    lines = ["", f"  {theme.bold('filetrail')}  {theme.dim('explain')}  {theme.bold(name)}", rule]

    for name_of_kind, question, claims in grouped(record):
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
    for sentence in conclusion(record, verdict):
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
    label = SOURCE_LABELS.get(origin.source, origin.source)
    word = STRENGTH.get(colour, colour)
    said = origin.url or origin.command or origin.tool or origin.note or "(no detail)"

    column = min(20, max(10, theme.width // 3))
    room = theme.width - 4 - column - 2 - len(word)
    show_strength = room >= 12
    if not show_strength:
        room = theme.width - 4 - column

    lines = []
    for index, part in enumerate(theme.wrap(said, room)):
        head = theme.paint(theme.clip(label, column).ljust(column), colour)
        if index:
            head = " " * column
        tail = f"  {theme.dim(word)}" if index == 0 and show_strength else ""
        lines.append(f"    {head}{theme.paint(part.ljust(room), 'body')}{tail}".rstrip())

    # Whatever became the headline must not be repeated underneath it.
    detail = [
        value
        for value in (origin.tool, origin.at, origin.geo, origin.location)
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


def render_compare(left: FileRecord, right: FileRecord, found, theme: Theme | None = None) -> str:
    """What two files share, where they differ, and how each one arrived."""
    theme = theme or detect()
    rule = f"  {theme.rule(theme.width - 2)}"
    names = [Path(record.path).name for record in (left, right)]

    lines = [
        "",
        f"  {theme.bold('filetrail')}  {theme.dim('compare')}  "
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


def render_json_doctor(found) -> str:
    return json.dumps(found.to_dict(), ensure_ascii=False, indent=2)


def render_json(records: list[FileRecord], root: Path, *, identify: bool = False) -> str:
    payload: dict[str, object] = {
        "root": str(root),
        "files": [_file_json(record) for record in records],
        "summary": {
            "total": len(records),
            "with_origin": sum(1 for record in records if record.origins),
        },
    }
    if identify:
        payload["identifiers"] = [entry.to_dict() for entry in extract(records)]

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def render_timeline(records: list[FileRecord], root: Path, *, theme: Theme | None = None) -> str:
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
                events.append((when, name, "(no recorded origin)", "filesystem"))

    if not events:
        return "No datable events found."

    stamp_width = 21
    rail = theme.rail_glyph()
    lines = []
    for when, name, detail, source in sorted(events):
        colour = theme.evidence(source)
        moment = theme.dim(when[:19].replace("T", " "))
        lines.append(f"  {moment}  {theme.bold(theme.clip(name, theme.width - stamp_width - 4))}")
        claim = theme.clip(detail, theme.width - stamp_width - 6)
        lines.append(f"  {' ' * (stamp_width - 2)}{rail} {theme.paint(claim, colour)}")
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
