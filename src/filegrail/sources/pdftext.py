"""The text a PDF shows, page by page, for the detectors to be pointed at.

A PDF does not store its text. It stores instructions for drawing glyphs, and
the bytes those instructions carry are indices into whatever encoding the font
happens to use. Two documents that look identical can hold entirely different
bytes, which is why pulling the string literals out and hoping is not a reader
but a guess - and a guess here produces an address nobody ever wrote.

So every run of text is decoded through the font that draws it, and a font
whose mapping cannot be established is not decoded at all. What a reader does
with the result is find identifiers in it, so the failure that matters is not
unreadable prose: it is a plausible address assembled out of the wrong glyphs.
Dropping a run costs a lead. Inventing one costs the investigation.

Three mappings are established, in this order:

* `/ToUnicode`, a CMap the writer supplies precisely so that the text can be
  recovered. Where it exists it is the answer and nothing else is consulted.
* `/Encoding`, either one of the named encodings or a base with `/Differences`
  naming glyphs one at a time. Glyph names are resolved through a table of the
  Latin names and the `uniXXXX` form.
* Nothing, for a font that states neither. Then only the printable ASCII range
  is taken and every other byte is dropped, because a subset font's own
  encoding agrees with ASCII for those positions far more often than not, and
  the values this tool looks for are written in them.

What is refused: an encrypted document, a stream under a filter this module
does not undo, a font whose glyphs resolve to nothing, and a file whose page
tree cannot be walked. A page number is a fact a PDF really does record - it
is structure, not pagination invented at render time - so it is reported, and
a document whose pages cannot be ordered is not reported on at all.
"""

from __future__ import annotations

import re
import unicodedata
import zlib
from collections.abc import Iterator
from typing import NamedTuple


class Font(NamedTuple):
    """What a font's bytes mean, and how many of them make one character.

    The width is not decoration. A composite font is shown two bytes at a
    time, and reading those bytes singly looks up two codes that are not the
    one drawn - which does not fail, it returns whatever those positions hold.
    A glyph index above 255 is ordinary in any subset font, so this is the
    difference between reading a document and reporting letters from the
    wrong places in it.
    """

    width: int
    table: dict[int, str]


#: The largest document this reader opens. It is read whole - see `_whole` in
#: `content.py` - so the bound is on the file rather than on a prefix of it.
MAX_FILE_BYTES = 64 * 1024 * 1024

#: How many pages are read from one document. A report names the page it found
#: a value on, so the number has to mean something; past this many the reader
#: stops rather than paginating for hours.
MAX_PAGES = 512

#: How much text is taken before the reader stops walking pages. The caller
#: bounds the result too - this stops the work, not just the output.
MAX_TEXT_BYTES = 1024 * 1024

#: How many objects one document may hold. A malformed or hostile file can
#: name millions; the table is built once and this is what it costs at most.
MAX_OBJECTS = 200_000

#: A kerning number in a `TJ` array moves the pen without drawing. Past this
#: much - a fifth of an em - the gap is a space the writer chose not to draw,
#: and joining the pieces without one glues two words into an address that was
#: never in the document.
_SPACE_KERN = -200

_OBJECT = re.compile(rb"(\d+)\s+\d+\s+obj\b(.*?)\bendobj", re.S)
_ROOT = re.compile(rb"/Root\s+(\d+)\s+\d+\s+R")
_REFERENCE = re.compile(rb"(\d+)\s+\d+\s+R")
_STREAM = re.compile(rb"stream\r?\n", re.S)
_TYPE_PAGE = re.compile(rb"/Type\s*/Page(?![sA-Za-z])")


