"""`docs/FORMATS.md` is held against the readers, so it cannot quietly go stale.

A list of formats in prose is the one category of documentation guaranteed to rot:
`CONTRIBUTING.md` asks for new readers, every new reader is a line somebody has
to remember to add, and nothing notices when they do not. Two years of that and
the file is a liability - it reads like a promise and is not one.

So it is parsed. Every extension a reader declares has to appear in the table,
and every extension in the table has to be one a reader actually reads. Either
direction failing is a red test rather than a wrong document.

This checks what `filegrail` reads out of the *files it is pointed at*. What it
reads from the machine - browser history, quarantine records, shell history,
Recent shortcuts - is a different axis, and `filegrail doctor` reports it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from filegrail.models import BLOCK_LABELS
from filegrail.sources import mail
from filegrail.sources.archives import ARCHIVE_SUFFIXES
from filegrail.sources.c2pa import SUPPORTED_SUFFIXES as C2PA_SUFFIXES
from filegrail.sources.content import SUFFIXES as CONTENT_SUFFIXES
from filegrail.sources.embedded import SUFFIXES as EMBEDDED_SUFFIXES

FORMATS = Path(__file__).resolve().parent.parent / "docs" / "FORMATS.md"

#: The header rows that mark the two tables this test reads. Anything else in
#: the file is prose and is left alone.
METADATA_HEADER = ("block", "extensions", "what comes out")
CROSS_HEADER = ("block", "where it is found", "what comes out")
MAIL_HEADER = ("extension", "what comes out")
ARCHIVE_HEADER = ("extensions", "what filegrail does with them")
CONTENT_HEADER = ("extensions", "what is read")

_EXTENSION = re.compile(r"`(\.[a-z0-9]+)`")
_NAME = re.compile(r"`([a-z0-9][a-z0-9-]*)`")


def _rows(header: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Every row under every table whose header row matches."""
    found: list[tuple[str, ...]] = []
    inside = False
    for line in FORMATS.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            inside = False
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if tuple(cell.lower() for cell in cells) == header:
            inside = True
            continue
        if inside and set("".join(cells)) <= set(":- "):
            continue  # the separator under the header
        if inside:
            found.append(cells)
    return found


def _documented(header: tuple[str, ...], column: int) -> set[str]:
    return {
        extension
        for row in _rows(header)
        if len(row) > column
        for extension in _EXTENSION.findall(row[column])
    }


def _documented_formats() -> set[str]:
    """Every extension the document claims, wherever it claims it.

    Three tables rather than one, because a mail message and a PNG do not
    answer the same question and forcing them into one table made the document
    worse to read. The test reads the document as written rather than the other
    way round.
    """
    return _documented(METADATA_HEADER, 1) | _documented(MAIL_HEADER, 0)


def _readable() -> set[str]:
    """Every extension something will try to decode metadata out of."""
    return EMBEDDED_SUFFIXES | C2PA_SUFFIXES | mail.SUFFIXES | mail.OUTLOOK_SUFFIXES


def _declared_blocks() -> set[str]:
    """Every block name the source tree actually passes to an `EvidenceRecord`."""
    found = set(BLOCK_LABELS)
    for path in (Path(__file__).resolve().parent.parent / "src" / "filegrail").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg == "block" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        found.add(keyword.value.value)
    return found


# --- the tables are there at all ---------------------------------------------


def test_the_metadata_table_is_found():
    """A header nobody can parse would make every check below vacuous."""
    assert _rows(METADATA_HEADER), f"no table headed {METADATA_HEADER} in {FORMATS.name}"


def test_the_archive_table_is_found():
    assert _rows(ARCHIVE_HEADER), f"no table headed {ARCHIVE_HEADER} in {FORMATS.name}"


def test_the_mail_table_is_found():
    assert _rows(MAIL_HEADER), f"no table headed {MAIL_HEADER} in {FORMATS.name}"


def test_the_cross_format_table_is_found():
    assert _rows(CROSS_HEADER), f"no table headed {CROSS_HEADER} in {FORMATS.name}"


# --- and they say what the code does -----------------------------------------


def test_every_format_a_reader_declares_is_documented():
    documented = _documented_formats()

    missing = _readable() - documented
    assert not missing, f"read but undocumented: {sorted(missing)}"


def test_nothing_is_documented_that_no_reader_reads():
    """A promise the tool does not keep is worse than a gap in the table."""
    documented = _documented_formats()

    invented = documented - _readable()
    assert not invented, f"documented but unread: {sorted(invented)}"


def test_every_archive_format_is_documented():
    documented = _documented(ARCHIVE_HEADER, 0)

    assert documented == set(ARCHIVE_SUFFIXES), sorted(documented ^ set(ARCHIVE_SUFFIXES))


def test_every_block_the_table_names_is_one_the_code_declares():
    """The first column is a `--json` value, not a label invented here."""
    declared = _declared_blocks()

    named = {
        name
        for header in (METADATA_HEADER, CROSS_HEADER)
        for row in _rows(header)
        for name in _NAME.findall(row[0])
    }
    assert named, "the table names no blocks at all"
    assert named <= declared, sorted(named - declared)


# --- the other axis -----------------------------------------------------------
#
# `--content` reads what a document *says*, which is neither what it records
# about itself nor what the machine remembers about it. A third axis and a third
# table, held the same way in both directions - the document exists precisely so
# that a reader added later cannot quietly go undocumented.


def test_every_format_content_reads_is_documented():
    documented = _documented(CONTENT_HEADER, 0)

    missing = CONTENT_SUFFIXES - documented
    assert not missing, f"read as text but undocumented: {sorted(missing)}"


