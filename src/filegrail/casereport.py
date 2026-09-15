"""The investigation report: a case read in the order an analyst asks about it.

What was analysed, whether evidence was there to be found, what the records
establish together, what contradicts itself, which files to open and which
values lead somewhere else - and only after that the technical detail.

Every object starts on a line of its own with a mark and a number, so the left
edge alone says where one ends and the next begins, and no name is ever broken
inside a table column. The numbers are local to one report and are how its
sections point at each other: `#001` a file, `F01` a finding, `C01` a conflict,
`P01` a pivot.

Nothing here decides what is true. It lays out an `analysis.Case`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import __version__
from .analysis import NOTHING, REVIEW, Case, CaseFile, Finding, named, stamp
from .identify import PLACE, Identifier
from .models import ACTIVITY, CATEGORIES, METADATA, ORIGIN, EvidenceRecord, FileRecord, category
from .overview import inventory
from .report import (
    _TYPE_SECTIONS,
    _blank,
    _clusters,
    _display,
    _format,
    _identifiers,
    _relative,
    _size,
)
from .scan import Unsearched
from .theme import BOTH_WAYS, DOUBLE_RULE, FLAG, MIDDOT, RULE, Theme, detect

#: Where a property's value starts, measured from its label.
LABEL = 12

#: How many files a finding names before it says how many more there are.
SHOWN = 4

#: Findings that name files one by one, and how many of them; None is all.
_LISTED: dict[str, int | None] = {
    "generated": None,
    "conflicts": None,
    "same-second": None,
    "geo": SHOWN,
}

#: What each match basis means, for the ones a report actually uses.
MATCHES = {
    "embedded": "decoded from the file's own bytes",
    "file-attribute": "read from what the filesystem keeps for this exact file",
    "recorded-path": "an external store names this exact path",
    "sidecar": "a separate file written next to it names it",
    "name+size": "name and size agree; two files can share both, but not easily",
    "filename": "the name is all that matched",
    "container-member": "read from a member, or inherited from the container",
    "sync-root": "the file lies under a folder a sync client manages",
}

_TIME_LABELS = {ORIGIN: "When", METADATA: "Created", ACTIVITY: "When"}
_AUTHOR_FIELDS = ("creator", "author", "Author", "By-line", "dc:creator", "LastAuthor")
_ABSENT = {
    ORIGIN: "No origin trace found in the evidence sources available for this scan.",
    METADATA: "Nothing the file records about itself was read.",
    ACTIVITY: "No local activity trace found.",
}

#: Words a type name carries in capitals wherever it is printed.
_CAPITALS = {
    "urls": "URLs", "ip": "IP", "ipv6": "IPv6", "md5": "MD5", "sha1": "SHA-1",
    "sha256": "SHA-256", "sha512": "SHA-512", "nip": "NIP", "regon": "REGON",
    "sec": "SEC", "vat": "VAT", "ids": "IDs", "cves": "CVEs", "cwes": "CWEs",
    "github": "GitHub", "windows": "Windows", "sids": "SIDs", "bitcoin": "Bitcoin",
    "litecoin": "Litecoin", "dogecoin": "Dogecoin", "monero": "Monero",
    "ethereum": "Ethereum", "onion": "Onion",
}  # fmt: skip


class _Page:
    """Lines laid out to one width, with the report's three ways of placing text."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self.width = theme.width
        self.lines: list[str] = []

    def add(self, line: str = "") -> None:
        self.lines.append(line.rstrip())

    def gap(self) -> None:
        if self.lines and self.lines[-1]:
            self.lines.append("")

    def wrapped(self, text: str, indent: int, first: str | None = None) -> None:
        """`text` from column `indent`, its first line opened by `first`."""
        opening = first if first is not None else " " * indent
        for number, line in enumerate(self.theme.wrap(text, self.width - indent)):
            self.add((opening if number == 0 else " " * indent) + line)

    def head(self, mark: str, ref: str, title: str) -> int:
        """The first line of an object. Returns the column its properties use."""
        opening = f"{mark} {ref}  " if ref else f"{mark} "
        self.wrapped(title, len(opening), opening)
        return len(opening)

    def prop(self, label: str, value: str, indent: int, width: int = LABEL) -> None:
        """A label and its value; the value takes a line of its own when the
        column left for it is too narrow to read."""
        column = indent + max(width, len(label) + 2)
        if self.width - column < 16:
            self.add(" " * indent + label)
            self.wrapped(value, indent + 2)
            return
        self.wrapped(value, column, " " * indent + label.ljust(column - indent))

    def figures(self, groups: list[list[tuple[str, str]]], indent: int = 0) -> None:
        """Short labels with their numbers lined up on the right, group by group."""
        rows = [row for group in groups for row in group]
        if not rows:
            return
        left = max(len(label) for label, _ in rows) + 4
        right = max(len(value) for _, value in rows)
        for number, group in enumerate(groups):
            if number:
                self.add()
            for label, value in group:
                if indent + left + right <= self.width:
                    self.add(" " * indent + label.ljust(left) + value.rjust(right))
                else:
                    self.prop(label.strip(), value, indent)

    def section(self, name: str) -> None:
        rule = self.theme.dim(self.theme.glyph(RULE) * self.width)
        self.gap()
        self.add()
        self.add(rule)
        self.add(self.theme.bold(name))
        self.add(rule)
        self.add()

    def double(self) -> None:
        self.add(self.theme.dim(self.theme.glyph(DOUBLE_RULE) * self.width))


