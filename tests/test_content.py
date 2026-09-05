"""What a file says, as opposed to what it records about itself."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from filegrail.sources.content import MAX_TEXT_BYTES, read_text
from tests.compound import ole


def _zip(path: Path, members: dict[str, str]) -> None:
    written = io.BytesIO()
    with zipfile.ZipFile(written, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, text in members.items():
            bundle.writestr(name, text)
    path.write_bytes(written.getvalue())


# --- files that are already text ----------------------------------------------


def test_a_text_file_is_its_own_text(tmp_path: Path):
    note = tmp_path / "notes.txt"
    note.write_text("write to ann.shaw@acme-legal.example", encoding="utf-8")

    assert read_text(note) == "write to ann.shaw@acme-legal.example"


def test_utf_16_is_read_as_utf_16(tmp_path: Path):
    """A Windows editor writes a byte order mark, and a UTF-8 read of that puts
    a NUL between every letter - which breaks every pattern, not one accent."""
    note = tmp_path / "notes.txt"
    note.write_bytes("ann.shaw@acme-legal.example".encode("utf-16"))

    assert read_text(note) == "ann.shaw@acme-legal.example"


def test_a_format_nothing_here_reads_says_so(tmp_path: Path):
    photo = tmp_path / "holiday.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")

    assert read_text(photo) is None


def test_the_text_of_one_file_is_bounded(tmp_path: Path):
    note = tmp_path / "huge.log"
    note.write_text("a" * (MAX_TEXT_BYTES * 2), encoding="utf-8")

    assert len(read_text(note)) == MAX_TEXT_BYTES


# --- markup -------------------------------------------------------------------


def test_html_gives_up_its_text_and_its_links(tmp_path: Path):
    page = tmp_path / "invoice.html"
    page.write_text(
        "<html><head><style>a { color: #abc; }</style>"
        "<script>var host = 'tracker.example';</script></head>"
        "<body><p>Invoice from <b>Acme</b></p>"
        '<a href="https://acme-legal.example/pay">pay here</a></body></html>',
        encoding="utf-8",
    )

    text = read_text(page)

    assert "Invoice from Acme" in " ".join(text.split())
    assert "https://acme-legal.example/pay" in text


def test_html_leaves_the_script_and_the_style_out(tmp_path: Path):
    """Neither is what the document says, and both are full of things that
    match: a colour is a hash, a bundler writes hosts nobody typed."""
    page = tmp_path / "page.html"
    page.write_text(
        "<html><style>.x { color: #aabbccddeeff00112233445566778899; }</style>"
        "<script>fetch('https://cdn.tracker.example/a.js');</script>"
        "<body>hello</body></html>",
        encoding="utf-8",
    )

    text = read_text(page)

    assert "hello" in text
    assert "tracker.example" not in text


def test_a_namespace_declaration_is_not_something_the_document_said(tmp_path: Path):
    """Every XML file in the world names w3.org. It is markup, not content."""
    drawing = tmp_path / "logo.svg"
    drawing.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><title>Acme</title>'
        '<a href="https://acme-legal.example">brand</a></svg>',
        encoding="utf-8",
    )

    text = read_text(drawing)

    assert "Acme" in text
    assert "https://acme-legal.example" in text
    assert "w3.org" not in text


# --- the zip-based document formats -------------------------------------------


def test_a_word_document_gives_up_its_body(tmp_path: Path):
    document = tmp_path / "letter.docx"
    _zip(
        document,
        {
            "docProps/core.xml": "<cp:coreProperties/>",
            "word/document.xml": "<w:document><w:t>Contact ann.shaw@acme-legal.example</w:t>"
            "</w:document>",
        },
    )

    assert "ann.shaw@acme-legal.example" in read_text(document)


def test_a_word_document_footnote_counts_as_its_body(tmp_path: Path):
    document = tmp_path / "letter.docx"
    _zip(
        document,
        {
            "word/document.xml": "<w:document><w:t>see below</w:t></w:document>",
            "word/footnotes.xml": "<w:footnotes><w:t>ann.shaw@acme-legal.example</w:t>"
            "</w:footnotes>",
        },
    )

    text = read_text(document)

    assert "see below" in text
    assert "ann.shaw@acme-legal.example" in text


def test_a_presentation_gives_up_every_slide(tmp_path: Path):
    deck = tmp_path / "deck.pptx"
    _zip(
        deck,
        {
            "ppt/slides/slide1.xml": "<p:sld><a:t>first</a:t></p:sld>",
            "ppt/slides/slide2.xml": "<p:sld><a:t>ann.shaw@acme-legal.example</a:t></p:sld>",
        },
    )

    text = read_text(deck)

    assert "first" in text
    assert "ann.shaw@acme-legal.example" in text


def test_a_spreadsheet_gives_up_its_shared_strings(tmp_path: Path):
    book = tmp_path / "ledger.xlsx"
    _zip(
        book,
        {
            "xl/sharedStrings.xml": "<sst><si><t>ann.shaw@acme-legal.example</t></si></sst>",
            "xl/worksheets/sheet1.xml": "<worksheet><v>42</v></worksheet>",
        },
    )

    assert "ann.shaw@acme-legal.example" in read_text(book)


def test_an_opendocument_file_gives_up_its_content(tmp_path: Path):
    document = tmp_path / "letter.odt"
    _zip(
        document,
        {
            "meta.xml": "<office:document-meta/>",
            "content.xml": "<office:body><text:p>ann.shaw@acme-legal.example</text:p>"
            "</office:body>",
        },
    )

    assert "ann.shaw@acme-legal.example" in read_text(document)


def test_an_epub_gives_up_its_chapters(tmp_path: Path):
    book = tmp_path / "book.epub"
    _zip(
        book,
        {
            "META-INF/container.xml": "<container/>",
            "OEBPS/chapter1.xhtml": "<html><body><p>ann.shaw@acme-legal.example</p></body></html>",
        },
    )

    assert "ann.shaw@acme-legal.example" in read_text(book)


def test_a_package_that_is_not_a_package_says_nothing(tmp_path: Path):
    document = tmp_path / "letter.docx"
    document.write_bytes(b"PK\x03\x04 and then nothing")

    assert read_text(document) is None


# --- mail ---------------------------------------------------------------------


def test_a_message_gives_up_its_body_and_not_its_headers(tmp_path: Path):
    """The headers are already read as evidence of delivery. Repeating them here
    would count one address twice and file it under the wrong corpus."""
    message = tmp_path / "message.eml"
    message.write_bytes(
        b"From: sender@example.test\r\nTo: someone@example.test\r\n"
        b"Subject: the file\r\nContent-Type: text/plain\r\n\r\n"
        b"Write to ann.shaw@acme-legal.example\r\n"
    )

    text = read_text(message)

    assert "ann.shaw@acme-legal.example" in text
    assert "sender@example.test" not in text


def test_a_message_body_is_decoded_before_it_is_read(tmp_path: Path):
    """Quoted-printable hides an address from anything reading the raw bytes."""
    message = tmp_path / "message.eml"
    message.write_bytes(
        b"From: sender@example.test\r\nContent-Type: text/plain\r\n"
        b"Content-Transfer-Encoding: quoted-printable\r\n\r\n"
        b"Write to ann=2Eshaw@acme-legal.example\r\n"
    )

    assert "ann.shaw@acme-legal.example" in read_text(message)


def test_an_outlook_message_gives_up_its_body(tmp_path: Path):
    message = tmp_path / "message.msg"
    message.write_bytes(
        ole({"__substg1.0_1000001F": "ann.shaw@acme-legal.example".encode("utf-16-le")})
    )

    assert "ann.shaw@acme-legal.example" in read_text(message)


def test_only_so_many_members_of_one_package_are_read(tmp_path: Path):
    """A deck can hold a thousand slides, and each one costs an open and a parse."""
    from filegrail.sources.content import MAX_PARTS

    deck = tmp_path / "deck.pptx"
    _zip(
        deck,
        {
            f"ppt/slides/slide{number}.xml": f"<p:sld><a:t>slide-{number}</a:t></p:sld>"
            for number in range(1, MAX_PARTS + 3)
        },
    )

    text = read_text(deck)

    assert "slide-1" in text
    assert f"slide-{MAX_PARTS + 2}" not in text


def test_a_member_too_large_to_read_does_not_take_the_rest_with_it(tmp_path: Path):
    """`read_part` refuses one member; the document is not only that member."""
    from filegrail.sources.embedded.parts import MAX_PART_BYTES

    document = tmp_path / "letter.docx"
    _zip(
        document,
        {
            "word/document.xml": "<w:t>" + "a" * (MAX_PART_BYTES + 1) + "</w:t>",
            "word/footnotes.xml": "<w:t>ann.shaw@acme-legal.example</w:t>",
        },
    )

    text = read_text(document)

    assert "ann.shaw@acme-legal.example" in text
    assert "aaaa" not in text
