"""What a PDF shows, read through the font that draws it.

A PDF stores instructions, not text: the bytes in a drawing instruction are
indices into whatever encoding the font uses, and two documents that look the
same can hold different bytes. So the test that matters is not that some text
comes back - it is that a document whose bytes are *not* the letters is read
correctly, and that one whose glyphs cannot be established is not read at all.

The failure this reader exists to avoid is an address assembled out of the
wrong glyphs. Dropping a run costs a lead; inventing one costs the case.
"""

from __future__ import annotations

from pathlib import Path

from filegrail.sources.content import read_passages
from filegrail.sources.pdftext import read_pages
from tests.pdf import document, stream, tounicode

#: One font whose bytes are not what they draw: `A` draws `m`, `B` draws `@`.
#: Reading the bytes would report `AB`, which is in no document anywhere.
SHIFTED = {0x41: "m", 0x42: "@", 0x43: "x", 0x44: ".", 0x45: "c", 0x46: "o"}


def _shows(text: bytes) -> bytes:
    return b"BT /F1 12 Tf 72 720 Td (" + text + b") Tj ET"


def test_a_page_says_what_it_draws_and_which_page_it_is(tmp_path: Path):
    path = tmp_path / "brief.pdf"
    path.write_bytes(document([_shows(b"write to press@example.org"), _shows(b"second")]))

    found = read_passages(path)

    assert found is not None
    assert [passage.place for passage in found] == ["page 1", "page 2"]
    assert "press@example.org" in found[0].text


def test_the_bytes_are_read_through_the_font_rather_than_as_letters(tmp_path: Path):
    """The whole reason this is a parser. `ABCDEF` here draws `m@x.co`."""
    path = tmp_path / "mapped.pdf"
    path.write_bytes(
        document(
            [_shows(b"ABCDEF")],
            font=b"<< /Type /Font /Subtype /Type1 /BaseFont /X /ToUnicode {extra} >>",
            extra=stream(tounicode(SHIFTED)) + b"\nendstream",
        )
    )

    found = read_passages(path)

    assert found is not None
    assert "m@x.co" in found[0].text
    assert "ABCDEF" not in found[0].text


def test_a_composite_font_is_read_the_width_its_codes_are_written_in(tmp_path: Path):
    """What a word processor writes. Its codes are two bytes and its glyph
    indices run past 255; read one byte at a time they land on other entries
    of the same map, which returns letters from the wrong places rather than
    failing. Here `m@x.co` would come back as `.`."""
    mapping = {0x0124: "m", 0x0225: "@", 0x0326: "x", 0x0027: ".", 0x0128: "c", 0x0229: "o"}
    drawn = b"".join(code.to_bytes(2, "big") for code in mapping)
    path = tmp_path / "word.pdf"
    path.write_bytes(
        document(
            [b"BT /F1 12 Tf 72 720 Td <" + drawn.hex().encode() + b"> Tj ET"],
            font=(
                b"<< /Type /Font /Subtype /Type0 /BaseFont /X "
                b"/Encoding /Identity-H /ToUnicode {extra} >>"
            ),
            extra=stream(tounicode(mapping, width=2)) + b"\nendstream",
        )
    )

    found = read_passages(path)

    assert found is not None
    assert "m@x.co" in found[0].text


def test_a_font_whose_glyphs_mean_nothing_here_is_dropped_rather_than_guessed(tmp_path: Path):
    """A subset font naming `g1 g2 g3` says what it draws to nobody. Reading
    the bytes anyway would put whatever they happen to be into the report."""
    path = tmp_path / "subset.pdf"
    path.write_bytes(
        document(
            [_shows(b"\x01\x02\x03")],
            font=(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /X "
                b"/Encoding << /Differences [1 /g1 /g2 /g3] >> >>"
            ),
        )
    )

    assert read_passages(path) is None


def test_an_encrypted_document_is_refused(tmp_path: Path):
    """Its strings are ciphertext, and decoding them would be invention."""
    path = tmp_path / "locked.pdf"
    path.write_bytes(document([_shows(b"press@example.org")], catalogue=b"/Encrypt 99 0 R "))

    assert read_passages(path) is None


def test_a_run_split_by_kerning_is_one_value(tmp_path: Path):
    """A writer draws `exam` and `ple.org` with a kern between them. Joined
    with a space, the address in the document is not the address reported."""
    path = tmp_path / "kerned.pdf"
    path.write_bytes(document([b"BT /F1 12 Tf 72 720 Td [(press@exam) -5 (ple.org)] TJ ET"]))

    found = read_passages(path)

    assert found is not None
    assert "press@example.org" in found[0].text


def test_a_document_too_large_to_hold_is_not_read_in_part(tmp_path: Path):
    """Half a PDF is not a shorter PDF. The page tree lives at the end."""
    import filegrail.sources.content as reader

    path = tmp_path / "huge.pdf"
    path.write_bytes(document([_shows(b"press@example.org")]))
    limit = reader.MAX_FILE_BYTES
    reader.MAX_FILE_BYTES = 8
    try:
        assert read_passages(path) is None
    finally:
        reader.MAX_FILE_BYTES = limit


def test_nothing_is_reported_for_a_file_that_is_not_a_pdf(tmp_path: Path):
    path = tmp_path / "claimed.pdf"
    path.write_bytes(b"this is not a document at all")

    assert read_pages(path.read_bytes()) == []
