"""One test per container family, built from minimal valid files."""

import json
import struct
import zipfile
import zlib
from pathlib import Path

from filetrail.sources.embedded import read_embedded_metadata
from filetrail.sources.embedded.exif import camera, coordinates, read_exif

# --- EXIF, and the containers that carry it ----------------------------------


def _ifd(entries: list[tuple[int, int, object]], base: int) -> tuple[bytes, bytes]:
    """Build a big-endian IFD plus its out-of-line value block."""
    directory = struct.pack(">H", len(entries))
    values = b""
    value_base = base + 2 + len(entries) * 12 + 4

    for tag, kind, value in entries:
        if kind == 2:
            raw = value.encode("ascii") + b"\x00"
            count = len(raw)
        elif kind == 5:
            raw = b"".join(struct.pack(">II", n, d) for n, d in value)
            count = len(value)
        else:
            raw = struct.pack(">I", value)
            count = 1

        directory += struct.pack(">HHI", tag, kind, count)
        if kind == 4 or len(raw) <= 4:
            directory += raw.ljust(4, b"\x00")[:4]
        else:
            directory += struct.pack(">I", value_base + len(values))
            values += raw
    return directory + struct.pack(">I", 0), values


def _tiff(main: list, gps: list | None = None) -> bytes:
    """Assemble a TIFF header with an optional GPS sub-IFD."""
    header = b"MM\x00\x2a" + struct.pack(">I", 8)
    if not gps:
        directory, values = _ifd(main, 8)
        return header + directory + values

    main_dir, main_vals = _ifd(main + [(0x8825, 4, 0)], 8)
    gps_offset = 8 + len(main_dir) + len(main_vals)
    main_dir, main_vals = _ifd(main + [(0x8825, 4, gps_offset)], 8)
    gps_dir, gps_vals = _ifd(gps, gps_offset)
    return header + main_dir + main_vals + gps_dir + gps_vals


def _jpeg(tiff: bytes) -> bytes:
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"


NIKON = [(0x010F, 2, "NIKON"), (0x0110, 2, "COOLPIX P6000"), (0x9003, 2, "2008:10:22 16:28:39")]
FLORENCE_GPS = [
    (0x0001, 2, "N"),
    (0x0002, 5, [(43, 1), (28, 1), (281, 100)]),
    (0x0003, 2, "E"),
    (0x0004, 5, [(11, 1), (53, 1), (646, 100)]),
]


def test_jpeg_gps_becomes_decimal_coordinates(tmp_path: Path):
    photo = tmp_path / "geotagged.jpg"
    photo.write_bytes(_jpeg(_tiff(NIKON, FLORENCE_GPS)))

    tags = read_exif(photo)

    assert camera(tags) == "NIKON COOLPIX P6000"
    latitude, longitude = coordinates(tags)
    assert round(latitude, 4) == 43.4674
    assert round(longitude, 4) == 11.8851


def test_southern_and_western_hemispheres_are_negative(tmp_path: Path):
    photo = tmp_path / "south.jpg"
    photo.write_bytes(
        _jpeg(
            _tiff(
                NIKON,
                [
                    (0x0001, 2, "S"),
                    (0x0002, 5, [(33, 1), (0, 1), (0, 1)]),
                    (0x0003, 2, "W"),
                    (0x0004, 5, [(70, 1), (0, 1), (0, 1)]),
                ],
            )
        )
    )

    assert coordinates(read_exif(photo)) == (-33.0, -70.0)


def test_out_of_range_coordinates_are_rejected(tmp_path: Path):
    photo = tmp_path / "bogus.jpg"
    photo.write_bytes(
        _jpeg(
            _tiff(
                NIKON,
                [
                    (0x0001, 2, "N"),
                    (0x0002, 5, [(200, 1), (0, 1), (0, 1)]),
                    (0x0003, 2, "E"),
                    (0x0004, 5, [(10, 1), (0, 1), (0, 1)]),
                ],
            )
        )
    )

    assert coordinates(read_exif(photo)) is None


