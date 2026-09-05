"""Writing a copy of a file with its metadata taken out.

This is the one thing in the project that produces a file, and it does so under
a rule the rest of the tool depends on: **the original is never touched**. A
cleaned copy is written somewhere else, and the source is left exactly as it
was found - which is what keeps `filegrail` safe to point at evidence.

Removal is claimed only where it can be verified. Every stripper here is held
against the readers that find metadata in the first place: if a reader can
still see something in the output, the copy is not clean and says so.
"""

from __future__ import annotations

import struct
import zipfile
import zlib
from pathlib import Path

from filegrail.clean import clean_file
from filegrail.sources.embedded import read_embedded_metadata
from tests.photo import jpeg_with_exif


def test_a_photographs_exif_does_not_survive_the_copy(tmp_path: Path):
    photo = tmp_path / "holiday.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(photo, out)

    assert result.written == out / "holiday.jpg"
    assert read_embedded_metadata(result.written) is None
    assert "exif" in result.removed


def test_the_original_is_left_exactly_as_it_was(tmp_path: Path):
    """The rest of the tool promises never to write to what it inspects, and
    the one command that writes anything must not be the exception."""
    photo = tmp_path / "holiday.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    before = photo.read_bytes()
    out = tmp_path / "clean"
    out.mkdir()

    clean_file(photo, out)

    assert photo.read_bytes() == before
    assert read_embedded_metadata(photo) is not None


def test_the_image_itself_is_still_there(tmp_path: Path):
    """Stripping metadata is not the same as damaging the file. What is left
    has to remain a readable image, or the copy is useless."""
    photo = tmp_path / "holiday.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    out = tmp_path / "clean"
    out.mkdir()

    written = clean_file(photo, out).written
    raw = written.read_bytes()

    assert raw.startswith(b"\xff\xd8")  # still a JPEG
    assert raw.endswith(b"\xff\xd9")  # with its end marker intact


def test_a_file_with_nothing_to_remove_says_so(tmp_path: Path):
    plain = tmp_path / "notes.txt"
    plain.write_text("nothing here", encoding="utf-8")
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(plain, out)

    assert result.written is None
    assert result.removed == []


# --- PNG ---------------------------------------------------------------------


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _png(path: Path, *extra: bytes) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + b"".join(extra)
        + _chunk(b"IDAT", b"\x00")
        + _chunk(b"IEND", b"")
    )


def test_a_pngs_text_chunks_do_not_survive(tmp_path: Path):
    image = tmp_path / "chart.png"
    _png(image, _chunk(b"tEXt", b"Author\x00A. Person"), _chunk(b"tEXt", b"Software\x00Some Tool"))
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(image, out)

    assert "png-text" in result.removed
    assert read_embedded_metadata(result.written) is None


def test_the_png_is_still_a_png(tmp_path: Path):
    """Every chunk that makes it an image has to survive, and the stream has to
    still end where a decoder expects it to."""
    image = tmp_path / "chart.png"
    _png(image, _chunk(b"tEXt", b"Author\x00A. Person"))
    out = tmp_path / "clean"
    out.mkdir()

    raw = clean_file(image, out).written.read_bytes()

    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IHDR" in raw and b"IDAT" in raw
    assert raw.endswith(_chunk(b"IEND", b""))
    assert b"A. Person" not in raw


def test_a_png_with_no_text_is_left_alone(tmp_path: Path):
    image = tmp_path / "plain.png"
    _png(image)
    out = tmp_path / "clean"
    out.mkdir()

    assert clean_file(image, out).written is None


# --- ISO base media (MP4, MOV) -----------------------------------------------


