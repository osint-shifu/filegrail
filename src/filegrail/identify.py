"""Identifiers found in the metadata a scan already read.

The detectors here are ported from DirSifu (MIT, same author), which arrived at
them by finding out what a regex sweep actually costs. Six types, each one
recognisable with high precision and normalisable without guessing: email, url,
domain, ipv4, cryptographic hash and geographic coordinate.

Deliberately **not** detected, with reasons, because a noisy identifier list is
worse than a short one:

* **phone numbers** - without a phone-number library and a region hint the false
  positive rate is ruinous: invoice numbers, order ids, timestamps, version
  strings and partial hashes all match.
* **dates** - a sweep yields thousands of meaningless hits, and the dates that
  matter here already arrive as a claim's timestamp.
* **IPv6** - high false-positive rate against code (``::``).

What differs from DirSifu is the corpus. DirSifu reads document text; this reads
what files record **about themselves** - an author line, a company, a template
path, a producing URL, a camera's GPS fix - which is exactly where identifiers a
document body never mentions turn out to live. That corpus is short strings
rather than prose, so precision costs less here than it does there.

Document text is available too, under `content=True`, and it is kept as its own
corpus rather than merged: the precision argument above is the reason, and
telling the two apart is what makes the answer worth having. A name in a
document is a lead. A name in a document that the record of the file's *arrival*
also carries was put there twice, by separate acts - and nothing that reads only
one corpus can say so.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from .models import ACQUISITION, FileRecord, kind

#: What files record about themselves: the corpus this has always read, and the
#: one the detectors were tuned for. Short structured strings, where a match is
#: nearly always a real identifier.
METADATA = "metadata"

#: What files say. Read only when asked, and kept as its own corpus rather than
#: merged into the one above: prose is an order of magnitude noisier - a
#: citation, a file name, an abbreviation with a dot in it all match something -
#: and letting that into the metadata list would drown the half that is reliable.
CONTENT = "content"


class _Text(NamedTuple):
    """One string to search, with everything needed to say where it came from."""

    file: str
    where: str
    text: str
    corpus: str

    #: Whether the origin this came from is a record of how the file arrived.
    #: Meaningless for content, which records nothing.
    acquired: bool


#: Occurrences are counted exactly; the sampled list of places is capped so one
#: value repeated across a huge tree cannot dominate the output.
MAX_SAMPLES = 20

#: How a file and the field it was found in are joined into one place
#: string. It goes into `--json` in exactly this form, so it is a constant
#: rather than a literal in two places - and the report re-renders the
#: separator with whatever the terminal can actually print.
PLACE = " · "

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@([A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+)\b"
)
URL_RE = re.compile(r"\bhttps?://[^\s<>\"'`\](){}]+", re.IGNORECASE)
IPV4_RE = re.compile(r"(?<![\w.\-])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.\-])")
HASH_RE = re.compile(
    r"(?<![A-Za-z0-9\-])([A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})(?![A-Za-z0-9\-])"
)
DOMAIN_RE = re.compile(
    r"(?<![\w.@\-/\\])"
    r"((?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,})"
    r"(?![\w\-])"
)

#: A bare ``name.ext`` token that is far more likely to be a file than a host.
#: Every one of these suffixes is also a real TLD, so a suffix blocklist alone
#: cannot decide it - the shape of the whole token has to be considered.
FILE_LIKE_RE = re.compile(
    r"^[a-z_][a-z0-9_\-]*\.(?:md|py|js|mjs|cjs|ts|tsx|jsx|json|txt|yml|yaml|sh|bash|zsh"
    r"|go|rs|css|html|htm|xml|csv|log|toml|ini|cfg|conf|lock|sql|rb|php|java|kt|swift"
    r"|c|h|cpp|hpp|cs|pl|lua|r|vue|svelte|proto|graphql|map|so|db|bak|tmp|zip|gz|tar"
    r"|doc|docx|xls|xlsx|ppt|pptx|pdf|jpg|jpeg|png|gif|tif|tiff|heic|mp4|mp3|dotm)$",
    re.IGNORECASE,
)

_DEC = r"[-+]?\d{1,3}(?:\.\d+)?"

#: Ordered, and the order is the precision ranking: an earlier pattern claims
#: its span so a later, looser one cannot re-read the same text.
COORDINATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("geo_uri", re.compile(rf"\bgeo:({_DEC}),\s*({_DEC})")),
    (
        "map_url",
        re.compile(
            rf"(?:/maps/@|[?&]q=|[?&]ll=|[?&]mlat=|#map=\d+/)({_DEC})[,/]\s*({_DEC})",
            re.IGNORECASE,
        ),
    ),
    (
        "dms",
        re.compile(
            r"(\d{1,3})\s*[°º]\s*(\d{1,2})\s*['′]\s*(\d{1,2}(?:\.\d+)?)?\s*[\"″]?\s*"
            r"([NnSs])[,;\s]+"
            r"(\d{1,3})\s*[°º]\s*(\d{1,2})\s*['′]\s*(\d{1,2}(?:\.\d+)?)?\s*[\"″]?\s*"
            r"([EeWw])"
        ),
    ),
    (
        "hemisphere",
        re.compile(rf"({_DEC})\s*[°º]?\s*([NnSs])[,;\s]+({_DEC})\s*[°º]?\s*([EeWw])"),
    ),
    (
        "labelled",
        re.compile(
            # [^\w+-] rather than \W for the separators: \W is greedy over the
            # sign, so "Longitude: -74.0060" silently yielded +74.0060 - a
            # coordinate in the wrong hemisphere, which is worse than none.
            rf"(?i)\blat(?:itude)?\b[^\w+-]{{0,4}}({_DEC})"
            rf"[^\w+-]{{1,12}}?\blon(?:g|gitude)?\b[^\w+-]{{0,4}}({_DEC})"
        ),
    ),
)

_TRAILING_PUNCT = ".,;:!?'\"`)]}>"

#: A coordinate this tool decoded itself, from EXIF or an ISO 6709 atom, is not
#: a string that has to earn belief - it arrived as a pair of numbers in a field
#: that means latitude and longitude.
_TRUSTED_COORDINATE_FIELDS = frozenset({"geo"})

#: Fields that name a piece of software. This corpus is *made* of version
#: strings - `LibreOffice/24.2.7.2$Linux_X86_64` is the commonest value in it -
#: and a dotted quad or a forty-character build hash inside one is never an
#: address or a document digest. DirSifu could not make this call because it
#: reads prose; here the field name is known, so it can.
#: Fields holding a message identifier. RFC 5322 builds one to the same shape
#: as a mailbox - `<id@domain>` - so it matches every test for an address, and
#: nobody can write to it. A lead nobody can follow is worse than no lead.
_MESSAGE_ID_FIELDS = frozenset({"message-id", "in-reply-to", "references", "content-id"})

_SOFTWARE_FIELDS = frozenset(
    {
        "tool",
        "software",
        "producer",
        "creator",
        "application",
        "appversion",
        "generator",
        "encoder",
        "template",
        "lastmodifiedby",
        # XMP's own names for the same thing, plus the version properties it
        # adds. `exif:GPSVersionID` is 2.2.0.0 in almost every photograph ever
        # geotagged, and it has never been an address.
        "creatortool",
        "softwareagent",
        "gpsversionid",
        "exifversion",
        "flashpixversion",
    }
)


@dataclass(slots=True)
class Identifier:
    """One value, everywhere it was seen."""

    type: str
    value: str
    normalized: str
    count: int = 0
    files: int = 0
    private: bool | None = None
    where: list[str] = field(default_factory=list)

    #: Which corpora it was seen in. Both is the interesting answer: the value
    #: was written into the document and recorded about it, by two separate
    #: acts, and neither one alone says that.
    corpora: set[str] = field(default_factory=set)

    #: Whether one of the places was a record of how the file arrived - a
    #: download address, a referrer, a quarantine event. A value a document
    #: names that its own arrival record also names is a link rather than a
    #: coincidence, and it is the whole reason for reading content at all.
    acquired: bool = False

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "type": self.type,
            "value": self.value,
            "normalized": self.normalized,
            "count": self.count,
            "files": self.files,
            "corpora": sorted(self.corpora),
            "acquired": self.acquired,
            "where": self.where,
        }
        if self.private is not None:
            data["private"] = self.private
        return data


# --- normalisation -----------------------------------------------------------


@lru_cache(maxsize=1)
def known_tlds() -> frozenset[str]:
    """The bundled IANA top-level domain list, lowercased."""
    path = Path(__file__).parent / "data" / "tlds.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(
        line.strip().lower() for line in lines if line.strip() and not line.startswith("#")
    )


def normalize_domain(host: str) -> str | None:
    cleaned = host.strip().strip(".").lower()
    if not cleaned or "." not in cleaned:
        return None
    with suppress(UnicodeError, UnicodeDecodeError):
        cleaned = cleaned.encode("idna").decode("ascii")
    if cleaned.rsplit(".", 1)[-1] not in known_tlds():
        return None
    return cleaned


def normalize_url(raw: str) -> tuple[str, str | None] | None:
    """Return ``(normalised_url, host)`` or None when unusable.

    ``SplitResult`` is lazy: :func:`urlsplit` itself rarely raises, but reading
    ``.port`` parses the netloc and raises on anything that is not a number in
    range. Real data contains things like ``http://localhost:1420$``, so every
    attribute read sits inside the guard, not just the parse.
    """
    cleaned = raw.rstrip(_TRAILING_PUNCT)
    try:
        parts = urlsplit(cleaned)
        if not parts.scheme or not parts.hostname:
            return None
        host = parts.hostname.lower()
        port = parts.port
        path = parts.path.rstrip("/") if parts.path != "/" else ""
        query = parts.query
    except ValueError:
        return None
    netloc = host if port is None else f"{host}:{port}"
    normalized = f"{parts.scheme.lower()}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized, normalize_domain(host)


def _dms(degrees: str, minutes: str, seconds: str | None, hemisphere: str) -> float:
    value = float(degrees) + float(minutes) / 60 + (float(seconds) if seconds else 0.0) / 3600
    return -value if hemisphere.upper() in {"S", "W"} else value


def find_coordinates(text: str) -> list[tuple[str, float, float, str]]:
    """Every coordinate literally written in `text`, as (raw, lat, lon, pattern).

    A bare pair of decimals is never accepted, however many places it carries:
    an SVG path, a CSV of measurements and a version tuple all look exactly like
    one. A coordinate has to arrive with a hemisphere letter, a degree symbol, a
    ``geo:`` scheme, a map URL or an explicit latitude label to be believed.
    """
    found: list[tuple[str, float, float, str]] = []
    claimed: list[tuple[int, int]] = []

    for name, pattern in COORDINATE_PATTERNS:
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in claimed):
                continue
            groups = match.groups()
            try:
                if name == "dms":
                    latitude = _dms(groups[0], groups[1], groups[2], groups[3])
                    longitude = _dms(groups[4], groups[5], groups[6], groups[7])
                elif name == "hemisphere":
                    latitude = float(groups[0]) * (-1 if groups[1].upper() == "S" else 1)
                    longitude = float(groups[2]) * (-1 if groups[3].upper() == "W" else 1)
                else:
                    latitude, longitude = float(groups[0]), float(groups[1])
            except (TypeError, ValueError):
                continue
            if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                continue
            # Null Island is a default, a placeholder or a parse failure.
            if abs(latitude) < 1e-9 and abs(longitude) < 1e-9:
                continue
            claimed.append(span)
            found.append((match.group(0).strip(), latitude, longitude, name))
    return found


def _looks_like_version(text: str, start: int) -> bool:
    """``v1.2.3.4`` is a version string, not an address."""
    return start > 0 and text[start - 1] in "vV"


# --- the corpus --------------------------------------------------------------


def _texts(records: list[FileRecord], *, content: bool = False) -> Iterator[_Text]:
    """Yield every string a scan can search, and where each one came from.

    The field name travels with the value because an identifier without its
    source is a lead nobody can check.

    `content` adds what the documents themselves say. It is off by default and
    costs an open, a decode and a parse per file - the metadata was already in
    hand, and this is not.
    """
    if content:
        # Imported here rather than at the top: reading bodies pulls in the
        # container readers, and a scan that was not asked for them should not
        # pay to import them.
        from .sources.content import read_passages
    for record in records:
        name = Path(record.path).name
        for origin in record.origins:
            arrival = kind(origin) == ACQUISITION
            for label, value in (
                ("url", origin.url),
                ("referrer", origin.referrer),
                ("command", origin.command),
                ("tool", origin.tool),
                ("note", origin.note),
                ("geo", origin.geo),
                ("location", origin.location),
            ):
                if value:
                    yield _Text(name, label, value, METADATA, arrival)
            for label, value in origin.fields.items():
                if value:
                    yield _Text(name, label, str(value), METADATA, arrival)
        if content:
            # One yield per passage rather than one per file. Scanning them
            # apart is what lets a value carry the line, slide or chapter it
            # was on, and it costs about a fifth more than scanning the
            # document as one string.
            for passage in read_passages(Path(record.path)) or ():
                yield _Text(name, passage.place, passage.text, CONTENT, False)


def extract(records: list[FileRecord], *, content: bool = False) -> list[Identifier]:
    """Every identifier in what the scan read, deduplicated across files.

    `content` widens the corpus from what the files record about themselves to
    what they say. The two are kept apart on each entry rather than merged, so
    a reader can tell a name in a document from a name in a download record -
    and see where one value is both.
    """
    found: dict[tuple[str, str], Identifier] = {}

    for source in _texts(records, content=content):
        origin = f"{source.file}{PLACE}{source.where}"
        for family, raw, normalized, private in _scan(source.text, source.where):
            key = (family, normalized)
            entry = found.get(key)
            if entry is None:
                entry = Identifier(type=family, value=raw, normalized=normalized, private=private)
                found[key] = entry
            entry.count += 1
            entry.corpora.add(source.corpus)
            entry.acquired = entry.acquired or source.acquired
            if origin not in entry.where:
                if len(entry.where) < MAX_SAMPLES:
                    entry.where.append(origin)

    for entry in found.values():
        entry.files = len({place.split(PLACE, 1)[0] for place in entry.where})

    return sorted(found.values(), key=lambda i: (i.type, -i.count, i.normalized))


def _scan(text: str, where: str) -> Iterator[tuple[str, str, str, bool | None]]:
    """Yield (type, raw, normalized, private) for one value."""
    hosts: set[str] = set()

    identifier = where.lower().rpartition(":")[2] in _MESSAGE_ID_FIELDS

    for match in EMAIL_RE.finditer(text):
        host = normalize_domain(match.group(1))
        if host is None:
            continue  # unknown TLD: almost always a false positive
        # The domain is still worth having: a message id names the host that
        # minted it, which is a real fact about where the message was written.
        if not identifier:
            yield "email", match.group(0), match.group(0).lower(), None
        hosts.add(host)

    for match in URL_RE.finditer(text):
        parsed = normalize_url(match.group(0))
        if parsed is None:
            continue
        normalized, host = parsed
        yield "url", match.group(0).rstrip(_TRAILING_PUNCT), normalized, None
        if host:
            hosts.add(host)

    # XMP writes `pdf:Producer` where a PDF writes `Producer`, so the namespace
    # comes off before the name is looked up.
    software = where.lower().rpartition(":")[2] in _SOFTWARE_FIELDS

    for match in IPV4_RE.finditer(text):
        if software or _looks_like_version(text, match.start(1)):
            continue
        try:
            address = ipaddress.IPv4Address(match.group(1))
        except ipaddress.AddressValueError:
            continue
        reserved = address.is_private or address.is_reserved or address.is_loopback
        yield "ipv4", match.group(1), str(address), bool(reserved)

    for raw, latitude, longitude, _pattern in _coordinates(text, where):
        # Five decimal places is about a metre, so two renderings of one fix
        # collapse together while two genuinely different fixes stay apart.
        yield "geo", raw, f"{latitude:.5f},{longitude:.5f}", None

    for match in HASH_RE.finditer(text):
        if software:
            continue  # a build id, not a digest of anything a case cares about
        raw = match.group(1)
        kind = {32: "md5", 40: "sha1", 64: "sha256"}[len(raw)]
        yield kind, raw, raw.lower(), None

    # Domains harvested from URLs and emails are certain. Bare tokens have to
    # clear the TLD list and not look like a file name.
    for host in sorted(hosts):
        yield "domain", host, host, None

    for match in DOMAIN_RE.finditer(text):
        candidate = match.group(1)
        if FILE_LIKE_RE.match(candidate):
            continue
        host = normalize_domain(candidate)
        if host is None or host in hosts:
            continue
        yield "domain", candidate, host, None


def _coordinates(text: str, where: str) -> list[tuple[str, float, float, str]]:
    if where in _TRUSTED_COORDINATE_FIELDS:
        parts = text.split(",")
        if len(parts) == 2:
            try:
                latitude, longitude = float(parts[0]), float(parts[1])
            except ValueError:
                return []
            if abs(latitude) > 1e-9 or abs(longitude) > 1e-9:
                return [(text, latitude, longitude, "decoded")]
        return []
    return find_coordinates(text)
