"""Command line interface. Standard library only, no runtime dependencies.

The tool does several distinct things, and they are commands rather than flags.
`--doctor` and `--explain` were modes wearing an option's clothes: each one
ignored most of the other options, and every pair of them was mutually
exclusive, which is exactly the shape subcommands exist to express.

`filegrail <path>` still scans, with no command word, because that is the thing
people do ninety per cent of the time and making them type `scan` for it would
be ceremony.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .filters import FAMILIES, UnknownType, describe, selection
from .report import (
    render_compare,
    render_doctor,
    render_explain,
    render_json,
    render_json_compare,
    render_json_doctor,
    render_json_explain,
    render_text,
    render_timeline,
)
from .scan import Unsearched, scan
from .theme import detect

if TYPE_CHECKING:  # only for the signatures; the scan brings the real thing
    from .models import FileRecord

COMMANDS = ("scan", "explain", "compare", "doctor", "menu", "clean", "help")


# --- parsers -----------------------------------------------------------------


def _common() -> argparse.ArgumentParser:
    """Options every command understands."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-j", "--json", action="store_true", help="Output machine-readable JSON.")
    colour = shared.add_mutually_exclusive_group()
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
        help="Disable ANSI colors.",
    )
    return shared


def _profile() -> argparse.ArgumentParser:
    """The option for reading a machine that is not this one.

    Every source that answers *how did this arrive* lives under a home
    directory, and the readers have always taken one as an argument. Offering
    it here is what turns `what does my machine remember about my files` into
    `here is a mounted profile, reconstruct what its machine remembered`.
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--home",
        type=Path,
        metavar="DIR",
        help="Read browser, shell and desktop history from this user profile "
        "instead of the current one, e.g. a mounted image.",
    )
    return shared


def _redaction() -> argparse.ArgumentParser:
    """The option for output that is about to leave the machine.

    A parent rather than a member of `_common()` because it belongs to the
    commands that render evidence and to no others: `doctor` prints which
    sources exist, `clean` prints file names and the blocks taken out of them,
    and neither can carry a credential. An option that does nothing is worse
    than an absent one - it reads as a promise.
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--redact", action="store_true", help="Redact credentials before printing.")
    return shared


def build_parser() -> argparse.ArgumentParser:
    """The scan parser, which is also what a bare path is parsed with."""
    parser = argparse.ArgumentParser(
        prog="filegrail scan",
        parents=[_common(), _profile(), _redaction()],
        description="Analyze a file or directory and report where its files came from.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="File or directory to examine (default: current directory).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show every evidence record, not the strongest of each kind.",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Summarise each file instead of listing every metadata field.",
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="Emit one chronological line per event instead of grouping by file.",
    )
    parser.add_argument(
        "--unknown-only", action="store_true", help="List only files nothing was found for."
    )
    parser.add_argument(
        "--identify",
        action="store_true",
        help="List the emails, domains, addresses, hashes and coordinates found.",
    )
    parser.add_argument(
        "--cluster",
        action="store_true",
        help="Group the files by the authors and cameras more than one of them names.",
    )
    parser.add_argument(
        "--hash", action="store_true", dest="hash_files", help="Compute SHA-256 for each file."
    )
    parser.add_argument(
        "--type",
        dest="families",
        action="append",
        default=[],
        metavar="NAME",
        help=f"Only these kinds of file: {', '.join(sorted(FAMILIES))}.",
    )
    parser.add_argument(
        "--ext",
        dest="extensions",
        action="append",
        default=[],
        metavar="LIST",
        help="Only these extensions, e.g. --ext jpg,pdf.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the list of files with no findings; 0 for all "
        f"(default: all, or {BRIEF_LIMIT} under --brief).",
    )
    parser.add_argument(
        "--no-recurse", action="store_true", help="Do not descend into subdirectories."
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Read the directories a scan normally leaves alone, such as "
        "build output, caches and vendored copies.",
    )
    parser.add_argument(
        "--no-shell-history", action="store_true", help="Skip shell history correlation."
    )
    parser.add_argument(
        "--no-archives", action="store_true", help="Do not inherit origins from archives."
    )
    parser.add_argument("--version", action="version", version=f"filegrail {__version__}")
    return parser


def _explain_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filegrail explain",
        parents=[_common(), _profile(), _redaction()],
        description="Explain why filegrail reached a conclusion about one file.",
    )
    parser.add_argument("path", type=Path, help="The file to explain.")
    return parser


def _compare_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filegrail compare",
        parents=[_common(), _profile(), _redaction()],
        description="Compare what two files record about themselves and how each arrived.",
    )
    parser.add_argument("left", type=Path, help="The first file.")
    parser.add_argument("right", type=Path, help="The second file.")
    return parser