def _atom(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + kind + payload


def _itunes_text(kind: bytes, text: str) -> bytes:
    raw = text.encode("utf-8")
    return _atom(kind, _atom(b"data", struct.pack(">II", 1, 0) + raw))


def _mvhd(created: int = 3_500_000_000) -> bytes:
    return _atom(b"mvhd", struct.pack(">IIIII", 0, created, created, 1000, 0) + b"\x00" * 80)


def test_a_movies_recording_metadata_does_not_survive(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    udta = _atom(
        b"udta",
        _itunes_text(b"\xa9too", "Lavf58.44.100") + _itunes_text(b"\xa9xyz", "+43.4674+011.8851/"),
    )
    clip.write_bytes(_atom(b"ftyp", b"isom") + _atom(b"moov", _mvhd() + udta))
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(clip, out)

    assert read_embedded_metadata(result.written) is None
    assert b"Lavf58.44.100" not in result.written.read_bytes()
    assert b"43.4674" not in result.written.read_bytes()


def test_the_movie_keeps_its_length_so_its_offsets_still_point_somewhere(tmp_path: Path):
    """A movie's sample tables address the media by absolute offset, so cutting
    bytes out of the header would leave every one of them pointing at the wrong
    place. The metadata is overwritten in place instead, and the file is
    exactly as long as it was."""
    clip = tmp_path / "clip.mp4"
    udta = _atom(b"udta", _itunes_text(b"\xa9too", "Lavf58.44.100"))
    clip.write_bytes(
        _atom(b"ftyp", b"isom") + _atom(b"moov", _mvhd() + udta) + _atom(b"mdat", b"x" * 64)
    )
    out = tmp_path / "clean"
    out.mkdir()

    written = clean_file(clip, out).written

    assert written.stat().st_size == clip.stat().st_size
    assert b"x" * 64 in written.read_bytes()  # the media itself is untouched


# --- the zip-based document formats ------------------------------------------


def _docx(path: Path) -> None:
    core = (
        '<?xml version="1.0"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
        'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:creator>A. Person</dc:creator>"
        "<cp:lastModifiedBy>Someone Else</cp:lastModifiedBy>"
        "</cp:coreProperties>"
    )
    app = (
        '<?xml version="1.0"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        'extended-properties"><Company>A Company</Company><Application>Word</Application>'
        "</Properties>"
    )
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        bundle.writestr("docProps/core.xml", core)
        bundle.writestr("docProps/app.xml", app)
        bundle.writestr("word/document.xml", "<w:document>the text itself</w:document>")


def test_a_documents_author_does_not_survive(tmp_path: Path):
    document = tmp_path / "report.docx"
    _docx(document)
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(document, out)

    assert read_embedded_metadata(result.written) is None
    assert b"A. Person" not in result.written.read_bytes()
    assert b"A Company" not in result.written.read_bytes()


def test_the_document_is_still_a_document(tmp_path: Path):
    """The properties are emptied rather than deleted: a package whose parts
    are named in its relationships and are then missing is a broken one."""
    document = tmp_path / "report.docx"
    _docx(document)
    out = tmp_path / "clean"
    out.mkdir()

    with zipfile.ZipFile(clean_file(document, out).written) as bundle:
        names = set(bundle.namelist())
        assert bundle.read("word/document.xml") == b"<w:document>the text itself</w:document>"

    assert {"[Content_Types].xml", "docProps/core.xml", "word/document.xml"} <= names


# --- checking the work -------------------------------------------------------


def test_a_clean_copy_reports_nothing_left(tmp_path: Path):
    photo = tmp_path / "holiday.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    out = tmp_path / "clean"
    out.mkdir()

    assert clean_file(photo, out).remaining == []


def test_what_the_stripper_missed_is_reported_rather_than_hidden(tmp_path: Path):
    """A packet appended after the end-of-image marker is outside the segment
    stream, so rebuilding the segments does not touch it. Somebody publishing
    on the strength of "cleaned" needs to be told that, so the copy is read
    back with the same readers that find metadata in the first place."""
    photo = tmp_path / "holiday.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    photo.write_bytes(
        photo.read_bytes() + b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        b'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
        b'xmlns:xmp="http://ns.adobe.com/xap/1.0/"><xmp:CreatorTool>Some Editor'
        b"</xmp:CreatorTool></rdf:Description></rdf:RDF></x:xmpmeta>"
    )
    out = tmp_path / "clean"
    out.mkdir()

    result = clean_file(photo, out)

    assert "xmp" in result.remaining