def test_nothing_is_documented_as_text_that_is_not_read_as_text():
    documented = _documented(CONTENT_HEADER, 0)

    invented = documented - CONTENT_SUFFIXES
    assert not invented, f"documented as text but unread: {sorted(invented)}"


# --- the numbers in the prose -------------------------------------------------
#
# The tables above cannot drift, because they are parsed. The counts written
# beside them in English can: add a reader and the tables are forced to follow,
# while `68 file extensions` keeps saying sixty-eight for ever. So they are read
# out of the documents and compared too.

README = Path(__file__).resolve().parent.parent / "README.md"


def _counted(document: Path, phrase: str) -> int:
    found = re.search(rf"(\d+)\s+(?:\*\*)?{phrase}", document.read_text(encoding="utf-8"))
    assert found is not None, f"{document.name} no longer states the count for {phrase!r}"
    return int(found.group(1))


def test_the_format_reference_agrees_with_the_readers_about_how_many_there_are():
    assert _counted(FORMATS, r"file extensions\*\*") == len(_readable())


def _backticked(document: Path, heading: str, stop: str) -> set[str]:
    """Every extension in the tables under one heading of a document."""
    text = document.read_text(encoding="utf-8")
    section = text[text.index(heading) : text.index(stop, text.index(heading))]
    return set(_EXTENSION.findall(section))


def test_the_readme_lists_exactly_what_content_reads():
    """A count in prose can be checked; a list of extensions can be checked
    against the reader itself, which is the stronger claim and the one the
    readme actually makes."""
    listed = _backticked(README, "### Document content", "## Analysis")

    assert listed == CONTENT_SUFFIXES, sorted(listed ^ CONTENT_SUFFIXES)


def test_every_place_the_readme_promises_is_one_the_reader_writes():
    """The table says where in a document a value will be reported from. A
    place named there that nothing ever emits is a promise about output, which
    is worse than a wrong extension: a reader will look for it and not find it.
    """
    import filegrail.sources.content as reader

    # Every place the reader can write: the ones its table of package members
    # names, and the ones it builds itself. Read out of the module rather than
    # kept here, so a new place cannot be documented before it exists.
    source = Path(reader.__file__).read_text(encoding="utf-8")
    built = {
        re.sub(r"\{[^}]*\}", "{}", place)
        for place in re.findall(r'Passage\(\s*f?"([^"]+)"', source)
    }
    written = {name for _, name in reader._PARTS} | built
    promised = set()
    for row in _readme_rows(README, "### Document content"):
        promised |= {re.sub(r"\d+", "{}", place) for place in _EXTENSION_FREE.findall(row[2])}

    assert promised, "the table no longer says where a value is reported from"
    assert promised <= written, sorted(promised - written)


def _readme_rows(document: Path, heading: str) -> list[list[str]]:
    """The cells of the table under one heading of a document."""
    text = document.read_text(encoding="utf-8")
    section = text[text.index(heading) :]
    rows = []
    for line in section.splitlines()[1:]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if set("".join(cells)) <= set(":- "):
            continue
        rows.append(cells)
    return rows


#: A backticked value that is not a file extension - the place names.
_EXTENSION_FREE = re.compile(r"`([^`.]+)`")


def test_the_readme_metadata_table_names_the_extensions_its_readers_declare():
    """The largest table on the page, and the one a reader arrives to check.

    Held row by row against the reader each row names, both ways: an extension
    listed under `EXIF` that the EXIF reader does not declare is a promise the
    tool does not keep, and one it declares but the row omits is a capability
    nobody can find.
    """
    from filegrail.sources.c2pa import SUPPORTED_SUFFIXES as C2PA
    from filegrail.sources.embedded import (
        containers,
        documents,
        exif,
        id3,
        isobmff,
        matroska,
        ole,
        png,
        riff,
        vorbis,
    )

    owners = {
        "EXIF": exif.SUFFIXES,
        "PNG text": png.SUFFIXES,
        "ISO BMFF": isobmff.SUFFIXES,
        "Matroska": matroska.SUFFIXES,
        "RIFF/BWF": riff.SUFFIXES,
        "Vorbis comments": vorbis.SUFFIXES,
        "ID3": id3.SUFFIXES,
        "PDF Info": documents.PDF_SUFFIXES,
        "OOXML properties": documents.OOXML_SUFFIXES,
        "OLE properties": ole.SUFFIXES,
        "OpenDocument metadata": containers.ODF_SUFFIXES,
        "EPUB package": containers.EPUB_SUFFIXES,
        "RTF metadata": containers.RTF_SUFFIXES,
        "SVG metadata": containers.SVG_SUFFIXES,
        "Jupyter notebook": containers.NOTEBOOK_SUFFIXES,
        "C2PA": C2PA,
    }

    rows = {
        row[0].strip("*"): set(_EXTENSION.findall(row[1]))
        for row in _readme_rows(README, "### Embedded metadata")[1:]
    }
    assert set(rows) == set(owners), sorted(set(rows) ^ set(owners))
    for block, listed in rows.items():
        assert listed == set(owners[block]), (block, sorted(listed ^ set(owners[block])))


def test_the_readme_lists_exactly_what_clean_can_strip():
    from filegrail.clean import _STRIPPERS

    listed = _backticked(README, "### Cleanable formats", "Clean one file")

    assert listed == set(_STRIPPERS), sorted(listed ^ set(_STRIPPERS))


def test_the_badge_agrees_too():
    """It is the first number a reader sees, and the easiest to forget."""
    badge = re.search(r"badge/formats-(\d+)", README.read_text(encoding="utf-8"))
    assert badge is not None, "the readme no longer carries a format badge"
    assert int(badge.group(1)) == len(_readable())