def test_gps_reaches_the_origin(tmp_path: Path):
    photo = tmp_path / "geotagged.jpg"
    photo.write_bytes(_jpeg(_tiff(NIKON, FLORENCE_GPS)))

    origin = read_embedded_metadata(photo)

    assert origin.source == "device-metadata"
    assert origin.location.startswith("43.4674")


def test_a_bare_tiff_is_read_directly(tmp_path: Path):
    scan = tmp_path / "scan.tiff"
    scan.write_bytes(_tiff([(0x0131, 2, "Nikon Scan 4.0")]))

    assert read_embedded_metadata(scan).tool == "Nikon Scan 4.0"


def test_webp_exif_chunk(tmp_path: Path):
    tiff = _tiff([(0x010F, 2, "Google"), (0x0110, 2, "Pixel 9")])
    chunk = b"EXIF" + struct.pack("<I", len(tiff)) + tiff
    body = b"WEBP" + b"VP8 " + struct.pack("<I", 4) + b"\x00\x00\x00\x00" + chunk
    image = tmp_path / "photo.webp"
    image.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)

    assert read_embedded_metadata(image).tool == "Google Pixel 9"


# --- PNG text chunks ---------------------------------------------------------


def _png(chunks: list[tuple[bytes, bytes]]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    for kind, payload in chunks:
        out += chunk(kind, payload)
    return out + chunk(b"IDAT", b"\x00") + chunk(b"IEND", b"")


def test_png_software_chunk(tmp_path: Path):
    image = tmp_path / "chart.png"
    image.write_bytes(_png([(b"tEXt", b"Software\x00matplotlib 3.9.0")]))

    assert read_embedded_metadata(image).tool == "matplotlib 3.9.0"


def test_png_generation_parameters_are_reported(tmp_path: Path):
    image = tmp_path / "generated.png"
    image.write_bytes(_png([(b"tEXt", b"parameters\x00a red bicycle, Steps: 30, Model: sdxl")]))

    note = read_embedded_metadata(image).note
    assert "generation parameters recorded" in note
    assert "a red bicycle" in note


def test_png_compressed_text_chunk(tmp_path: Path):
    payload = b"Software\x00\x00" + zlib.compress(b"Adobe Photoshop 25.0")
    image = tmp_path / "edited.png"
    image.write_bytes(_png([(b"zTXt", payload)]))

    assert read_embedded_metadata(image).tool == "Adobe Photoshop 25.0"


# --- ISO base media ----------------------------------------------------------


def _atom(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + kind + payload


def _itunes_text(kind: bytes, text: str) -> bytes:
    raw = text.encode("utf-8")
    data = _atom(b"data", struct.pack(">II", 1, 0) + raw)
    return _atom(kind, data)


def test_mp4_encoder_and_location(tmp_path: Path):
    udta = _atom(
        b"udta",
        _itunes_text(b"\xa9too", "Lavf58.44.100") + _itunes_text(b"\xa9xyz", "+43.4674+011.8851/"),
    )
    video = tmp_path / "clip.mp4"
    video.write_bytes(_atom(b"ftyp", b"isom") + _atom(b"moov", udta))

    origin = read_embedded_metadata(video)

    assert origin.tool == "Lavf58.44.100"
    assert origin.location == "43.4674, 11.8851"


def test_mp4_data_box_does_not_leak_into_the_text(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(
        _atom(b"ftyp", b"isom")
        + _atom(b"moov", _atom(b"udta", _itunes_text(b"\xa9too", "HandBrake")))
    )

    assert read_embedded_metadata(video).tool == "HandBrake"


def test_mp4_camera_make_and_model(tmp_path: Path):
    udta = _atom(
        b"udta", _itunes_text(b"\xa9mak", "Apple") + _itunes_text(b"\xa9mod", "iPhone 15 Pro")
    )
    video = tmp_path / "iphone.mov"
    video.write_bytes(_atom(b"ftyp", b"qt  ") + _atom(b"moov", udta))

    origin = read_embedded_metadata(video)

    assert origin.tool == "Apple iPhone 15 Pro"
    assert origin.source == "device-metadata"


# --- zip and text containers -------------------------------------------------

ODF_META = """<?xml version="1.0"?>
<office:document-meta
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <office:meta>
    <meta:generator>LibreOffice/24.2.7.2$Linux_X86_64</meta:generator>
    <dc:creator>Jan Kowalski</dc:creator>
    <meta:creation-date>2026-02-22T16:15:38</meta:creation-date>
  </office:meta>
</office:document-meta>"""


def test_odf_generator_and_author(tmp_path: Path):
    document = tmp_path / "notes.odt"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("meta.xml", ODF_META)

    origin = read_embedded_metadata(document)

    assert origin.tool == "LibreOffice/24.2.7.2$Linux_X86_64"
    assert origin.at == "2026-02-22T16:15:38Z"
    assert "author Jan Kowalski" in origin.note


def test_epub_package_metadata(tmp_path: Path):
    container = """<?xml version="1.0"?>
    <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
      <rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles>
    </container>"""
    opf = """<?xml version="1.0"?>
    <package xmlns="http://www.idpf.org/2007/opf">
      <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Frankenstein</dc:title>
        <dc:creator>Mary Shelley</dc:creator>
        <dc:date>1993-10-01</dc:date>
      </metadata>
    </package>"""
    book = tmp_path / "book.epub"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)

    origin = read_embedded_metadata(book)

    assert origin.at == "1993-10-01T00:00:00Z"
    assert "author Mary Shelley" in origin.note
    assert "title Frankenstein" in origin.note


def test_rtf_generator(tmp_path: Path):
    document = tmp_path / "letter.rtf"
    document.write_bytes(rb"{\rtf1\ansi{\*\generator Riched20 10.0.19041;}Hello}")

    assert read_embedded_metadata(document).tool == "Riched20 10.0.19041"


def test_svg_inkscape_version(tmp_path: Path):
    drawing = tmp_path / "logo.svg"
    drawing.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        'inkscape:version="1.3.2"><rect width="1" height="1"/></svg>',
        encoding="utf-8",
    )

    assert read_embedded_metadata(drawing).tool == "Inkscape 1.3.2"


def test_svg_without_a_generator(tmp_path: Path):
    drawing = tmp_path / "plain.svg"
    drawing.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")

    assert read_embedded_metadata(drawing) is None


def test_jupyter_notebook_kernel(tmp_path: Path):
    notebook = tmp_path / "analysis.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [],
                "metadata": {
                    "kernelspec": {"display_name": "Python 3"},
                    "language_info": {"name": "python", "version": "3.12.1"},
                },
            }
        ),
        encoding="utf-8",
    )

    assert read_embedded_metadata(notebook).tool == "Jupyter (Python 3, python 3.12.1)"


# --- ID3 ---------------------------------------------------------------------


def test_id3v2_encoder_frame(tmp_path: Path):
    def frame(identifier: bytes, text: str) -> bytes:
        payload = b"\x03" + text.encode("utf-8")
        return identifier + struct.pack(">I", len(payload)) + b"\x00\x00" + payload

    body = frame(b"TSSE", "Lavf58.44.100") + frame(b"TPE1", "Someone")
    size = bytes(((len(body) >> shift) & 0x7F) for shift in (21, 14, 7, 0))
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"ID3\x03\x00\x00" + size + body)

    origin = read_embedded_metadata(audio)

    assert origin.tool == "Lavf58.44.100"
    assert "artist Someone" in origin.note


def test_file_without_an_id3_tag(tmp_path: Path):
    audio = tmp_path / "bare.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00" * 16)

    assert read_embedded_metadata(audio) is None
