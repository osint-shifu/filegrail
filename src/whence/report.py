"""Render scan results.

The default rendering is styled for a terminal and degrades to the identical
layout in plain text when the output is piped or colour is unwanted, so the
same command reads well by eye and greps cleanly.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import FileRecord, Origin
from .theme import ARROW, BULLET, MIDDOT, SOURCE_COLOURS, Theme, detect

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


def render_text(
    records: list[FileRecord],
    root: Path,
    *,
    verbose: bool = False,
    limit: int = 25,
    stats: dict[str, int] | None = None,
    theme: Theme | None = None,
) -> str:
    theme = theme or detect()
    known = [record for record in records if record.origins]
    unknown = [record for record in records if not record.origins]

    lines = _header(theme, root, len(records), len(known))
    for record in known:
        lines.extend(_entry(theme, record, root, verbose=verbose))

    if unknown:
        lines.extend(_unknown(theme, unknown, root, limit))

    lines.extend(_summary(theme, records, known, stats))
    return "\n".join(lines)


def _header(theme: Theme, root: Path, total: int, traced: int) -> list[str]:
    name = theme.bold("whence")
    where = theme.paint(_display(root), "white")
    count = theme.dim(f"{traced}/{total} traced")
    gap = max(1, theme.width - _visible(f"{name} {where}") - _visible(count))
    return ["", f"{name} {where}{' ' * gap}{count}", theme.rule(), ""]


def _entry(theme: Theme, record: FileRecord, root: Path, *, verbose: bool) -> list[str]:
    colour = SOURCE_COLOURS.get((record.best.source if record.best else ""), "grey")
    bullet = theme.paint(theme.glyph(BULLET), colour)
    name = theme.bold(_relative(record.path, root))
    size = theme.dim(_size(record.size))

    gap = max(1, theme.width - _visible(f"{bullet} {name}") - _visible(size))
    lines = [f"{bullet} {name}{' ' * gap}{size}"]

    for origin in record.origins if verbose else [record.best]:
        if origin is not None:
            lines.extend(_origin(theme, origin, record))
    lines.append("")
    return lines


def _origin(theme: Theme, origin: Origin, record: FileRecord) -> list[str]:
    colour = SOURCE_COLOURS.get(origin.source, "grey")
    arrow = theme.dim(theme.glyph(ARROW))
    headline = _headline(origin, record)
    lines = [f"  {arrow} {theme.paint(theme.clip(headline, theme.width - 6), colour)}"]

    facts = [SOURCE_LABELS.get(origin.source, origin.source)]
    if origin.tool and origin.tool not in headline:
        facts.append(origin.tool)
    stamp = origin.at if origin.source in SELF_REPORTED else (origin.at or record.btime)
    if stamp:
        facts.append(stamp)
    detail = theme.dim(theme.glyph(MIDDOT).join(f" {fact} " for fact in facts).strip())

    meter = theme.paint(theme.bar(origin.confidence), colour)
    gap = max(1, theme.width - 4 - _visible(detail) - _visible(meter))
    lines.append(f"    {detail}{' ' * gap}{meter}")

    if origin.location:
        lines.append(f"    {theme.dim('location')}  {theme.paint(origin.location, 'yellow')}")
    if origin.referrer:
        lines.append(f"    {theme.dim('referrer')}  {theme.dim(theme.clip(origin.referrer, 70))}")
    if origin.note:
        lines.append(f"    {theme.dim('note')}      {theme.dim(theme.clip(origin.note, 70))}")
    return lines


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
    heading = theme.dim(f"no recorded origin ({len(unknown)})")
    lines = [f"{heading}", theme.rule(), ""]

    for record in shown:
        name = _relative(record.path, root)
        when = theme.dim(record.btime or record.mtime or "")
        gap = max(1, theme.width - 2 - _visible(name) - _visible(when))
        lines.append(f"  {theme.dim(name)}{' ' * gap}{when}")

    if len(shown) < len(unknown):
        hidden = len(unknown) - len(shown)
        lines.append(theme.dim(f"  ... and {hidden} more (--limit 0 for all, --json for each)"))
    lines.append("")
    return lines


def _summary(
    theme: Theme, records: list[FileRecord], known: list[FileRecord], stats: dict[str, int] | None
) -> list[str]:
    counts: dict[str, int] = {}
    for record in known:
        if record.best:
            counts[record.best.source] = counts.get(record.best.source, 0) + 1

    lines = [theme.rule()]
    if counts:
        parts = [
            theme.paint(
                f"{count} {SOURCE_LABELS.get(source, source)}", SOURCE_COLOURS.get(source, "grey")
            )
            for source, count in sorted(counts.items(), key=lambda item: -item[1])
        ]
        lines.append("  " + theme.dim(theme.glyph(MIDDOT).join(f" {p} " for p in parts).strip()))

    total = theme.bold(f"{len(known)} of {len(records)}")
    lines.append(f"  {total} files have a recorded origin.")

    if not known and records:
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
            theme.dim("  No browser profile was readable, so the strongest source"),
            theme.dim("  was unavailable."),
        ]

    return [
        "",
        theme.dim(
            f"  There was little to match against: {downloads} download "
            f"{'record' if downloads == 1 else 'records'} across {profiles} browser "
            f"{'profile' if profiles == 1 else 'profiles'}."
        ),
        theme.dim("  Browsers prune download history (Chromium keeps about 90 days by"),
        theme.dim("  default) and clearing history or migrating a profile discards it,"),
        theme.dim("  so files older than the surviving history cannot be resolved."),
    ]


def render_json(records: list[FileRecord], root: Path) -> str:
    return json.dumps(
        {
            "root": str(root),
            "files": [record.to_dict() for record in records],
            "summary": {
                "total": len(records),
                "with_origin": sum(1 for record in records if record.origins),
            },
        },
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

    lines = []
    for when, name, detail, source in sorted(events):
        colour = SOURCE_COLOURS.get(source, "grey")
        lines.append(f"{theme.dim(when[:19].replace('T', ' '))}  {theme.bold(name)}")
        lines.append(f"{' ' * 21}{theme.paint(theme.clip(detail, theme.width - 22), colour)}")
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