def read_pages(raw: bytes) -> list[tuple[int, str]]:
    """Every page's text, numbered the way the document numbers its pages."""
    if b"/Encrypt" in raw[-2048:] or re.search(rb"/Encrypt\s+\d+\s+\d+\s+R", raw) is not None:
        return []  # the strings are ciphertext; decoding them would be invention
    objects = _objects(raw)
    if not objects:
        return []

    pages = list(_pages(raw, objects))
    if not pages:
        return []

    found: list[tuple[int, str]] = []
    budget = MAX_TEXT_BYTES
    for number, page in enumerate(pages[:MAX_PAGES], 1):
        fonts = _fonts(page, objects)
        content = b"".join(_contents(page, objects))
        if not content:
            continue
        text = _show(content, fonts)
        if not text.strip():
            continue
        found.append((number, text))
        budget -= len(text)
        if budget <= 0:
            break
    return found


# --- the objects ---------------------------------------------------------------


def _objects(raw: bytes) -> dict[int, bytes]:
    """Every object body, including the ones packed into an object stream.

    Read by pattern rather than through the cross-reference table on purpose:
    a table that disagrees with the file is ordinary in a document something
    has appended to, and the bodies are what is wanted either way.
    """
    found: dict[int, bytes] = {}
    for match in _OBJECT.finditer(raw):
        if len(found) >= MAX_OBJECTS:
            break
        found.setdefault(int(match.group(1)), match.group(2))
    for body in list(found.values()):
        if b"/ObjStm" in body:
            found.update(_packed(body, found))
    return found