def render_case(
    case: Case,
    *,
    theme: Theme | None = None,
    verbose: bool = False,
    brief: bool = False,
    limit: int = 0,
    identifiers: list[Identifier] | None = None,
    content: bool = False,
    cluster: bool = False,
    home: Path | None = None,
    unsearched: Unsearched | None = None,
    filtered: str = "",
    now: datetime | None = None,
) -> str:
    """The report, top to bottom. A section with nothing in it is not printed."""
    page = _Page(theme or detect())
    files = {entry.record.path: entry for entry in case.files}
    records = [entry.record for entry in case.files]

    _masthead(page, case, home, now, brief=brief, verbose=verbose)
    _summary(page, case, records)
    _findings(page, case, files)
    if not brief:
        _coverage(page, case, unsearched)
        _conflicts(page, case, files)
    _files(page, case, verbose=verbose, limit=limit, compact=brief)
    if not brief:
        _relationships(page, case, files)
        if cluster:
            page.lines.extend(_clusters(page.theme, records, case.root))
        _pivots(page, case, files, verbose=verbose, identifiers=identifiers, content=content)
        _details(page, case, files, verbose=verbose)
        _notes(page, records)
    if filtered:
        page.gap()
        page.add(f"{'No file matched' if not records else 'Limited to'} {filtered}.")
    page.gap()
    page.double()
    page.add("END OF REPORT")
    page.double()
    return "\n".join(page.lines)


def _mark(page: _Page, entry: CaseFile) -> str:
    if entry.state == REVIEW:
        return page.theme.glyph(FLAG)
    if entry.state == NOTHING:
        return page.theme.glyph(MIDDOT)
    return " "


def _name(entry: CaseFile) -> str:
    return Path(entry.record.path).name


def _folder(case: Case, record: FileRecord) -> str | None:
    """Where under the target a file lies, or None when it lies in the target itself."""
    relative = Path(_relative(record.path, case.root))
    return str(relative) if relative.parent != Path(".") else None


def _masthead(
    page: _Page, case: Case, home: Path | None, now: datetime | None, *, brief: bool, verbose: bool
) -> None:
    dot = page.theme.glyph(MIDDOT)
    mode = f" {dot} BRIEF" if brief else f" {dot} VERBOSE" if verbose else ""
    page.add(page.theme.bold(f"FILEGRAIL {__version__}"))
    page.add(f"INVESTIGATION REPORT{mode}")
    page.double()
    page.add()
    page.prop("Target", _display(case.root), 0)
    if home:
        page.prop("Profile", f"{_display(home)} {dot} external", 0)
    moment = now or datetime.now().astimezone()
    page.prop("Generated", moment.strftime("%Y-%m-%d %H:%M %Z").strip(), 0)


