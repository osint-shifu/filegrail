"""Do the acquisition records agree with each other?

One record is a claim. Two records that agree are corroboration. Two that
disagree are a finding in their own right - a file downloaded twice, a file
copied after acquisition, or origin metadata that was replaced - and a report
that silently prints the higher-scoring one has destroyed the finding.
"""

from __future__ import annotations

from pathlib import Path

from filetrail.models import FileRecord, Origin
from filetrail.reconcile import (
    AGREEMENT,
    ATTRIBUTION_CONFLICT,
    CONFLICT,
    NONE,
    PARTIAL,
    SINGLE,
    reconcile,
)
from filetrail.report import render_text
from filetrail.theme import Theme

PLAIN = Theme(colour=False, unicode=True, width=88)


def _record(*origins: Origin, mtime: str = "2026-08-24T19:00:00Z") -> FileRecord:
    record = FileRecord(path="/case/a.pdf", size=4096, mtime=mtime)
    record.origins.extend(origins)
    return record


def _download(url: str, **extra) -> Origin:
    return Origin(source="browser-download", url=url, tool="firefox", **extra)


def _zone(url: str, **extra) -> Origin:
    return Origin(source="windows-zone-identifier", url=url, **extra)


# --- the verdict -------------------------------------------------------------


def test_no_acquisition_record_at_all():
    verdict = reconcile(_record(Origin(source="device-metadata", tool="Canon")))

    assert verdict.state == NONE


def test_one_record_is_not_corroboration():
    """A single source is the ordinary case, and not a finding either way."""
    verdict = reconcile(_record(_download("https://example.org/a.pdf")))

    assert verdict.state == SINGLE


def test_two_records_naming_the_same_url_agree():
    verdict = reconcile(
        _record(_download("https://example.org/a.pdf"), _zone("https://example.org/a.pdf"))
    )

    assert verdict.state == AGREEMENT
    assert "browser download" in " ".join(verdict.reasons)


def test_trivial_url_differences_still_agree():
    """A trailing slash and a capitalised host are the same address."""
    verdict = reconcile(
        _record(_download("https://Example.ORG/a.pdf"), _zone("https://example.org/a.pdf/"))
    )

    assert verdict.state == AGREEMENT


def test_the_same_host_by_a_different_path_is_partial():
    verdict = reconcile(
        _record(_download("https://example.org/a.pdf"), _zone("https://example.org/copy/a.pdf"))
    )

    assert verdict.state == PARTIAL
    assert "example.org" in " ".join(verdict.reasons)


def test_different_hosts_conflict():
    verdict = reconcile(
        _record(_download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf"))
    )

    assert verdict.state == CONFLICT
    reasons = " ".join(verdict.reasons)
    assert "example.com" in reasons
    assert "mirror.example.net" in reasons


def test_a_file_claiming_to_predate_nothing_is_unremarkable():
    """Created before it was downloaded is the normal order of events."""
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf", at="2026-08-24T19:02:11Z"),
            Origin(source="document-metadata", tool="Word", at="2026-08-01T10:00:00Z"),
        )
    )

    assert verdict.state == SINGLE
    assert not verdict.reasons


def test_a_file_claiming_to_postdate_its_download_is_flagged():
    """The bytes cannot have been authored after they arrived."""
    verdict = reconcile(
        _record(
            _download("https://example.org/a.pdf", at="2026-08-01T10:00:00Z"),
            Origin(source="document-metadata", tool="Word", at="2026-08-24T19:02:11Z"),
        )
    )

    assert any("after" in reason for reason in verdict.reasons)


def test_a_name_only_match_is_called_out():
    origin = _download("https://example.org/a.pdf")
    origin.note = "matched by file name; the file was moved or renamed since download"

    verdict = reconcile(_record(origin))

    assert any("name" in reason for reason in verdict.reasons)


# --- what the report shows ---------------------------------------------------


def test_a_single_source_gets_no_verdict_line():
    """The common case must not be annotated, or the annotation means nothing."""
    output = render_text(
        [_record(_download("https://example.org/a.pdf"))], Path("/case"), theme=PLAIN
    )

    assert "agreement" not in output
    assert "conflict" not in output