def _packed(body: bytes, objects: dict[int, bytes]) -> dict[int, bytes]:
    """The objects inside one object stream: a header of pairs, then the bodies."""
    data = _stream(body, objects)
    if data is None:
        return {}
    count = _integer(body, b"/N")
    first = _integer(body, b"/First")
    if count is None or first is None or first > len(data):
        return {}
    numbers = data[:first].split()
    found: dict[int, bytes] = {}
    for index in range(min(count, len(numbers) // 2)):
        try:
            number = int(numbers[index * 2])
            start = first + int(numbers[index * 2 + 1])
        except ValueError:
            break
        end = len(data)
        if index * 2 + 3 < len(numbers):
            try:
                end = first + int(numbers[index * 2 + 3])
            except ValueError:
                pass
        found[number] = data[start:end]
    return found


def _integer(body: bytes, key: bytes) -> int | None:
    match = re.search(re.escape(key) + rb"\s+(\d+)", body)
    return int(match.group(1)) if match else None


def _stream(body: bytes, objects: dict[int, bytes]) -> bytes | None:
    """An object's stream, undone where every filter on it is one done here."""
    opening = _STREAM.search(body)
    if opening is None:
        return None
    end = body.rfind(b"endstream")
    data = body[opening.end() : end if end != -1 else len(body)]
    header = body[: opening.start()]

    filters = re.findall(rb"/([A-Za-z0-9]+Decode)", header)
    for name in filters:
        if name == b"FlateDecode":
            try:
                data = zlib.decompress(data)
            except zlib.error:
                try:  # a writer that miscounted the length leaves a short tail
                    data = zlib.decompressobj().decompress(data)
                except zlib.error:
                    return None
        else:
            return None  # an image codec, or a filter nothing here undoes
    if filters and (predictor := _integer(header, b"/Predictor")) and predictor >= 10:
        data = _unpredict(data, _integer(header, b"/Columns") or 1)
    return data


def _unpredict(data: bytes, columns: int) -> bytes:
    """Undo the PNG row filters a writer may put in front of Flate."""
    width = columns + 1
    out = bytearray()
    previous = bytearray(columns)
    for start in range(0, len(data) - 1, width):
        row = bytearray(data[start + 1 : start + width])
        if len(row) < columns:
            break
        kind = data[start]
        if kind == 2:  # up, the only one a writer uses for a table of numbers
            for index in range(columns):
                row[index] = (row[index] + previous[index]) & 0xFF
        elif kind == 1:  # sub
            for index in range(1, columns):
                row[index] = (row[index] + row[index - 1]) & 0xFF
        out += row
        previous = row
    return bytes(out)


def _resolve(value: bytes, objects: dict[int, bytes]) -> bytes:
    """A reference followed to the object it names; anything else unchanged."""
    match = _REFERENCE.fullmatch(value.strip())
    if match is None:
        return value
    return objects.get(int(match.group(1)), b"")


# --- the pages -----------------------------------------------------------------


def _pages(raw: bytes, objects: dict[int, bytes]) -> Iterator[bytes]:
    """The page objects in the order the document puts them in.

    Walked from the root rather than collected by type, because the order is
    the page number and a number read off the wrong sequence is a false place.
    """
    root = _ROOT.search(raw)
    if root is None:
        return
    catalogue = objects.get(int(root.group(1)))
    if catalogue is None:
        return
    tree = re.search(rb"/Pages\s+(\d+)\s+\d+\s+R", catalogue)
    if tree is None:
        return
    yield from _leaves(int(tree.group(1)), objects, set(), b"")


def _leaves(
    number: int, objects: dict[int, bytes], seen: set[int], inherited: bytes
) -> Iterator[bytes]:
    """Every page under one node, depth first, with what it inherits attached."""
    if number in seen or len(seen) > MAX_OBJECTS:
        return  # a tree that points at itself is malformed, not infinite work
    seen.add(number)
    body = objects.get(number)
    if body is None:
        return
    # Resources are inherited down the tree, so a page that states none is
    # drawn with its parent's fonts and has to be read with them.
    resources = _entry(body, b"/Resources") or inherited
    kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
    if kids is not None:
        for child in _REFERENCE.finditer(kids.group(1)):
            yield from _leaves(int(child.group(1)), objects, seen, resources)
        return
    if _TYPE_PAGE.search(body):
        yield body + b"\n/filegrail-resources " + resources


def _entry(body: bytes, key: bytes) -> bytes:
    """One dictionary entry's raw value: a reference, a name or a `<<...>>`."""
    at = body.find(key)
    if at == -1:
        return b""
    rest = body[at + len(key) :].lstrip()
    if rest.startswith(b"<<"):
        depth, index = 0, 0
        while index < len(rest) - 1:
            if rest[index : index + 2] == b"<<":
                depth += 1
                index += 2
                continue
            if rest[index : index + 2] == b">>":
                depth -= 1
                index += 2
                if depth == 0:
                    return rest[:index]
                continue
            index += 1
        return rest
    match = re.match(rb"(\d+\s+\d+\s+R|/[^\s/\[\]<>]+|\[[^\]]*\])", rest)
    return match.group(1) if match else b""


def _contents(page: bytes, objects: dict[int, bytes]) -> Iterator[bytes]:
    """The content streams of one page, in the order they are drawn."""
    value = _entry(page, b"/Contents")
    references = [int(match.group(1)) for match in _REFERENCE.finditer(value)]
    for number in references:
        body = objects.get(number)
        if body is None:
            continue
        data = _stream(body, objects)
        if data is not None:
            yield data


# --- the fonts -----------------------------------------------------------------


def _fonts(page: bytes, objects: dict[int, bytes]) -> dict[bytes, Font]:
    """Every font the page names, with what each one's bytes mean."""
    resources = _resolve(_entry(page, b"/filegrail-resources"), objects)
    if resources.lstrip().startswith(b"<<") is False:
        resources = _resolve(resources, objects)
    table = _resolve(_entry(resources, b"/Font"), objects)
    found: dict[bytes, Font] = {}
    for match in re.finditer(rb"(/[^\s/\[\]<>]+)\s+(\d+)\s+\d+\s+R", table):
        body = objects.get(int(match.group(2)))
        if body is not None:
            found[match.group(1)[1:]] = _mapping(body, objects)
    return found


def _mapping(font: bytes, objects: dict[int, bytes]) -> Font:
    """What each code this font is shown draws, and how wide those codes are.

    An empty table means the run is dropped: a font whose glyphs cannot be
    established says nothing this tool is willing to repeat.
    """
    # A composite font is shown two bytes at a time unless its own CMap says
    # otherwise, which the `/ToUnicode` codespace below is allowed to correct.
    composite = b"/Type0" in font
    width = 2 if composite else 1

    unicode_map = _entry(font, b"/ToUnicode")
    if unicode_map:
        body = _resolve(unicode_map, objects)
        data = _stream(body, objects)
        if data:
            decoded, stated = _cmap(data)
            if decoded:
                return Font(stated or width, decoded)

    if composite:
        return Font(width, {})  # an identity encoding names glyphs, not letters

    encoding = _entry(font, b"/Encoding")
    if encoding.startswith(b"/"):
        return Font(1, dict(_named(encoding)))
    if encoding:
        block = _resolve(encoding, objects) if not encoding.startswith(b"<<") else encoding
        base = _entry(block, b"/BaseEncoding") or b"/StandardEncoding"
        table = dict(_named(base))
        differences = re.search(rb"/Differences\s*\[(.*?)\]", block, re.S)
        if differences is not None:
            table.update(_differences(differences.group(1)))
        return Font(1, table)
    return Font(1, {})


def _named(encoding: bytes) -> Iterator[tuple[int, str]]:
    """One of the encodings a font may name instead of describing.

    Only the positions these three agree on are taken: the printable ASCII
    range, which is where every address, host and hash is written. The upper
    halves differ between them and a wrong guess there writes an accent into
    the middle of a value.
    """
    if encoding.strip() not in (
        b"/WinAnsiEncoding",
        b"/MacRomanEncoding",
        b"/StandardEncoding",
        b"/PDFDocEncoding",
    ):
        return
    for code in range(0x20, 0x7F):
        yield code, chr(code)


def _differences(body: bytes) -> dict[int, str]:
    """A `/Differences` array: a code, then the glyphs that follow it."""
    table: dict[int, str] = {}
    code = 0
    for token in re.findall(rb"\d+|/[^\s/\[\]<>]+", body):
        if token.isdigit():
            code = int(token)
            continue
        letter = _glyph(token[1:].decode("latin-1"))
        if letter is not None:
            table[code] = letter
        code += 1
    return table


#: The glyph names that carry a value. Names outside this table - a subset
#: font's `g42`, a symbol, a logo - resolve to nothing and their code is left
#: out of the map, so the byte is dropped rather than guessed at.
_GLYPHS = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$",
    "percent": "%", "ampersand": "&", "quotesingle": "'", "quoteright": "'",
    "quoteleft": "'", "parenleft": "(", "parenright": ")", "asterisk": "*",
    "plus": "+", "comma": ",", "hyphen": "-", "period": ".", "slash": "/",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "colon": ":",
    "semicolon": ";", "less": "<", "equal": "=", "greater": ">", "question": "?",
    "at": "@", "bracketleft": "[", "backslash": "\\", "bracketright": "]",
    "asciicircum": "^", "underscore": "_", "grave": "`", "braceleft": "{",
    "bar": "|", "braceright": "}", "asciitilde": "~", "endash": "-", "emdash": "-",
    "hyphenchar": "-", "fi": "fi", "fl": "fl", "ff": "ff", "ffi": "ffi", "ffl": "ffl",
}  # fmt: skip


#: How a glyph name spells an accent, in the words Unicode uses for one. A name
#: like `aogonek` is a letter and a mark, and what it draws is the character
#: Unicode calls `LATIN SMALL LETTER A WITH OGONEK` - so what is kept here is
#: the marks, and the several thousand letters they make are derived. Without
#: this a Polish document loses every accented letter it has, and `Łódź` comes
#: back as `d`: not a letter missing but a word that reads as another one.
_MARKS = {
    "acute": "ACUTE", "grave": "GRAVE", "circumflex": "CIRCUMFLEX",
    "dieresis": "DIAERESIS", "tilde": "TILDE", "ring": "RING ABOVE",
    "cedilla": "CEDILLA", "ogonek": "OGONEK", "caron": "CARON",
    "breve": "BREVE", "macron": "MACRON", "slash": "STROKE", "bar": "STROKE",
    "dotaccent": "DOT ABOVE", "hungarumlaut": "DOUBLE ACUTE",
    "commaaccent": "COMMA BELOW", "stroke": "STROKE",
}  # fmt: skip


def _glyph(name: str) -> str | None:
    """What a glyph name draws, where this module can say."""
    if len(name) == 1 and name.isascii() and name.isprintable():
        return name
    if name in _GLYPHS:
        return _GLYPHS[name]
    accented = re.fullmatch(r"([A-Za-z])([a-z]+)", name)
    if accented is not None and accented.group(2) in _MARKS:
        letter, mark = accented.group(1), _MARKS[accented.group(2)]
        case = "CAPITAL" if letter.isupper() else "SMALL"
        try:
            return unicodedata.lookup(f"LATIN {case} LETTER {letter.upper()} WITH {mark}")
        except KeyError:
            return None
    match = re.fullmatch(r"uni([0-9A-Fa-f]{4})|u([0-9A-Fa-f]{4,6})", name)
    if match is not None:
        try:
            return chr(int(match.group(1) or match.group(2), 16))
        except ValueError:
            return None
    return None


def _cmap(data: bytes) -> tuple[dict[int, str], int]:
    """A `/ToUnicode` CMap: single codes, ranges of them, and how wide a code is.

    The width comes from the codespace the CMap declares, and failing that from
    the codes it writes - four hex digits is a two-byte code. Guessing it wrong
    in either direction reads the document through the wrong positions.
    """
    table: dict[int, str] = {}
    widths = {
        len(low) // 2
        for block in re.findall(rb"begincodespacerange(.*?)endcodespacerange", data, re.S)
        for low, _ in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block)
    }
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for source, target in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            letter = _utf16(target)
            if letter is not None:
                table[int(source, 16)] = letter
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for low, high, target in re.findall(
            rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            start, end = int(low, 16), int(high, 16)
            first = _utf16(target)
            if first is None or end < start or end - start > 0xFFFF:
                continue
            for offset in range(end - start + 1):
                table[start + offset] = chr(ord(first[0]) + offset) + first[1:]
    if not widths:
        widths = {
            len(source) // 2
            for block in re.findall(rb"beginbf(?:char|range)(.*?)endbf(?:char|range)", data, re.S)
            for source in re.findall(rb"<([0-9A-Fa-f]+)>", block)[:1]
        }
    return table, max(widths) if widths else 0


def _utf16(target: bytes) -> str | None:
    """A CMap's value, which is UTF-16BE however many code units it holds."""
    try:
        letter = bytes.fromhex(target.decode("ascii")).decode("utf-16-be")
    except (ValueError, UnicodeDecodeError):
        return None
    return letter or None


# --- what the page draws ---------------------------------------------------------


def _show(content: bytes, fonts: dict[bytes, Font]) -> str:
    """The text the drawing instructions put on one page.

    Where the break goes decides what gets reported. Inside a `TJ` array the
    pieces are one run and are joined, because the numbers between them are
    kerning and a document that draws `exam` `ple.com` has written one address;
    past a fifth of an em the gap is a space the writer chose not to draw.

    Every other boundary breaks the run. Joining across them was measured on
    real documents and reported more values that were never written than it
    recovered: a table whose columns sit on one baseline turns `0` and `works`
    into a domain. A break costs at most a value that was split in two. A join
    invents one, which is the more expensive of the two mistakes here.
    """
    out: list[str] = []
    font: Font | None = None
    pending: list[tuple[bytes, str]] = []
    for token, kind in _tokens(content):
        if kind in ("string", "hex", "number", "name"):
            pending.append((token, kind))
            continue
        if kind != "operator":
            continue
        if token == b"Tf":
            for value, sort in reversed(pending):
                if sort == "name":
                    font = fonts.get(value[1:])
                    break
        elif token in (b"Tj", b"'", b'"'):
            for value, sort in reversed(pending):
                if sort in ("string", "hex"):
                    out.append(_text(value, sort, font))
                    break
            out.append(" ")
        elif token == b"TJ":
            for value, sort in pending:
                if sort in ("string", "hex"):
                    out.append(_text(value, sort, font))
                elif sort == "number" and _kerned(value):
                    out.append(" ")
            out.append(" ")
        elif token in (b"Td", b"TD", b"T*", b"Tm", b"ET"):
            out.append("\n")
        pending = []
    return "".join(out)


def _kerned(value: bytes) -> bool:
    try:
        return float(value) <= _SPACE_KERN
    except ValueError:
        return False


def _text(value: bytes, kind: str, font: Font | None) -> str:
    """One drawn string, through the font that draws it."""
    raw = _hex(value) if kind == "hex" else _literal(value)
    if font is not None and font.table:
        return "".join(font.table.get(code, "") for code in _codes(raw, font.width))
    if font is not None and font.width > 1:
        return ""  # a composite font whose codes mean nothing without its map
    # A font that states no encoding is read as ASCII and nothing else: see
    # the module docstring. Anything outside that range is dropped.
    return "".join(chr(code) if 0x20 <= code <= 0x7E else "" for code in raw)


def _codes(raw: bytes, width: int) -> Iterator[int]:
    """The string's bytes as the codes the font is shown, however wide."""
    if width <= 1:
        yield from raw
        return
    for at in range(0, len(raw) - width + 1, width):
        yield int.from_bytes(raw[at : at + width], "big")


def _hex(value: bytes) -> bytes:
    digits = re.sub(rb"[^0-9A-Fa-f]", b"", value)
    if len(digits) % 2:
        digits += b"0"
    try:
        return bytes.fromhex(digits.decode("ascii"))
    except ValueError:
        return b""


_ESCAPES = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
_OCTAL = set(b"01234567")


def _literal(value: bytes) -> bytes:
    """A `(...)` string with its escapes undone, still as the font's own bytes."""
    out = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != 0x5C:  # backslash
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(value):
            break
        nxt = value[index]
        if nxt in _OCTAL:
            octal = bytearray()
            while len(octal) < 3 and index < len(value) and value[index] in _OCTAL:
                octal.append(value[index])
                index += 1
            out.append(int(octal, 8) & 0xFF)
            continue
        if nxt in _ESCAPES:
            out.append(_ESCAPES[nxt])
        elif nxt not in (10, 13):  # a line continuation draws nothing
            out.append(nxt)
        index += 1
    return bytes(out)


def _tokens(content: bytes) -> Iterator[tuple[bytes, str]]:
    """The content stream's tokens, with strings scanned rather than matched.

    A PDF string nests its parentheses, which no regular expression can follow,
    so the one construct that needs a scanner gets one and everything else is
    matched around it.
    """
    index, length = 0, len(content)
    while index < length:
        char = content[index]
        if char in b" \t\r\n\x00":
            index += 1
            continue
        if char == 0x28:  # (
            start = index + 1
            depth, index = 1, index + 1
            while index < length and depth:
                if content[index] == 0x5C:
                    index += 2
                    continue
                if content[index] == 0x28:
                    depth += 1
                elif content[index] == 0x29:
                    depth -= 1
                index += 1
            yield content[start : index - 1], "string"
            continue
        if char == 0x3C and index + 1 < length and content[index + 1] != 0x3C:  # <
            end = content.find(b">", index)
            if end == -1:
                return
            yield content[index + 1 : end], "hex"
            index = end + 1
            continue
        match = re.compile(rb"<<|>>|/[^\s/\[\]<>(){}]*|[-+.\d][-+.\d]*|[A-Za-z'\"*]+").match(
            content, index
        )
        if match is None:
            index += 1
            continue
        token = match.group(0)
        if token[:1] == b"/":
            yield token, "name"
        elif token[:1].isdigit() or token[:1] in b"-+.":
            yield token, "number"
        elif token in (b"<<", b">>"):
            pass
        else:
            yield token, "operator"
        index = match.end()