def _summary(page: _Page, case: Case, records: list[FileRecord]) -> None:
    contents = inventory(records)
    flag, dot = page.theme.glyph(FLAG), page.theme.glyph(MIDDOT)
    holding = {name: sum(1 for entry in case.files if entry.found[name]) for name in CATEGORIES}
    known = sum(1 for record in records if record.evidence)
    fields = sum(len(conflict.differences) for conflict in case.conflicts)

    groups = [
        [
            ("Files", f"{len(records):,}"),
            ("File types", f"{len(contents.types):,}"),
            ("Total size", _size(contents.size)),
        ],
        [
            ("Evidence", ""),
            ("  Files with evidence", f"{known:,} / {len(records):,}"),
            ("  Origin", f"{holding[ORIGIN]:,}"),
            ("  Metadata", f"{holding[METADATA]:,}"),
            ("  Activity", f"{holding[ACTIVITY]:,}"),
        ],
    ]
    analysed = [
        ("Analysis", ""),
        (
            f"  {flag if case.conflicts else dot} Conflicts",
            f"{len(case.conflicts)} files / {fields} fields" if case.conflicts else "0",
        ),
        (f"  {dot} Relationships", f"{case.relationships:,}"),
    ]
    if case.pivots is not None:
        analysed += [
            (f"  {dot} Investigative pivots", f"{case.pivots.total:,}"),
            (f"  {dot} Shared pivots", f"{case.pivots.across:,}"),
            (f"  {dot} Cross-corpus pivots", f"{case.pivots.cross_corpus:,}"),
        ]
    groups.append(analysed)
    stores = [source for source in case.coverage if source.store]
    if stores:
        found = sum(1 for source in stores if source.state == "found")
        groups.append([("Coverage", f"{found} / {len(stores)} trace stores")])

    page.section("CASE SUMMARY")
    page.figures(groups)


def _findings(page: _Page, case: Case, files: dict[str, CaseFile]) -> None:
    if not case.findings:
        return
    page.section("KEY FINDINGS")
    for finding in case.findings:
        mark = page.theme.glyph(FLAG if finding.notable else MIDDOT)
        indent = page.head(mark, finding.ref, finding.title)
        page.add()
        facts = finding.facts
        if finding.kind == "generated":
            facts = [fact for fact in facts if fact[0] != "files"]
        labels = [label for label, _ in facts]
        labels += [label for item in finding.items for label, _ in item.facts]
        width = _width(labels)
        for label, value in facts:
            page.prop(_capital(label), value, indent, width)
        _items(page, case, finding, files, indent, width)
        if finding.kind == "no-trace":
            page.add()
            page.wrapped(
                "This does not mean the files were never downloaded or transferred.", indent
            )
            if case.begins:
                page.wrapped(f"Available trace history begins on {case.begins}.", indent)
        if finding.see:
            page.add()
            page.prop("See", finding.see, indent, width)
        page.gap()


def _items(
    page: _Page,
    case: Case,
    finding: Finding,
    files: dict[str, CaseFile],
    indent: int,
    width: int,
) -> None:
    if finding.kind == "generated":
        for item in finding.items:
            entry = files[item.path]
            opening = " " * indent + "File".ljust(width) + f"{entry.ref}  "
            page.wrapped(_name(entry), len(opening), opening)
            for label, value in item.facts:
                page.prop(_capital(label), value, indent, width)
        return
    if finding.kind not in _LISTED:
        return
    most = _LISTED[finding.kind]
    shown = finding.items if most is None else finding.items[:most]
    page.add()
    for item in shown:
        entry = files[item.path]
        opening = " " * indent + f"{entry.ref}  "
        page.wrapped(_name(entry), len(opening), opening)
        if (folder := _folder(case, entry.record)) and finding.kind != "conflicts":
            page.prop("path", folder, len(opening), width=6)
    if len(finding.items) > len(shown):
        page.add(" " * indent + f"+{len(finding.items) - len(shown)} more")


