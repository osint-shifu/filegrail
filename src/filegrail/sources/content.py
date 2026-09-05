"""What a file says, as distinct from what it records about itself.

Every other reader here answers *where did this come from*. This one answers
nothing on its own: it hands back the readable text of a document so that the
identifier detectors can be pointed at it, and the text is not a claim about
provenance. A body is not evidence of arrival, and turning one into an `Origin`
would put a paragraph beside a download record as though the two said the same
kind of thing.

What makes it worth reading here rather than with `grep` is what sits beside
it. An address in a document is a lead. An address in a document that the
file's *arrival* record also names is a link, and only something that already
read the arrival record can see that.

**No new dependencies, and that is not a compromise.** The formats where a text
search fails hardest - a `.docx`, an `.odt`, a slide deck - are zip archives of
XML, and this package already opens them for their properties, with a bounded
member reader written for exactly this hazard. The body is a different member
of the same archive.

Deliberately not read, with reasons:

* **PDF** - the only format here that genuinely needs work rather than
  plumbing. Pulling the string literals out of a content stream takes an
  afternoon and produces readable text for perhaps half of real documents;
  for the other half it produces mush that cannot be told apart from data.
  In a tool that reports evidence, a confident wrong answer is worse than an
  absent one, and `_origin()` in the readers beside this one already refuses
  to guess for the same reason.
* **Source code** - a checkout is thousands of files whose identifiers are
  dependency hosts and licence URLs. `SKIP_DIRECTORIES` keeps a scan out of
  `node_modules` on the same principle.
* **RTF** - text under a layer of control words and hex escapes, which would
  need a parser to read honestly and yields noise without one.
"""

from __future__ import annotations

import codecs
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from .embedded.containers import EPUB_SUFFIXES, ODF_SUFFIXES, SVG_SUFFIXES
from .embedded.documents import OOXML_SUFFIXES
from .embedded.parts import read_part
from .mail import OUTLOOK_SUFFIXES
from .mail import SUFFIXES as MAIL_SUFFIXES

#: The most text taken from one file. Identifiers repeat; a document long
#: enough to exhaust this has said what it is going to say, and the point of
#: the number is that there be one - the same argument `parts.py` makes.
MAX_TEXT_BYTES = 1024 * 1024

#: How many members of one package are read. A deck can hold a thousand slides
#: and each one costs an open, a bounded read and a parse.
MAX_PARTS = 64

#: Files that already are text. Data formats are included - a JSON export from
#: an application is exactly the sort of file an examiner is handed - and
#: source code is not, for the reason in the module docstring.
PLAIN_SUFFIXES = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".rst",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".ndjson",
    ".jsonl",
    ".ipynb",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".vcf",
    ".ics",
}

#: Markup, read for its text and its links rather than its tags.
MARKUP_SUFFIXES = {".html", ".htm", ".xhtml", ".xml"} | SVG_SUFFIXES

#: Packages whose body lives in a named member beside the properties.
PACKAGE_SUFFIXES = OOXML_SUFFIXES | ODF_SUFFIXES | EPUB_SUFFIXES

SUFFIXES = PLAIN_SUFFIXES | MARKUP_SUFFIXES | PACKAGE_SUFFIXES | MAIL_SUFFIXES | OUTLOOK_SUFFIXES

#: Which members of a package hold what the document says. Word keeps the notes
#: and comments outside the main part, a deck keeps one member per slide, and a
#: spreadsheet keeps every string it shows in one table - so the body of a file
#: is several members and never just one.
_BODY_PARTS = re.compile(
    r"(?:^word/(?:document|footnotes|endnotes|comments)\d*\.xml$)"
    r"|(?:^ppt/(?:slides|notesSlides)/[^/]+\.xml$)"
    r"|(?:^xl/(?:sharedStrings\.xml|worksheets/[^/]+\.xml)$)"
    r"|(?:^content\.xml$)|(?:^styles\.xml$)"
    r"|(?:\.x?html?$)"
)

#: Elements whose text is not what the document says. A stylesheet is full of
#: things that match - a colour is a short hex digest - and a script carries
#: hosts a bundler wrote rather than hosts anybody typed.
_SILENT = {"script", "style"}

#: Attributes that carry an address a person put there. `xmlns` is excluded on
#: purpose: every XML document in the world names `w3.org`, and reporting that
#: as something a file said would be the loudest false positive available.
_LINK_ATTRIBUTES = {"href", "src", "cite", "action", "data", "longdesc", "poster"}

#: A body stream in a compound message, unicode first. Same shape as the
#: transport headers `mail.py` reads out of the same container.
_OUTLOOK_BODY = ("__substg1.0_1000001F", "__substg1.0_1000001E")

#: What a document raises when it is not the document its extension claims.
#: The list the readers beside this one keep, for the same reason - and with
#: the two `zipfile` contributes that are neither `OSError` nor `ValueError`.
_UNREADABLE = (
    OSError,
    ValueError,
    LookupError,
    zipfile.BadZipFile,
    NotImplementedError,
)