def test_a_conflict_is_reported():
    record = _record(
        _download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf")
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "conflict" in output


def test_a_conflict_shows_both_records_without_verbose():
    """A verdict that refers to evidence the report hid is not a verdict."""
    record = _record(
        _download("https://example.com/a.pdf"), _zone("https://mirror.example.net/a.pdf")
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "example.com/a.pdf" in output
    assert "mirror.example.net/a.pdf" in output


def test_agreement_is_reported_too():
    record = _record(_download("https://example.org/a.pdf"), _zone("https://example.org/a.pdf"))

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "agreement" in output


# --- what the file says about itself, said twice ------------------------------


def _iptc(**fields: str) -> Origin:
    return Origin(source="iptc", fields=dict(fields))


def _xmp(**fields: str) -> Origin:
    return Origin(source="xmp", fields={name.replace("_", ":"): v for name, v in fields.items()})


def _exif(**fields: str) -> Origin:
    return Origin(source="device-metadata", fields=dict(fields))


def test_a_camera_and_its_xmp_mirror_naming_different_models_is_a_finding():
    """The `tiff:` properties are the XMP serialisation of the EXIF tags - the
    specification says so - which is what makes them comparable at all. Two
    different cameras in one file is one of them having been rewritten."""
    record = _record(
        _exif(Make="Canon", Model="Canon PowerShot G9"),
        _xmp(tiff_Make="NIKON CORPORATION", tiff_Model="NIKON D700"),
    )

    findings = reconcile(record).findings

    assert [f.kind for f in findings] == [ATTRIBUTION_CONFLICT, ATTRIBUTION_CONFLICT]
    assert "device metadata says Canon" in findings[0].text
    assert "XMP says NIKON CORPORATION" in findings[0].text


def test_a_camera_agreeing_with_its_mirror_says_nothing():
    record = _record(
        _exif(Make="Canon", Model="Canon PowerShot G9"),
        _xmp(tiff_Make="Canon", tiff_Model="Canon PowerShot G9"),
    )

    assert reconcile(record).findings == []


def test_a_zoneless_tag_agrees_with_its_zoned_mirror():
    """EXIF writes no zone and the XMP mirror writes the same clock reading with
    one attached. Reading the tag as UTC and the mirror as an instant would make
    every photograph taken outside Greenwich contradict itself."""
    record = _record(
        _exif(DateTimeOriginal="2004:08:27 13:52:55"),
        _xmp(exif_DateTimeOriginal="2004-08-27T13:52:55+02:00"),
    )

    assert reconcile(record).findings == []


def test_a_capture_time_moved_to_another_day_is_a_finding():
    record = _record(
        _exif(DateTimeOriginal="2004:08:27 13:52:55"),
        _xmp(exif_DateTimeOriginal="2004-08-28T13:52:55+02:00"),
    )

    assert [f.kind for f in reconcile(record).findings] == [ATTRIBUTION_CONFLICT]


def test_a_bare_iim_day_agrees_with_a_full_xmp_stamp():
    """IIM records the day in one dataset and the clock in another, so its date
    field is eight digits. A day that agrees is not a conflict merely because
    the other writer also wrote down a time."""
    record = _record(
        _iptc(DateCreated="20190304"),
        _xmp(photoshop_DateCreated="2019-03-04T10:22:31+01:00"),
    )

    assert reconcile(record).findings == []


def test_exposure_settings_are_left_out_of_the_comparison():
    """XMP writers put units, rationals and comma decimals in these - "f/5,6"
    against 5.6, "1/500 sec." against 0.002 - and a comparison that cannot read
    them would report a conflict on almost every photograph ever taken."""
    record = _record(
        _exif(FNumber="5.6", ExposureTime="0.002", FocalLength="105"),
        _xmp(exif_FNumber="f/5,6", exif_ExposureTime="1/500 sec.", exif_FocalLength="105,0 mm"),
    )

    assert reconcile(record).findings == []


def test_two_self_descriptions_disagreeing_about_the_byline_is_a_finding():
    """IIM and XMP hold the same facts, and tools maintain the XMP while leaving
    the IIM block as they found it. Two different photographers in one file is
    not a formatting difference - it is the trace of an attribution being
    changed, and printing both without a word leaves the reader to notice."""
    record = _record(
        _iptc(**{"By-line": "Francisco Gonzalez", "Credit": "Reuters"}),
        _xmp(dc_creator="Marta Nowak", photoshop_Credit="Agencja Wschod"),
    )

    findings = reconcile(record).findings

    assert [f.kind for f in findings] == [ATTRIBUTION_CONFLICT, ATTRIBUTION_CONFLICT]
    assert "IPTC says Francisco Gonzalez" in findings[0].text
    assert "XMP says Marta Nowak" in findings[0].text
    assert "By-line" in findings[0].text


def test_two_self_descriptions_that_agree_are_not_a_finding():
    """One editor writes both blocks at once and keeps them consistent, so
    agreement here is the common case. Annotating it would put a line on almost
    every photograph, and a line on everything says nothing."""
    record = _record(
        _iptc(**{"By-line": "Ansel Adams", "Credit": "Magnum"}),
        _xmp(dc_creator="ansel  adams", photoshop_Credit="Magnum"),
    )

    assert reconcile(record).findings == []


def test_a_contested_attribution_is_not_labelled_by_the_acquisition_state():
    """`state` describes how the acquisition records relate. Printing it over a
    finding that came from somewhere else labels one thing with the name of
    another - and "no acquisition record", in the colour of good news, is a
    strange headline for two photographers contradicting each other."""
    record = _record(
        _iptc(**{"By-line": "Francisco Gonzalez"}),
        _xmp(dc_creator="Marta Nowak"),
    )

    output = render_text([record], Path("/case"), theme=PLAIN)

    assert "contested attribution" in output
    assert "no acquisition record" not in output


def test_a_contested_attribution_brings_both_self_descriptions_on_screen():
    """The report shows one intrinsic claim, the strongest. A finding that names
    IPTC while the report prints only the XMP is a verdict about evidence the
    reader cannot see - the same reason a conflicting acquisition record is
    brought forward."""
    iptc = _iptc(**{"By-line": "Francisco Gonzalez"})
    iptc.tool = "Adobe Photoshop 7.0"
    xmp = _xmp(dc_creator="Marta Nowak")
    xmp.tool = "darktable 4.6.1"

    output = render_text([_record(iptc, xmp)], Path("/case"), theme=PLAIN)

    # The tool heads a rendered claim and appears nowhere in a finding's text,
    # so seeing both is seeing both claims rather than one claim and a quotation.
    assert "Adobe Photoshop 7.0" in output
    assert "darktable 4.6.1" in output