def _coverage(page: _Page, case: Case, unsearched: Unsearched | None) -> None:
    missed = [(path, "could not be read") for path in (unsearched.unreadable if unsearched else [])]
    missed += [(path, "skipped by name") for path in (unsearched.by_name if unsearched else [])]
    if not case.coverage and not missed:
        return
    page.section("EVIDENCE COVERAGE")
    for source in case.coverage:
        if source.state in ("found", "readable"):
            mark = "[+]"
        elif source.state == "partial":
            mark = "[~]"
        else:
            mark = "[-]"
        indent = page.head(mark, "", source.name)
        page.prop("Status", source.state, indent)
        if source.detail:
            page.prop("Detail", source.detail, indent)
        if source.since:
            page.prop("Since", source.since, indent)
        page.gap()
    for path, why in missed:
        indent = page.head("[-]", "", _relative(path, case.root))
        page.prop("Status", why, indent)
        page.gap()
    if case.coverage:
        page.add("NOTE")
        page.add()
        if case.begins:
            page.wrapped(f"Observable trace history begins on {case.begins}.", 4)
        page.wrapped(
            "Absence of origin evidence is not proof that a file was never downloaded, "
            "copied or otherwise transferred to this machine.",
            4,
        )


def _conflicts(page: _Page, case: Case, files: dict[str, CaseFile]) -> None:
    if not case.conflicts:
        return
    page.section("CONFLICTS")
    both = f" {page.theme.glyph(BOTH_WAYS)} "
    for conflict in case.conflicts:
        entry = files[conflict.path]
        opening = f"{page.theme.glyph(FLAG)} {conflict.ref}  {entry.ref}  "
        page.wrapped(_name(entry), len(opening), opening)
        indent = 2 + len(conflict.ref) + 2
        page.add()
        page.prop("Sources", both.join(conflict.sources), indent)
        page.prop("Fields", str(len(conflict.differences)), indent)
        for difference in conflict.differences:
            page.add()
            page.wrapped(difference.field, indent)
            width = max([len(source) for source, _ in difference.values] + [len("Delta")]) + 3
            for source, value in difference.values:
                page.prop(source or "Value", value, indent + 2, width=width)
            if difference.delta:
                page.prop("Delta", difference.delta, indent + 2, width=width)
        page.gap()


def _files(page: _Page, case: Case, *, verbose: bool, limit: int, compact: bool) -> None:
    if not case.files:
        return
    theme = page.theme
    dot = theme.glyph(MIDDOT)
    records = [entry.record for entry in case.files]
    contents = inventory(records)
    kinds = {finding.ref: finding.kind for finding in case.findings}
    notable = {finding.ref for finding in case.findings if finding.notable}
    page.section("FILES")
    page.add(
        f" {dot} ".join(
            [f"{len(records):,} files", f"{len(contents.types):,} types", _size(contents.size)]
        )
    )
    states = {entry.state for entry in case.files}
    legend = [
        (theme.glyph(FLAG), "needs review", REVIEW),
        (dot, "no evidence found", NOTHING),
        (" ", "evidence present", "evidence"),
    ]
    page.add()
    page.add("Legend")
    for mark, meaning, state in legend:
        if state in states:
            page.add(f"  {mark}  {meaning}")
    page.add()

    listed = hidden = 0
    for entry in case.files:
        if entry.state == NOTHING:
            if limit and listed >= limit:
                hidden += 1
                continue
            listed += 1
        # A block for what wants reading: a conflict, an arrival, a local trace,
        # a finding that needs a second look. Everything else is one line, which
        # still points at every finding the file is part of.
        opened = bool(entry.conflicts or entry.found[ORIGIN] or entry.found[ACTIVITY])
        opened = opened or any(ref in notable for ref in entry.findings)
        if not compact and (verbose or opened):
            _file_block(page, case, entry, kinds)
        else:
            _file_line(page, case, entry, kinds)
    if hidden:
        page.gap()
        page.wrapped(f"+{hidden} more files with no evidence found; --limit 0 lists them all.", 2)


def _references(entry: CaseFile, kinds: dict[str, str]) -> list[tuple[str, str]]:
    findings = [ref for ref in entry.findings if kinds[ref] != "no-trace"]
    said = []
    if findings:
        said.append(("findings", " · ".join(findings)))
    if entry.conflicts:
        said.append(("conflicts", " · ".join(entry.conflicts)))
    if entry.pivots:
        said.append(("pivots", " · ".join(entry.pivots)))
    return said


