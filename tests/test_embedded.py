import struct
import zipfile
from pathlib import Path

from filetrail.sources.embedded import read_embedded_metadata

CORE_XML = """<?xml version="1.0"?>
<cp:coreProperties
  xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:creator>Jan Kowalski</dc:creator>
  <cp:lastModifiedBy>Anna Nowak</cp:lastModifiedBy>
  <dcterms:created>2026-03-12T09:14:00Z</dcterms:created>
</cp:coreProperties>"""

APP_XML = """<?xml version="1.0"?>
<Properties
  xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Microsoft Office Word</Application>
  <AppVersion>16.0000</AppVersion>
  <Company>Acme Holdings</Company>
</Properties>"""


def test_reads_ooxml_authorship(tmp_path: Path):
    document = tmp_path / "report.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("docProps/core.xml", CORE_XML)
        archive.writestr("docProps/app.xml", APP_XML)

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.source == "document-metadata"
    assert origin.tool == "Microsoft Office Word 16.0000"
    assert origin.at == "2026-03-12T09:14:00Z"
    assert "author Jan Kowalski" in origin.note
    assert "last edited by Anna Nowak" in origin.note
    assert "company Acme Holdings" in origin.note
    assert origin.confidence == 50


def test_ooxml_without_properties_yields_nothing(tmp_path: Path):
    document = tmp_path / "empty.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")

    assert read_embedded_metadata(document) is None


def test_reads_pdf_info_dictionary(tmp_path: Path):
    document = tmp_path / "paper.pdf"
    document.write_bytes(
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Producer (Adobe PDF Library 15.0) "
        b"/Creator (Adobe InDesign CC 13.1) "
        b"/Author (Maria Wolf) "
        b"/CreationDate (D:20180511143720+02'00') >>\nendobj\n"
    )

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool == "Adobe PDF Library 15.0 (created in Adobe InDesign CC 13.1)"
    assert origin.at == "2018-05-11T14:37:20Z"
    assert origin.note == "author Maria Wolf"


def test_pdf_with_only_a_producer(tmp_path: Path):
    document = tmp_path / "print.pdf"
    document.write_bytes(b"%PDF-1.4\n<< /Producer (Skia/PDF m142) >>\n")

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool == "Skia/PDF m142"
    assert origin.at is None


def test_pdf_without_metadata_yields_nothing(tmp_path: Path):
    document = tmp_path / "bare.pdf"
    document.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n")

    assert read_embedded_metadata(document) is None


def _jpeg_with_exif(path: Path, make: str, model: str, taken: str) -> None:
    """Build a minimal JPEG carrying an Exif APP1 segment with three ASCII tags."""
    entries = [(0x010F, make), (0x0110, model), (0x0132, taken)]

    header = b"MM\x00\x2a" + struct.pack(">I", 8)
    values = b""
    value_base = 8 + 2 + len(entries) * 12 + 4
    directory = struct.pack(">H", len(entries))
    for tag, text in entries:
        raw = text.encode("ascii") + b"\x00"
        directory += struct.pack(">HHI", tag, 2, len(raw))
        directory += struct.pack(">I", value_base + len(values))
        values += raw
    tiff = header + directory + struct.pack(">I", 0) + values

    app1 = b"Exif\x00\x00" + tiff
    path.write_bytes(
        b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"
    )


def test_reads_jpeg_camera_and_capture_time(tmp_path: Path):
    photo = tmp_path / "photo.jpg"
    _jpeg_with_exif(photo, "Canon", "Canon EOS 5D", "2026:04:19 21:43:48")

    origin = read_embedded_metadata(photo)

    assert origin is not None
    # The maker is not repeated when the model already carries it.
    assert origin.tool == "Canon EOS 5D"
    assert origin.at == "2026-04-19T21:43:48Z"
    assert origin.source == "device-metadata"


def test_maker_is_kept_when_the_model_does_not_carry_it(tmp_path: Path):
    photo = tmp_path / "photo.jpg"
    _jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2026:04:19 21:43:48")

    assert read_embedded_metadata(photo).tool == "NIKON COOLPIX P6000"


def test_jpeg_without_exif_yields_nothing(tmp_path: Path):
    photo = tmp_path / "plain.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xdb\x00\x04\x00\x00\xff\xd9")

    assert read_embedded_metadata(photo) is None


def test_unsupported_and_corrupt_files_are_not_an_error(tmp_path: Path):
    plain = tmp_path / "notes.txt"
    plain.write_text("hello", encoding="utf-8")
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a zip at all")

    assert read_embedded_metadata(plain) is None
    assert read_embedded_metadata(broken) is None


def test_reads_hex_string_info_values(tmp_path: Path):
    """LibreOffice writes /Producer<FEFF...> rather than a literal string."""
    document = tmp_path / "hex.pdf"
    producer = "LibreOffice 24.2".encode("utf-16-be").hex().upper()
    author = "OSINT360".encode("utf-16-be").hex().upper()
    document.write_bytes(
        b"%PDF-1.6\n<< /Producer<FEFF"
        + producer.encode()
        + b"> /Author<FEFF"
        + author.encode()
        + b"> >>\n"
    )

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool == "LibreOffice 24.2"
    assert origin.note == "author OSINT360"
    assert "﻿" not in origin.tool  # the byte-order mark must not survive


def test_empty_info_values_do_not_mask_a_real_date(tmp_path: Path):
    document = tmp_path / "empty-producer.pdf"
    document.write_bytes(
        b"%PDF-1.4\n<< /Creator () /Producer () /CreationDate (D:20260720190521+00'00') >>\n"
    )

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool is None
    assert origin.at == "2026-07-20T19:05:21Z"


def test_reads_info_from_a_compressed_object_stream(tmp_path: Path):
    """PDF 1.5+ writers put the Info dictionary inside a Flate stream."""
    import zlib

    inner = b"<< /Producer (WeasyPrint 68.0) /Creator (pandoc) >>"
    compressed = zlib.compress(inner)
    document = tmp_path / "objstm.pdf"
    document.write_bytes(
        b"%PDF-1.7\n5 0 obj\n<< /Type /ObjStm /Filter /FlateDecode >>\nstream\n"
        + compressed
        + b"\nendstream\nendobj\n"
    )

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool == "WeasyPrint 68.0 (created in pandoc)"


def test_undecompressable_stream_is_not_an_error(tmp_path: Path):
    document = tmp_path / "broken-stream.pdf"
    document.write_bytes(
        b"%PDF-1.7\nstream\nnot actually deflate data at all\nendstream\n"
        b"<< /Producer (Fallback 1.0) >>\n"
    )

    origin = read_embedded_metadata(document)

    assert origin is not None
    assert origin.tool == "Fallback 1.0"
