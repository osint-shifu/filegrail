"""Command line interface. Standard library only, no runtime dependencies."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .report import render_json, render_text, render_timeline
from .scan import scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whence",
        description="Reconstruct where the files in a directory came from, after the fact.",
        epilog="whence reads records that already exist. It never asks you to change how you work.",
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
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        metavar="N",
        help="Cap the list of files with no recorded origin (default: 25).",
    )
    parser.add_argument(
        "--unknown-only",
        action="store_true",
        help="List only files with no recorded origin.",
    )
    parser.add_argument("--version", action="version", version=f"whence {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = args.path.resolve()
    if not root.exists():
        print(f"whence: no such file or directory: {args.path}", file=sys.stderr)
        return 2

    stats: dict[str, int] = {}
    records = scan(
        root,
        recursive=not args.no_recurse,
        hash_files=args.hash_files,
        use_shell_history=not args.no_shell_history,
        follow_archives=not args.no_archives,
        stats=stats,
    )

    if args.unknown_only:
        records = [record for record in records if not record.origins]

    base = root if root.is_dir() else root.parent
    if args.json:
        print(render_json(records, base))
    elif args.timeline:
        print(render_timeline(records, base))
    else:
        print(render_text(records, base, verbose=args.verbose, limit=args.limit, stats=stats))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