def _doctor_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="filegrail doctor",
        parents=[_common(), _profile()],
        description="Report which evidence sources this machine has, and how far back they reach.",
    )


def _clean_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filegrail clean",
        parents=[_common()],
        description=(
            "Write copies of files with their metadata removed. The originals are never modified."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", type=Path, help="File or directory.")
    parser.add_argument(
        "--out",
        dest="out",
        required=True,
        type=Path,
        metavar="DIR",
        help="Where to write the cleaned copies. Required, and never the source directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace a file already at the destination path.",
    )
    parser.add_argument(
        "--type",
        dest="families",
        action="append",
        default=[],
        metavar="NAME",
        help=f"Only these kinds of file: {', '.join(sorted(FAMILIES))}.",
    )
    parser.add_argument(
        "--ext",
        dest="extensions",
        action="append",
        default=[],
        metavar="LIST",
        help="Only these extensions, e.g. --ext jpg,png.",
    )
    parser.add_argument(
        "--no-recurse", action="store_true", help="Do not descend into subdirectories."
    )
    return parser


def _menu_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filegrail menu",
        parents=[_common()],
        description="Choose what to run from a list instead of remembering flags.",
    )
    parser.add_argument("path", nargs="?", default=".", type=Path, help="Where to start.")
    return parser


PARSERS = {
    "scan": build_parser,
    "explain": _explain_parser,
    "compare": _compare_parser,
    "doctor": _doctor_parser,
    "menu": _menu_parser,
    "clean": _clean_parser,
}


# --- dispatch ----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    given = sys.argv[1:] if argv is None else list(argv)

    # A bare run introduces the tool rather than scanning the current directory.
    # Starting an unasked-for scan of wherever the shell happens to be is a
    # surprise, and in a home directory an expensive one.
    if not given:
        from .about import render

        print(render(detect()))
        return 0

    if given[0] in COMMANDS:
        command, rest = given[0], given[1:]
    else:
        command, rest = "scan", given

    if command == "help":
        return _help(rest)
    return {
        "scan": _scan,
        "explain": _explain,
        "compare": _compare,
        "doctor": _doctor,
        "menu": _menu,
        "clean": _clean,
    }[command](rest)


