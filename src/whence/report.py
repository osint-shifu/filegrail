"""Render scan results as text or JSON."""

from __future__ import annotations

import json
from pathlib import Path

from .models import FileRecord

_ARROW = "  <- "


def _shorten(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[: width - 1] + "…"


def render_text(records: list[FileRecord], root: Path, *, verbose: bool = False) -> str:
    lines: list[str] = []
    known = [record for record in records if record.origins]
    unknown = [record for record in records if not record.origins]

    for record in known:
        relative = Path(record.path)
        try:
            relative = relative.relative_to(root)
        except ValueError:
            pass
        lines.append(str(relative))

        origins = record.origins if verbose else [record.best]
        for origin in origins:
            if origin is None:
                continue
            target = origin.url or origin.command or origin.tool or "(no detail)"
            stamp = origin.at or record.btime or record.mtime
            lines.append(f"{_ARROW}{_shorten(target, 96)}")
            detail = f"     {origin.source}"
            if origin.tool and origin.tool not in target:
                detail += f" / {origin.tool}"
            if stamp:
                detail += f"  {stamp}"
            detail += f"  confidence {origin.confidence}"
            lines.append(detail)
            if verbose and origin.referrer:
                lines.append(f"     referrer  {_shorten(origin.referrer, 88)}")
            if origin.note:
                lines.append(f"     note      {origin.note}")
        lines.append("")

    if unknown:
        lines.append(f"No recorded origin ({len(unknown)}):")
        for record in unknown:
            relative = Path(record.path)
            try:
                relative = relative.relative_to(root)
            except ValueError:
                pass
            lines.append(f"  {relative}    created {record.btime or record.mtime}")
        lines.append("")

    lines.append(f"{len(known)} of {len(records)} files have a recorded origin.")
    return "\n".join(lines)


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


def render_timeline(records: list[FileRecord], root: Path) -> str:
    events: list[tuple[str, str, str]] = []
    for record in records:
        relative = Path(record.path)
        try:
            relative = relative.relative_to(root)
        except ValueError:
            pass
        for origin in record.origins:
            when = origin.at or record.btime or record.mtime
            if when:
                events.append((when, str(relative), origin.url or origin.command or origin.source))
        if not record.origins:
            when = record.btime or record.mtime
            if when:
                events.append((when, str(relative), "(no recorded origin)"))

    lines = [f"{when}  {name}\n    {_shorten(detail, 96)}" for when, name, detail in sorted(events)]
    return "\n".join(lines) if lines else "No datable events found."
