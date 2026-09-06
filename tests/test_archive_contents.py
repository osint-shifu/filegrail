"""Metadata from the files inside an archive, without unpacking it.

An archive already tells the scan what it contains by name and size. What it
also contains is metadata - a photograph in a zip has the same EXIF it would
have on disk - and none of it was being read.

The claim is about the archive, and that is the whole difficulty. A photograph
taken in 2008 inside a zip made in 2024 does not date the zip, and its GPS fix
is not the zip's location, so neither is carried anywhere that would present it
as a property of the container.
"""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

from filegrail.models import METADATA, EvidenceRecord, category
from filegrail.scan import scan
from filegrail.sources.archives import _about_the_archive, read_contents
from tests.photo import jpeg_with_exif

#: A minimal XMP packet, stored uncompressed inside the archive so that a
#: reader sweeping the container's own bytes would find it there.
PACKET = (
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
    b"<xmp:CreatorTool>Adobe Photoshop</xmp:CreatorTool>"
    b"</rdf:Description></rdf:RDF></x:xmpmeta>"
)


def _zip_of(tmp_path: Path, name: str = "holiday.jpg") -> Path:
    photo = tmp_path / "source.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.write(photo, name)
    return archive


def test_a_photograph_inside_a_zip_is_read(tmp_path: Path):
    origins = read_contents(_zip_of(tmp_path))

    assert len(origins) == 1
    assert origins[0].fields["Model"] == "COOLPIX P6000"


def test_the_member_it_came_from_is_named(tmp_path: Path):
    origins = read_contents(_zip_of(tmp_path, "images/holiday.jpg"))

    assert "images/holiday.jpg" in origins[0].note


def test_the_archive_is_not_dated_by_what_is_inside_it(tmp_path: Path):
    """A photograph from 2008 in a zip made last week does not date the zip,
    and an origin carrying that moment would put the archive on the timeline
    sixteen years before it existed."""
    origin = read_contents(_zip_of(tmp_path))[0]

    assert origin.at is None
    assert "2008" in origin.fields["DateTime"]


def test_it_is_a_claim_about_the_container(tmp_path: Path):
    origin = read_contents(_zip_of(tmp_path))[0]

    assert category(origin) == METADATA
    assert origin.priority > 0


def test_a_tar_is_read_the_same_way(tmp_path: Path):
    photo = tmp_path / "source.jpg"
    jpeg_with_exif(photo, "Canon", "Canon EOS 5D", "2026:04:19 21:43:48")
    archive = tmp_path / "pack.tar"
    with tarfile.open(archive, "w") as bundle:
        bundle.add(photo, arcname="holiday.jpg")

    assert read_contents(archive)[0].fields["Model"] == "Canon EOS 5D"


def test_members_no_reader_claims_are_skipped(tmp_path: Path):
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("notes.txt", "nothing here")

    assert read_contents(archive) == []


def test_something_that_is_not_an_archive(tmp_path: Path):
    plain = tmp_path / "plain.zip"
    plain.write_bytes(b"not a zip")

    assert read_contents(plain) == []


def test_a_packet_belonging_to_a_member_is_not_the_archives_own(tmp_path: Path):
    """The readers that sweep raw bytes for a block - XMP, IPTC - find the
    member's inside the container and, before the members were read, that was
    the only signal there was. It was never the archive's own claim: a zip is
    not made by Photoshop. Now that the member carrying it is read under its
    own name, repeating it as the container's would be wrong twice over."""
    case = tmp_path / "case"
    case.mkdir()
    photo = tmp_path / "source.jpg"
    jpeg_with_exif(photo, "NIKON", "COOLPIX P6000", "2008:10:22 16:28:39")
    # A packet the sweep would find in the container's raw bytes if it looked.
    photo.write_bytes(photo.read_bytes() + PACKET)
    with zipfile.ZipFile(case / "pack.zip", "w") as bundle:
        bundle.write(photo, "holiday.jpg", compress_type=zipfile.ZIP_STORED)

    record = next(iter(scan(case, use_shell_history=False)))
    sources = {origin.source for origin in record.evidence}

    assert "archive-content" in sources
    assert not sources & {"xmp", "iptc"}


def test_a_members_fix_is_not_the_archives_location():
    """Where the member carried coordinates, they are the member's. Left on the
    restated claim they would read as a place the archive was, and a zip has
    never been anywhere. They keep saying what they say, in the fields."""
    member = EvidenceRecord(
        source="device-metadata",
        block="exif",
        at="2008-10-22T16:28:39Z",
        geo="43.467448, 11.885127",
    )

    restated = _about_the_archive(member, "trip/holiday.jpg")

    assert restated.geo is None
    assert restated.at is None
    assert restated.fields["location"] == "43.467448, 11.885127"
