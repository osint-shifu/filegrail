"""Vorbis comments, as FLAC, Ogg Vorbis and Opus all carry them.

One layout, three containers. FLAC keeps it in a metadata block at the front of
the file; Ogg keeps it in the second packet of the stream, behind a marker that
says which codec is speaking.
"""

from __future__ import annotations

import struct
from pathlib import Path

from filetrail.sources.embedded import read_embedded_metadata
from filetrail.sources.embedded.vorbis import read_comments

VENDOR = b"reference libFLAC 1.4.3 20230623"

#: The block type a comment block declares, reused to build one that must not
#: be read: after the last block, these bytes are audio.
_COMMENT_BLOCK = 4


def comments(vendor: bytes, *entries: bytes) -> bytes:
    block = struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", len(entries))
    for entry in entries:
        block += struct.pack("<I", len(entry)) + entry
    return block


def flac(tmp_path: Path, block: bytes, name: str = "take.flac") -> Path:
    """A FLAC whose stream info is followed by one comment block."""
    path = tmp_path / name
    path.write_bytes(
        b"fLaC"
        + b"\x00"
        + (34).to_bytes(3, "big")
        + b"\x00" * 34
        + b"\x84"  # last block, type 4
        + len(block).to_bytes(3, "big")
        + block
    )
    return path


def ogg(tmp_path: Path, marker: bytes, block: bytes, name: str = "take.ogg") -> Path:
    path = tmp_path / name
    path.write_bytes(b"OggS\x00\x00" + b"\x00" * 21 + b"\x01\xff" + marker + block)
    return path


# --- FLAC --------------------------------------------------------------------


def test_the_encoder_names_the_tool(tmp_path: Path):
    audio = flac(tmp_path, comments(VENDOR, b"ENCODER=Lavf60.16.100", b"DATE=2019-03-04"))

    origin = read_embedded_metadata(audio)

    assert origin.tool == "Lavf60.16.100"
    assert origin.at == "2019-03-04T00:00:00Z"


def test_a_name_is_found_whatever_case_it_was_written_in(tmp_path: Path):
    """The specification says the names are case-insensitive and ffmpeg takes it
    at its word, writing every one of them in lower case. A reader that only
    knows the shouted form finds nothing in most of the files there are."""
    audio = flac(tmp_path, comments(VENDOR, b"encoder=Lavf60.16.100", b"date=2019-03-04"))

    origin = read_embedded_metadata(audio)

    assert origin.tool == "Lavf60.16.100"
    assert origin.at == "2019-03-04T00:00:00Z"


def test_the_name_is_kept_as_the_writer_wrote_it(tmp_path: Path):
    """Case-insensitive to look up, and untouched in the record: shouting a
    studio's own field names back at it is editing the evidence."""
    audio = flac(tmp_path, comments(VENDOR, b"encoder=Lavf", b"original_medium=DAT tape 14"))

    assert "original_medium" in read_embedded_metadata(audio).fields


def test_the_library_stands_in_when_nothing_else_named_itself(tmp_path: Path):
    """The vendor string is written by whatever wrote the file, so it is the
    weaker answer and never the wrong one."""
    audio = flac(tmp_path, comments(VENDOR, b"ARTIST=Studio Quartet"))

    assert read_embedded_metadata(audio).tool == "reference libFLAC 1.4.3 20230623"


def test_the_credited_people_reach_the_note(tmp_path: Path):
    audio = flac(tmp_path, comments(VENDOR, b"ARTIST=Studio Quartet", b"TITLE=Interview take 3"))

    note = read_embedded_metadata(audio).note

    assert "artist Studio Quartet" in note
    assert "title Interview take 3" in note


def test_a_field_nobody_summarises_is_kept_under_its_own_name(tmp_path: Path):
    """The list of names is open: a studio writes whatever it uses, and a reader
    that knows only a fixed set throws away the ones that mattered."""
    audio = flac(tmp_path, comments(VENDOR, b"ENCODER=Lavf", b"ORIGINAL_MEDIUM=DAT tape 14"))

    assert read_embedded_metadata(audio).fields["ORIGINAL_MEDIUM"] == "DAT tape 14"


def test_an_entry_with_no_equals_sign_is_not_a_comment(tmp_path: Path):
    audio = flac(tmp_path, comments(VENDOR, b"ENCODER=Lavf", b"just some bytes"))

    assert "just some bytes" not in str(read_embedded_metadata(audio).fields)


def test_embedded_cover_art_does_not_land_in_the_report(tmp_path: Path):
    """A picture arrives base64-encoded in a comment like any other. It is not
    provenance, and a screenful of it would bury what is."""
    art = b"METADATA_BLOCK_PICTURE=" + b"A" * 8192
    audio = flac(tmp_path, comments(VENDOR, b"ENCODER=Lavf", art))

    fields = read_embedded_metadata(audio).fields

    assert "METADATA_BLOCK_PICTURE" not in fields
    assert fields["ENCODER"] == "Lavf"


# --- Ogg ---------------------------------------------------------------------


def test_an_ogg_vorbis_stream_is_read(tmp_path: Path):
    audio = ogg(tmp_path, b"\x03vorbis", comments(b"Lavf60.16.100", b"ARTIST=Studio Quartet"))

    assert read_comments(audio)["ARTIST"] == "Studio Quartet"


def test_an_opus_stream_is_read(tmp_path: Path):
    audio = ogg(
        tmp_path,
        b"OpusTags",
        comments(b"Lavf60.16.100", b"TITLE=Interview take 3"),
        name="take.opus",
    )

    assert read_comments(audio)["TITLE"] == "Interview take 3"


def test_a_length_running_past_what_was_read_stops_the_parse(tmp_path: Path):
    """Ogg breaks a long comment block across pages and puts a page header in
    between. Reading on past the end of one is how a parser starts reporting
    page headers as though a studio had typed them."""
    block = struct.pack("<I", 4) + b"Lavf" + struct.pack("<I", 2)
    block += struct.pack("<I", 21) + b"ARTIST=Studio Quartet"
    block += struct.pack("<I", 4096) + b"TITLE=cut off here"
    audio = ogg(tmp_path, b"\x03vorbis", block)

    assert read_comments(audio) == {"Vendor": "Lavf", "ARTIST": "Studio Quartet"}


# --- files with nothing to say -----------------------------------------------


def test_the_walk_stops_where_the_metadata_does(tmp_path: Path):
    """The last block says it is the last, and audio follows. Any bytes at all
    can appear in audio, a block header among them, and a walk that reads on
    would report the recording itself as something a studio had typed."""
    audio = tmp_path / "sounds-like-a-block.flac"
    block = comments(b"noise", b"ARTIST=not a comment")
    frames = bytes([_COMMENT_BLOCK]) + len(block).to_bytes(3, "big") + block
    audio.write_bytes(b"fLaC" + b"\x80" + (34).to_bytes(3, "big") + b"\x00" * 34 + frames)

    assert read_comments(audio) is None


def test_a_file_that_is_not_flac_is_not_claimed(tmp_path: Path):
    audio = tmp_path / "misnamed.flac"
    audio.write_bytes(b"RIFF" + b"\x00" * 60)

    assert read_comments(audio) is None
    assert read_embedded_metadata(audio) is None


def test_a_flac_with_no_comment_block_makes_no_claim(tmp_path: Path):
    audio = tmp_path / "bare.flac"
    audio.write_bytes(b"fLaC" + b"\x80" + (34).to_bytes(3, "big") + b"\x00" * 34)

    assert read_embedded_metadata(audio) is None
