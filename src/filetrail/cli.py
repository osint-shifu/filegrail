"""Command line interface. Standard library only, no runtime dependencies."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .filters import UnknownType, describe, selection
from .report import render_doctor, render_json, render_json_doctor, render_text, render_timeline
from .scan import scan
from .theme import detect


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filetrail",
        description="Reconstruct where the files in a directory came from, after the fact.",
        epilog="filetrail reads records that already exist. "
        "It never asks you to change how you work.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="File or directory to examine (default: current directory).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="Emit one chronological line per event instead of grouping by file.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show every origin claim, not only the highest-confidence one.",
    )
    parser.add_argument(
        "--identify",
        action="store_true",
        help="List the emails, domains, URLs, addresses, hashes and coordinates "
        "found in the metadata that was read.",
    )
    parser.add_argument(
        "--type",
        dest="families",
        action="append",
        default=[],
        metavar="NAME",
        help="Only these kinds of file: image, video, audio, document, archive, text. "
        "Repeatable, and accepts a comma-separated list.",
    )
    parser.add_argument(
        "--ext",
        dest="extensions",
        action="append",
        default=[],
        metavar="LIST",
        help="Only these extensions, e.g. --ext jpg,pdf. The leading dot is optional.",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Summarise each file instead of listing every metadata field.",
    )
    parser.add_argument(
        "--no-recurse", action="store_true", help="Do not descend into subdirectories."
    )
    parser.add_argument(
        "--no-shell-history",
        action="store_true",
        help="Skip shell history correlation.",
    )
    parser.add_argument(
        "--hash",
        action="store_true",
        dest="hash_files",
        help="Compute SHA-256 for each file.",
    )
    parser.add_argument(
        "--no-archives",
        action="store_true",
        help="Do not inherit origins from archives the files were extracted from.",
    )
    colour = parser.add_mutually_exclusive_group()
    colour.add_argument(
        "--color",
        "--colour",
        dest="colour",
        action="store_true",
        default=None,
        help="Force styled output even when not writing to a terminal.",
    )
    colour.add_argument(
        "--no-color",
        "--no-colour",
        dest="colour",
        action="store_false",
        help="Plain text with no escape sequences.",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Remove credentials from URLs and commands before printing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        metavar="N",
        help="Cap the list of files with no recorded origin; 0 for all (default: 25).",
    )
    parser.add_argument(
        "--unknown-only",
        action="store_true",
        help="List only files with no recorded origin.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Report which evidence sources this machine has, and how far back they reach.",
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Print what this is, who wrote it, and how to use it.",
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Choose what to run from a list instead of remembering flags.",
    )
    parser.add_argument("--version", action="version", version=f"filetrail {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    given = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)

    # A bare run introduces the tool rather than scanning the current directory.
    # Starting an unasked-for scan of wherever the shell happens to be is a
    # surprise, and in a home directory an expensive one.
    if args.about or not given:
        from .about import render

        print(render(detect(colour=args.colour)))
        return 0

    if args.doctor:
        from .doctor import survey

        found = survey()
        theme = detect(colour=args.colour)
        print(render_json_doctor(found) if args.json else render_doctor(found, theme))
        return 0

    if args.menu:
        return _menu(args.path)

    root = args.path.resolve()
    if not root.exists():
        print(f"filetrail: no such file or directory: {args.path}", file=sys.stderr)
        return 2

    try:
        suffixes = selection(args.families, args.extensions)
    except UnknownType as unknown:
        print(f"filetrail: {unknown}", file=sys.stderr)
        return 2

    stats: dict[str, int] = {}
    records = scan(
        root,
        recursive=not args.no_recurse,
        hash_files=args.hash_files,
        use_shell_history=not args.no_shell_history,
        follow_archives=not args.no_archives,
        suffixes=suffixes,
        stats=stats,
    )

    if args.unknown_only:
        records = [record for record in records if not record.origins]

    if args.redact:
        records = [record.redacted() for record in records]

    base = root if root.is_dir() else root.parent
    theme = detect(colour=args.colour)

    if args.json:
        print(render_json(records, base, identify=args.identify))
    elif args.timeline:
        print(render_timeline(records, base, theme=theme))
    else:
        print(
            render_text(
                records,
                base,
                verbose=args.verbose,
                brief=args.brief,
                limit=args.limit,
                stats=stats,
                theme=theme,
                filtered=describe(args.families, args.extensions),
                identify=args.identify,
            )
        )

    return 0


def _menu(start: Path) -> int:
    """Hand over to the interactive front end, if there is a terminal for it."""
    from . import menu

    if not menu.available():
        print(
            "filetrail: --menu needs a terminal; it cannot be piped or redirected.",
            file=sys.stderr,
        )
        return 2
    if not start.exists():
        print(f"filetrail: no such file or directory: {start}", file=sys.stderr)
        return 2

    return menu.run(start, execute=main)


if __name__ == "__main__":
    raise SystemExit(main())