def read_text(path: Path) -> str | None:
    """The readable text of `path`, or None where there is none to read.

    None is the answer for a format nothing here handles, for a file that is
    not the format its name claims, and for a document that turns out to hold
    no text - all three of which are ordinary, and none of which is an error.
    """
    suffix = path.suffix.lower()
    if suffix not in SUFFIXES:
        return None

    try:
        if suffix in PLAIN_SUFFIXES:
            text = _decode(_head(path))
        elif suffix in MARKUP_SUFFIXES:
            text = _stripped(_decode(_head(path)))
        elif suffix in PACKAGE_SUFFIXES:
            text = _package(path)
        elif suffix in MAIL_SUFFIXES:
            text = _message(path)
        else:
            text = _outlook(path)
    except _UNREADABLE:
        return None

    return text[:MAX_TEXT_BYTES] if text.strip() else None


def _head(path: Path) -> bytes:
    """The front of the file, and one byte more than will be kept.

    Read rather than mapped: the bound here is the point, and a file larger
    than it is the ordinary case rather than the exception - a log grows
    without anybody deciding to make it big.
    """
    with path.open("rb") as handle:
        # Two bytes per character in the worst case this decodes, so the byte
        # budget is doubled to fill the character budget.
        return handle.read(MAX_TEXT_BYTES * 2 + 1)


def _decode(raw: bytes) -> str:
    """Bytes as text, without a character-set detector.

    Everything read from this afterwards is ASCII - an address, a host, a
    dotted quad, a hex digest, a coordinate - so a mis-decoded accent costs a
    character nothing was looking for, and guessing properly would cost a
    dependency this package does not have. UTF-16 is the exception worth
    handling: a Windows editor marks it, and reading it as UTF-8 puts a NUL
    between every letter, which breaks every pattern rather than one accent.
    """
    for mark, encoding in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if raw.startswith(mark):
            return raw.decode(encoding, "replace")
    return raw.decode("utf-8", "replace")


class _Text(HTMLParser):
    """Markup reduced to what a person would have read, plus the links.

    A parser rather than a regular expression over angle brackets, because the
    two things that have to be got right - which elements to stay out of, and
    which attributes carry an address somebody typed - are both about
    structure. `HTMLParser` is in the standard library, is written in Python,
    and expands no entities of its own, so it adds no new way for a file to
    cost more than it is worth.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._silent = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SILENT:
            self._silent += 1
        for name, value in attrs:
            if value and name.lower() in _LINK_ATTRIBUTES:
                self.parts.append(value)

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag: str) -> None:
        if tag in _SILENT and self._silent:
            self._silent -= 1

    def handle_data(self, data: str) -> None:
        if not self._silent:
            self.parts.append(data)


def _stripped(markup: str) -> str:
    parser = _Text()
    parser.feed(markup)
    parser.close()
    return " ".join(parser.parts)


def _package(path: Path) -> str:
    """The body members of a zip-based document, in the order it stores them.

    Read through `read_part`, so one member cannot cost more than the bound it
    already sets, and capped at `MAX_PARTS` members so a package cannot cost
    more by holding many small ones instead of one large one.
    """
    collected: list[str] = []
    size = 0
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if _BODY_PARTS.search(name)]
        for name in members[:MAX_PARTS]:
            payload = read_part(archive, name)
            if payload is None:
                continue
            collected.append(_stripped(_decode(payload)))
            size += len(collected[-1])
            if size >= MAX_TEXT_BYTES:
                break
    return " ".join(collected)


def _message(path: Path) -> str:
    """A message's body, and none of its headers.

    The headers are already read as evidence of delivery, so taking them again
    here would count one address twice and file the second copy under the wrong
    corpus. The body is decoded first: quoted-printable and base64 both hide an
    address from anything reading the bytes as they lie.
    """
    from email import policy
    from email.parser import BytesParser

    with path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parsebytes(handle.read(MAX_TEXT_BYTES * 2))

    collected: list[str] = []
    for part in message.walk():
        if part.get_content_maintype() != "text":
            continue
        try:
            payload = part.get_content()
        except (LookupError, ValueError):
            continue  # an encoding this interpreter has no codec for
        if isinstance(payload, str):
            collected.append(
                _stripped(payload) if part.get_content_subtype() == "html" else payload
            )
    return "\n".join(collected)


def _outlook(path: Path) -> str:
    """The body stream of a compound message, unicode spelling first."""
    from .embedded.ole import read_streams

    streams = read_streams(path, list(_OUTLOOK_BODY))
    unicode_body = streams.get(_OUTLOOK_BODY[0])
    if unicode_body is not None:
        return unicode_body.decode("utf-16-le", "replace").rstrip("\x00")
    ansi_body = streams.get(_OUTLOOK_BODY[1])
    return ansi_body.decode("utf-8", "replace").rstrip("\x00") if ansi_body is not None else ""