def _file_block(page: _Page, case: Case, entry: CaseFile, kinds: dict[str, str]) -> None:
    page.gap()
    indent = page.head(_mark(page, entry), entry.ref, _name(entry))
    if folder := _folder(case, entry.record):
        page.prop("path", folder, indent)
    page.prop("type", _format(entry.record.path), indent)
    page.prop("size", _size(entry.record.size), indent)
    page.add()
    if entry.state == NOTHING:
        page.prop("evidence", "none found", indent)
    else:
        blank = _blank(page.theme)
        for name in CATEGORIES:
            page.prop(name, " · ".join(entry.found[name]) or blank, indent)
    references = _references(entry, kinds)
    if references:
        page.add()
        for label, value in references:
            page.prop(label, value, indent)
    page.gap()


def _file_line(page: _Page, case: Case, entry: CaseFile, kinds: dict[str, str]) -> None:
    dot = page.theme.glyph(MIDDOT)
    found = [name for category_ in CATEGORIES for name in entry.found[category_]]
    facts = [_format(entry.record.path), _size(entry.record.size)]
    facts.append(" · ".join(found) if found else "no evidence found")
    facts += [value for label, value in _references(entry, kinds) if label != "pivots"]
    if folder := _folder(case, entry.record):
        facts.append(f"in {Path(folder).parent}")
    opening = f"{_mark(page, entry)} {entry.ref}  "
    said = f" {dot} ".join(facts)
    line = f"{opening}{_name(entry)}  {said}"
    if len(line) <= page.width:
        page.add(line)
        return
    page.wrapped(_name(entry), len(opening), opening)
    page.wrapped(said, len(opening))


def _relationships(page: _Page, case: Case, files: dict[str, CaseFile]) -> None:
    linked = [entry for entry in case.files if entry.record.links]
    if not linked:
        return
    page.section("RELATIONSHIPS")
    for entry in linked:
        indent = page.head(" ", entry.ref, _name(entry))
        for link in entry.record.links:
            others = [files[path] for path in link.others if path in files]
            said = " · ".join(f"{other.ref} {_name(other)}" for other in others)
            page.prop(link.kind, said or f"{link.count} files", indent, width=16)
        page.gap()


def _pivots(
    page: _Page,
    case: Case,
    files: dict[str, CaseFile],
    *,
    verbose: bool,
    identifiers: list[Identifier] | None,
    content: bool,
) -> None:
    pivots = case.pivots
    if pivots is None or not pivots.total:
        return
    page.section("INVESTIGATIVE PIVOTS")
    page.add("SUMMARY")
    page.add()
    page.figures([[(_type_name(kind), f"{count:,}") for kind, count in pivots.by_type]], indent=2)

    if pivots.shared:
        page.gap()
        page.add("CROSS-FILE PIVOTS")
        page.add()
        for ref, entry in pivots.shared:
            indent = page.head(" ", ref, entry.type.upper())
            page.prop("Value", entry.value, indent)
            page.prop("Files", f"{entry.files:,}", indent)
            sources = dict.fromkeys(
                place.split(PLACE)[1] for place in entry.where if PLACE in place
            )
            page.prop("Sources", " · ".join(sources), indent)
            page.gap()

    if pivots.dense:
        page.gap()
        page.add("HIGH-DENSITY FILES")
        page.add()
        for dense in pivots.dense:
            held = files.get(dense.path)
            indent = page.head(" ", held.ref if held else "", Path(dense.path).name)
            page.prop("Pivot locations", f"{dense.places:,}", indent, width=18)
            page.add()
            for kind, count in dense.by_type:
                page.prop(_type_name(kind), f"{count:,}", indent, width=18)
            page.gap()

    if verbose and identifiers:
        page.lines.extend(_identifiers(page.theme, identifiers, content=content))
    else:
        page.gap()
        page.wrapped("Full pivot lists: add -v, or use --json.", 0)


