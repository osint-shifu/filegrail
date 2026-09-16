"""Build the example report published with the project.

The case is invented on the spot, file by file, because the alternative is to
publish a report made from somebody's real documents: a report carries the
names, addresses and paths its files carry, so an example built from a real
corpus publishes all of them. Every value here is fictional and every domain
is one of the reserved example domains.

The files are real files, written so that the scanner reads them the way it
reads any others: a JPEG with an Exif segment, a PDF carrying an Info
dictionary and an XMP packet that disagree, OOXML property parts, a PNG with a
C2PA manifest naming a generative source, and a download whose origin is in a
file attribute.

    python tools/build_example.py

It writes `docs/example-report.html`, which GitHub Pages serves.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

#: The scan the example is the output of.
_COMMAND = (sys.executable, "-m", "filegrail.cli")
CASE = Path("/tmp/filegrail-example/case")
PAGE = HERE / "docs" / "example-report.html"

#: One fixed camera, so three photographs share a body rather than a model.
BODY = "JX41-0099231"

#: Written into two files to the same second, which is how a batch export reads.
BATCH = "2026-04-07T11:20:04Z"


def _exif(path: Path, make: str, model: str, taken: str, serial: str) -> None:
    """A minimal JPEG carrying Make, Model, DateTimeOriginal and a body serial."""
    entries = [(0x010F, make), (0x0110, model), (0x9003, taken), (0xA431, serial)]
    header = b"MM\x00\x2a" + struct.pack(">I", 8)
    values = b""
    base = 8 + 2 + len(entries) * 12 + 4
    directory = struct.pack(">H", len(entries))
    for tag, text in entries:
        raw = text.encode("ascii") + b"\x00"
        directory += struct.pack(">HHI", tag, 2, len(raw))
        directory += struct.pack(">I", base + len(values))
        values += raw
    app1 = b"Exif\x00\x00" + header + directory + struct.pack(">I", 0) + values
    path.write_bytes(b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9")


def _pdf(path: Path, info: str, xmp: str | None = None) -> None:
    """A PDF with an Info dictionary, and optionally an XMP packet beside it."""
    body = b"%PDF-1.7\n<< " + info.encode("ascii") + b" >>\n"
    if xmp is not None:
        packet = (
            '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
            f"{xmp}</rdf:Description></rdf:RDF></x:xmpmeta>"
            '<?xpacket end="r"?>'
        ).encode()
        body += (
            b"1 0 obj\n<< /Type /Metadata /Subtype /XML /Length "
            + str(len(packet)).encode()
            + b" >>\nstream\n"
            + packet
            + b"\nendstream\nendobj\n"
        )
    path.write_bytes(body)


def _ooxml(path: Path, creator: str, edited_by: str, created: str, application: str) -> None:
    """A document that records who wrote it, in the parts a reader looks at."""
    core = (
        '<?xml version="1.0"?>\n<cp:coreProperties'
        ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:dcterms="http://purl.org/dc/terms/">'
        f"<dc:creator>{creator}</dc:creator>"
        f"<cp:lastModifiedBy>{edited_by}</cp:lastModifiedBy>"
        f"<dcterms:created>{created}</dcterms:created>"
        "</cp:coreProperties>"
    )
    app = (
        '<?xml version="1.0"?>\n<Properties'
        ' xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        f"<Application>{application}</Application><AppVersion>16.0000</AppVersion>"
        "<Company>Northwind Survey Ltd</Company></Properties>"
    )
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("docProps/core.xml", core)
        bundle.writestr("docProps/app.xml", app)


def _generated(path: Path) -> None:
    """A PNG whose Content Credentials name a generative source.

    The manifest writer lives with the tests that pin the format; duplicating a
    JUMBF and CBOR encoder here would give the example a second one to keep
    right.
    """
    sys.path.insert(0, str(HERE / "tests"))
    from test_c2pa import GENERATED_CLAIM, _manifest, _png_with  # noqa: PLC0415

    _png_with(path, _manifest(GENERATED_CLAIM))


def _origin(path: Path, url: str, referrer: str) -> bool:
    """Where a download came from, as the desktop records it on the file itself."""
    if not hasattr(os, "setxattr"):
        return False
    try:
        os.setxattr(str(path), "user.xdg.origin.url", url.encode("utf-8"))
        os.setxattr(str(path), "user.xdg.referrer.url", referrer.encode("utf-8"))
    except OSError:
        return False
    return True


def _stamp(path: Path, moment: str) -> None:
    when = datetime.strptime(moment, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    os.utime(path, (when.timestamp(), when.timestamp()))


def build() -> Path:
    """Write the case, and return the directory it is in."""
    shutil.rmtree(CASE.parent, ignore_errors=True)
    (CASE / "photos").mkdir(parents=True)
    (CASE / "documents").mkdir()
    (CASE / "downloads").mkdir()

    for number, taken in enumerate(
        ("2026:04:05 08:12:44", "2026:04:05 08:13:01", "2026:04:06 17:41:09"), 1
    ):
        photo = CASE / "photos" / f"harbour_{number:02d}.jpg"
        _exif(photo, "NIKON CORPORATION", "COOLPIX P950", taken, BODY)
        _stamp(photo, BATCH if number < 3 else "2026-04-08T09:02:11Z")

    for name in ("survey_report.docx", "annex_a.docx", "annex_b.docx"):
        document = CASE / "documents" / name
        _ooxml(document, "R. Mazur", "k.dabrowa", "2026-03-30T14:05:00Z", "Microsoft Office Word")
        _stamp(document, BATCH)

    invoice = CASE / "documents" / "invoice_2214.pdf"
    _pdf(
        invoice,
        "/Producer (LibreOffice 7.6) /Creator (Writer) "
        "/CreationDate (D:20260211184002+01'00') /ModDate (D:20260211163315+01'00')",
        "<xmp:CreatorTool>Adobe Illustrator 27.2</xmp:CreatorTool>"
        "<xmp:CreateDate>2025-11-03T10:22:00+01:00</xmp:CreateDate>",
    )
    _stamp(invoice, "2026-02-11T17:40:02Z")

    _generated(CASE / "photos" / "render_final.png")
    _stamp(CASE / "photos" / "render_final.png", "2026-04-09T22:07:19Z")

    brief = CASE / "downloads" / "press_brief.pdf"
    _pdf(brief, "/Producer (Skia/PDF m124) /CreationDate (D:20260401091500+00'00')")
    _origin(brief, "https://files.example.org/press/brief.pdf", "https://portal.example.org/press/")
    _stamp(brief, "2026-04-01T09:15:00Z")

    contacts = CASE / "documents" / "contacts.csv"
    contacts.write_text(
        "name,contact,profile,note\n"
        "R. Mazur,press@example.org,https://social.example.net/@rmazur,"
        "spoke at the April briefing\n"
        "K. Dabrowa,k.dabrowa@example.org,https://social.example.net/@kdabrowa,"
        "signed the annex\n"
        "Northwind Survey Ltd,office@example.com,https://portal.example.org/press/,"
        "publisher of the brief\n",
        encoding="utf-8",
    )
    _stamp(contacts, "2026-04-02T12:00:00Z")

    quiet = CASE / "downloads" / "notes.txt"
    quiet.write_text("no metadata, no trace, nothing to say\n", encoding="utf-8")
    _stamp(quiet, "2026-03-01T08:00:00Z")
    return CASE


def main() -> int:
    case = build()
    written = case.parent / "example-report.html"
    run = subprocess.run(
        [*_COMMAND, str(case), "--content", "--html", "-o", str(written)],
        cwd=HERE,
        env={**os.environ, "PYTHONPATH": str(HERE / "src")},
    )
    if run.returncode != 0:
        return run.returncode
    PAGE.write_text(written.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"{PAGE} - {PAGE.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
