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

from .identify import Identifier, extract
from .models import FileRecord, Origin
from .theme import ARROW, BULLET, EVIDENCE_HEADINGS, MIDDOT, Theme, detect

#: Sources describing what a file says about itself, rather than where it came from.
SELF_REPORTED = frozenset({"document-metadata", "device-metadata", "c2pa"})

#: How each source reads in a summary line.
SOURCE_LABELS = {
    "browser-download": "browser download",
    "windows-zone-identifier": "Windows zone",
    "macos-wherefroms": "macOS where-from",
    "xdg-xattr": "XDG attribute",
    "archive-member": "archive member",
    "c2pa": "content credentials",
    "device-metadata": "device metadata",
    "document-metadata": "document metadata",
    "shell-history": "shell history",
    "filesystem": "filesystem",
}

#: Width of the label column inside an entry, so values line up across labels.
_LABEL = 10

#: Where an entry's text begins: two spaces, one gutter glyph, one space.
_INDENT = 4


def _row(theme: Theme, prefix: str, body: str, right: str, *, paint=None) -> str:
    """One line carrying a single right-aligned column.

    `prefix` and `right` arrive painted, so only their visible width matters.
    `body` arrives plain and is clipped to whatever the right-hand column leaves
    before being painted - clipping afterwards would cut an escape sequence in
    half, and not clipping at all is how a narrow terminal wraps into nonsense.
    """
    room = theme.width - _visible(prefix) - _visible(right) - 2
    body = theme.clip(body, max(8, room))
    painted = paint(body) if paint else body
    gap = max(1, theme.width - _visible(prefix) - _visible(painted) - _visible(right))
    return f"{prefix}{painted}{' ' * gap}{right}"


def render_text(
    records: list[FileRecord],
    root: Path,
    *,
    verbose: bool = False,
    full: bool = False,
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
    lines.extend(_sections(theme, known, root, verbose=verbose, full=full))

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
    theme: Theme, known: list[FileRecord], root: Path, *, verbose: bool, full: bool
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
            lines.extend(_entry(theme, record, root, verbose=verbose, full=full))

    for members in grouped.values():  # any class the table above did not name
        for record in members:
            lines.extend(_entry(theme, record, root, verbose=verbose, full=full))
    return lines


def _heading(theme: Theme, text: str, count: int, noun: str = "file") -> list[str]:
    right = theme.dim(f"{count} {noun}" + ("" if count == 1 else "s"))
    return [
        _row(theme, "  ", text, right, paint=theme.label),
        f"  {theme.rule(theme.width - 2)}",
        "",
    ]


def _entry(theme: Theme, record: FileRecord, root: Path, *, verbose: bool, full: bool) -> list[str]:
    colour = theme.evidence(record.best.source if record.best else "filesystem")
    prefix = f"  {theme.paint(theme.glyph(BULLET), colour)} "
    lines = [
        _row(
            theme,
            prefix,
            _relative(record.path, root),
            theme.dim(_size(record.size)),
            paint=theme.bold,
        )
    ]

    for origin in record.origins if verbose else [record.best]:
        if origin is not None:
            lines.extend(_origin(theme, origin, record, full=full))
    lines.append("")
    return lines


def _origin(theme: Theme, origin: Origin, record: FileRecord, *, full: bool = False) -> list[str]:
    colour = theme.evidence(origin.source)
    arrow = theme.paint(theme.glyph(ARROW), colour)
    rail = theme.rail_glyph()

    headline = _headline(origin, record)
    room = theme.width - _INDENT - len(theme.glyph(ARROW))
    lines = [f"  {arrow} {theme.paint(theme.clip(headline, room), colour)}"]

    facts = [SOURCE_LABELS.get(origin.source, origin.source)]
    if origin.tool and origin.tool not in headline:
        facts.append(origin.tool)
    stamp = origin.at if origin.source in SELF_REPORTED else (origin.at or record.btime)
    if stamp:
        facts.append(stamp)
    detail = theme.glyph(MIDDOT).join(f" {fact} " for fact in facts).strip()

    meter = f"{theme.meter(origin.confidence, colour)} {theme.dim(str(origin.confidence))}"
    lines.append(_row(theme, f"  {rail} ", detail, meter, paint=theme.label))

    for label, value, paint in _facts(origin):
        text = theme.clip(value, theme.width - _INDENT - _LABEL)
        painted = theme.paint(text, paint) if paint else theme.dim(text)
        lines.append(f"  {rail} {theme.dim(label.ljust(_LABEL))}{painted}")

    if full and origin.fields:
        lines.extend(_fields_block(theme, rail, origin.fields))
    return lines


def _fields_block(theme: Theme, rail: str, fields: dict[str, str]) -> list[str]:
    """Every decoded field, one per line, in the entry's own rail.

    The label column is sized to the names actually present rather than to a
    constant: EXIF names run to seventeen characters and a fixed column would
    either waste width on every other reader or wrap on this one.
    """
    width = min(max(len(name) for name in fields), 24)
    room = theme.width - _INDENT - width - 2
    out = [f"  {rail}"]
    for name, value in fields.items():
        label = theme.dim(theme.clip(name, width).ljust(width))
        out.append(f"  {rail} {label}  {theme.paint(theme.clip(str(value), room), 'body')}")
    return out


def _facts(origin: Origin) -> list[tuple[str, str, str | None]]:
    """The labelled lines under a claim, in a fixed order."""
    found = []
    if origin.location:
        found.append(("location", origin.location, "circumstantial"))
    if origin.referrer:
        found.append(("referrer", origin.referrer, None))
    if origin.note:
        found.append(("note", origin.note, None))
    return found


def _headline(origin: Origin, record: FileRecord) -> str:
    if origin.source in SELF_REPORTED:
        if origin.tool:
            return f"made by {origin.tool}"
        if origin.location:
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


def render_json(records: list[FileRecord], root: Path, *, identify: bool = False) -> str:
    payload: dict[str, object] = {
        "root": str(root),
        "files": [record.to_dict() for record in records],
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