def _details(page: _Page, case: Case, files: dict[str, CaseFile], *, verbose: bool) -> None:
    # What wants a second look, and every file whose arrival or handling here
    # was recorded: where a file came from is what the report is for.
    chosen = [
        entry
        for entry in case.files
        if entry.state == REVIEW
        or entry.found[ORIGIN]
        or entry.found[ACTIVITY]
        or (verbose and entry.state != NOTHING)
    ]
    if not chosen:
        return
    findings = {finding.ref: finding for finding in case.findings}
    conflicts = {conflict.ref: conflict for conflict in case.conflicts}
    page.section("FILE DETAIL")
    for entry in chosen:
        record = entry.record
        page.gap()
        indent = page.head(_mark(page, entry), entry.ref, _name(entry))
        page.prop("Type", _format(record.path), indent)
        page.prop("Size", _size(record.size), indent)
        if folder := _folder(case, record):
            page.prop("Path", folder, indent)

        for name in CATEGORIES:
            held = [found for found in record.evidence if category(found) == name]
            page.add()
            page.add(" " * 4 + name.upper())
            if not held:
                page.wrapped(_ABSENT[name], 8)
                continue
            for found in held:
                page.add(" " * 6 + named(found))
                facts = _facts(found, name, verbose=verbose)
                width = _width([label for label, _ in facts])
                for label, value in facts:
                    page.prop(label, value, 8, width)

        notes = []
        for ref in entry.conflicts:
            conflict = conflicts[ref]
            fields = " · ".join(difference.field for difference in conflict.differences)
            notes.append(
                (
                    page.theme.glyph(FLAG),
                    f"{' and '.join(conflict.sources)} disagree on {fields} ({ref})",
                )
            )
        for ref in entry.findings:
            finding = findings[ref]
            if finding.kind in ("conflicts", "no-trace"):
                continue
            others = [files[item.path] for item in finding.items if item.path != record.path]
            said = f"{finding.title} ({ref})"
            if others and len(others) <= SHOWN:
                said += ": " + " · ".join(f"{other.ref} {_name(other)}" for other in others)
            elif others:
                said += f": with {len(others)} other files"
            notes.append((page.theme.glyph(MIDDOT), said))
        if notes:
            page.add()
            page.add("    ANALYTICAL NOTES")
            for mark, said in notes:
                page.wrapped(said, 8, f"      {mark} ")
        page.gap()


def _facts(found: EvidenceRecord, name: str, *, verbose: bool) -> list[tuple[str, str]]:
    said: list[tuple[str, str]] = []
    if found.tool:
        said.append(("Software" if name == METADATA else "Tool", found.tool))
    for field_name in _AUTHOR_FIELDS:
        if who := found.fields.get(field_name):
            said.append(("Author", str(who)))
            break
    if found.url:
        said.append(("URL", found.url))
    if found.referrer:
        said.append(("Referrer", found.referrer))
    if found.command:
        said.append(("Command", found.command))
    if found.at:
        timed = "When" if found.block == "xmp-history" else _TIME_LABELS[name]
        said.append((timed, stamp(found.at)))
    if found.geo:
        said.append(("Location", found.geo))
    if found.location:
        said.append(("Place", found.location))
    author = next((value for label, value in said if label == "Author"), None)
    if found.note and found.note != f"author {author}":
        said.append(("Note", found.note))
    said.append(("Match", found.matched_by))
    if verbose:
        said += [(key, str(value)) for key, value in found.fields.items() if value]
    return said


def _notes(page: _Page, records: list[FileRecord]) -> None:
    dot = page.theme.glyph(MIDDOT)
    page.section("REPORT NOTES")
    page.add("Evidence categories")
    page.prop("Origin", "How a file reached the examined environment.", 2)
    page.prop("Metadata", "What the file records about itself.", 2)
    page.prop("Activity", "What happened to the file locally.", 2)

    used = {found.matched_by for record in records for found in record.evidence}
    if used:
        page.add()
        page.add("Match basis")
        for basis, meaning in MATCHES.items():
            if basis in used:
                page.prop(basis, meaning, 2, width=18)

    page.add()
    page.add("Interpretation")
    for said in (
        "No origin evidence is not proof that a file was never downloaded or transferred.",
        "Recorded authors, organizations, devices and identifiers are values the files "
        "carry, not verified identity.",
    ):
        page.wrapped(said, 4, f"  {dot} ")


def _width(labels: list[str]) -> int:
    """One label column for a whole object, so its values line up."""
    return min(24, max([LABEL, *(len(label) + 2 for label in labels)]))


def _capital(label: str) -> str:
    return label[:1].upper() + label[1:]


def _type_name(kind: str) -> str:
    words = _TYPE_SECTIONS.get(kind, kind).split()
    shown = [_CAPITALS.get(word, word) for word in words]
    return _capital(" ".join(shown))