def _help(rest: list[str]) -> int:
    """`filegrail help <command>`, and the landing screen without one."""
    if not rest:
        from .about import render

        print(render(detect()))
        return 0

    name = rest[0]
    if name not in PARSERS:
        print(f"filegrail: no such command: {name}", file=sys.stderr)
        print(f"filegrail: try one of: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2
    PARSERS[name]().print_help()
    return 0


#: How many unexplained files `--brief` lists before it says how many are left.
#: `--brief` is the flag for somebody scanning a large tree, and it is the only
#: place the default report shortens anything.
BRIEF_LIMIT = 25


def _limit(args: argparse.Namespace) -> int:
    """How much of the `no findings` list to print.

    All of it, unless asked otherwise. A report that hides part of a list it
    already has makes somebody run the tool twice for data it had the first
    time, which is the same objection that put every decoded field on screen
    by default.
    """
    if args.limit is not None:
        return int(args.limit)
    return BRIEF_LIMIT if args.brief else 0


def _missing(path: Path) -> int:
    print(f"filegrail: no such file or directory: {path}", file=sys.stderr)
    return 2


def _home(args: argparse.Namespace) -> Path | None | int:
    """Resolve `--home`, refusing a profile that is not there.

    A mistyped path would otherwise read as an answer: every source comes back
    empty, and a run that found nothing because it looked in the wrong place is
    indistinguishable from one that found nothing because there was nothing to
    find. That confusion is the exact thing `doctor` exists to prevent, so it
    is not one to introduce here.
    """
    if args.home is None:
        return None
    if not args.home.is_dir():
        return _missing(args.home)
    return Path(args.home).resolve()


def _scan(rest: list[str]) -> int:
    args = build_parser().parse_args(rest)
    root = args.path.resolve()
    if not root.exists():
        return _missing(args.path)

    home = _home(args)
    if isinstance(home, int):
        return home

    try:
        suffixes = selection(args.families, args.extensions)
    except UnknownType as unknown:
        print(f"filegrail: {unknown}", file=sys.stderr)
        return 2

    stats: dict[str, int] = {}
    missed = Unsearched()
    records = scan(
        root,
        recursive=not args.no_recurse,
        hash_files=args.hash_files,
        use_shell_history=not args.no_shell_history,
        follow_archives=not args.no_archives,
        suffixes=suffixes,
        home=home,
        stats=stats,
        skip_names=not args.no_skip,
        unsearched=missed,
    )

    if args.unknown_only:
        records = [record for record in records if not record.origins]
    if args.redact:
        records = [record.redacted() for record in records]

    base = root if root.is_dir() else root.parent
    theme = detect(colour=args.colour)

    if args.json:
        print(
            render_json(
                records,
                base,
                identify=args.identify,
                cluster=args.cluster,
                home=home,
                unsearched=missed,
            )
        )
    elif args.timeline:
        print(render_timeline(records, base, theme=theme, home=home))
    else:
        print(
            render_text(
                records,
                base,
                verbose=args.verbose,
                brief=args.brief,
                limit=_limit(args),
                stats=stats,
                theme=theme,
                filtered=describe(args.families, args.extensions),
                identify=args.identify,
                cluster=args.cluster,
                home=home,
                unsearched=missed,
            )
        )
    return 0


def _one(path: Path, home: Path | None = None) -> FileRecord | None:
    """Scan exactly one file, for the commands that take one."""
    resolved = path.resolve()
    if not resolved.is_file():
        return None
    found = scan(resolved, home=home)
    return found[0] if found else None


def _explain(rest: list[str]) -> int:
    args = _explain_parser().parse_args(rest)
    home = _home(args)
    if isinstance(home, int):
        return home

    record = _one(args.path, home)
    if record is None:
        print(f"filegrail: explain takes one file: {args.path}", file=sys.stderr)
        return 2
    if args.redact:
        record = record.redacted()

    if args.json:
        print(render_json_explain(record, home))
        return 0

    print(render_explain(record, theme=detect(colour=args.colour), home=home))
    return 0


def _compare(rest: list[str]) -> int:
    args = _compare_parser().parse_args(rest)
    home = _home(args)
    if isinstance(home, int):
        return home

    # Built one at a time rather than as a pair, so that "this one is missing"
    # is answered before the next line rather than after both are read.
    pair: list[FileRecord] = []
    for path in (args.left, args.right):
        record = _one(path, home)
        if record is None:
            print(f"filegrail: compare takes two files: {path}", file=sys.stderr)
            return 2
        pair.append(record.redacted() if args.redact else record)
    left, right = pair

    if args.json:
        print(render_json_compare(left, right, home))
        return 0

    from .compare import compare

    print(render_compare(left, right, compare(left, right), theme=detect(colour=args.colour)))
    return 0


def _clean(rest: list[str]) -> int:
    """Write cleaned copies, and say what came out and what did not."""
    args = _clean_parser().parse_args(rest)
    from .clean import clean_file
    from .report import render_clean, render_json_clean
    from .scan import iter_files

    if not args.path.exists():
        print(f"filegrail: {args.path} does not exist", file=sys.stderr)
        return 2

    source = args.path.resolve()
    destination = args.out.resolve()
    # Writing into the tree being read would make the run depend on the order
    # it happened to walk in, and a second run would clean its own output.
    if destination == source or (source.is_dir() and destination.is_relative_to(source)):
        print("filegrail: --out must be outside the directory being cleaned", file=sys.stderr)
        return 2

    try:
        suffixes = selection(args.families, args.extensions)
    except UnknownType as unknown:
        print(f"filegrail: {unknown}", file=sys.stderr)
        return 2

    destination.mkdir(parents=True, exist_ok=True)
    # The copies mirror the tree, so `below` is the directory the walk started
    # from. A single file has no tree above it and keeps its own name.
    below = source if source.is_dir() else source.parent
    results = [
        clean_file(path, destination, below=below, overwrite=args.overwrite)
        for path in iter_files(source, recursive=not args.no_recurse, suffixes=suffixes)
    ]

    if args.json:
        print(render_json_clean(results, source, destination))
        return 0
    print(render_clean(results, source, destination, theme=detect(colour=args.colour)))
    return 0


def _doctor(rest: list[str]) -> int:
    args = _doctor_parser().parse_args(rest)
    from .doctor import survey

    home = _home(args)
    if isinstance(home, int):
        return home

    found = survey(home)
    if args.json:
        print(render_json_doctor(found, home))
        return 0
    print(render_doctor(found, detect(colour=args.colour), home=home))
    return 0


def _menu(rest: list[str]) -> int:
    """Hand over to the interactive front end, if there is a terminal for it."""
    args = _menu_parser().parse_args(rest)
    from . import menu

    if not menu.available():
        print(
            "filegrail: menu needs a terminal; it cannot be piped or redirected.",
            file=sys.stderr,
        )
        return 2
    if not args.path.exists():
        return _missing(args.path)
    return menu.run(args.path, execute=main)


if __name__ == "__main__":
    raise SystemExit(main())
