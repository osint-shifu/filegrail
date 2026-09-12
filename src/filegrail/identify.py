"""Identifiers found in the metadata a scan already read.

The detectors here are ported from DirSifu (MIT, same author), which arrived at
them by finding out what a regex sweep actually costs. Each type is
recognisable with high precision and normalisable without guessing - by a known
TLD, a checksum, a shape nothing else has, or the label beside it - and the
readme's table of identifier types is the list of them.

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
from email.utils import getaddresses
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from .checksums import bech32_version, is_base58check, is_iban, is_nip, is_onion, is_regon
from .models import ORIGIN, FileRecord, category
from .models import label as source_label
from .redact import PATTERNS as REDACT_PATTERNS
from .redact import fingerprint

#: What files record about themselves: the corpus this has always read, and the
#: one the detectors were tuned for. Short structured strings, where a match is
#: nearly always a real identifier.
IN_METADATA = "metadata"

#: What files say. Read only when asked, and kept as its own corpus rather than
#: merged into the one above: prose is an order of magnitude noisier - a
#: citation, a file name, an abbreviation with a dot in it all match something -
#: and letting that into the metadata list would drown the half that is reliable.
IN_CONTENT = "content"


class _Text(NamedTuple):
    """One string to search, with everything needed to say where it came from."""

    file: str
    source: str
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

#: What the `source` of a value found in a document body is called. The text of
#: a file is not one of the evidence sources - nothing wrote it down about the
#: file - so it is named for what it is.
CONTENT_SOURCE = "content"

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

#: Candidates only: the checksum decides. A legacy or pay-to-script address is
#: base58 with a version character in front; a Bech32 address is `bc1` and its
#: own alphabet, which leaves out `1`, `b`, `i` and `o` so nothing is misread.
BTC_LEGACY_RE = re.compile(r"(?<![A-Za-z0-9])([13][1-9A-HJ-NP-Za-km-z]{25,34})(?![A-Za-z0-9])")
BTC_BECH32_RE = re.compile(
    r"(?<![A-Za-z0-9])(bc1[02-9ac-hj-np-z]{6,87})(?![A-Za-z0-9])", re.IGNORECASE
)

#: Printed in groups of four as often as not, so a space is allowed between
#: any two characters and stripped before the number is checked.
IBAN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30})(?![A-Za-z0-9])")

#: The Polish numbers are taken only beside their label, or behind the `PL`
#: of an EU VAT id: their check digit passes about one random number in
#: eleven, and ten bare digits in a document are an order number far more
#: often than a taxpayer. The label is what makes the checksum worth trusting.
NIP_LABELLED_RE = re.compile(r"\bNIP\b[\s:.#-]*((?:\d[\s-]?){9}\d)", re.IGNORECASE)
NIP_PREFIXED_RE = re.compile(r"(?<![A-Za-z0-9])PL(\d{10})(?![A-Za-z0-9])")
REGON_RE = re.compile(r"\bREGON\b[\s:.#-]*(\d{14}|\d{9})(?!\d)", re.IGNORECASE)

#: A version 3 onion address is 56 base32 characters and its own checksum.
ONION_RE = re.compile(r"(?<![a-z2-7])([a-z2-7]{56})\.onion(?![\w\-])", re.IGNORECASE)

#: Six pairs of hex with one separator throughout, and not a window cut out
#: of something longer - a key fingerprint is the same pairs, sixteen or
#: thirty-two of them.
MAC_RE = re.compile(
    r"(?<![\w:\-])([0-9A-Fa-f]{2}([:\-])(?:[0-9A-Fa-f]{2}\2){4}[0-9A-Fa-f]{2})(?![\w:\-])"
)

#: Neither is a device: one is unset, the other is everybody.
_NOT_A_DEVICE = frozenset({"00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"})

#: An account or group on a Windows machine or domain: the machine's three
#: sub-authorities and a relative id. The short well-known SIDs - `S-1-5-18`
#: is SYSTEM on every Windows there is - identify nothing in particular.
SID_RE = re.compile(r"(?<![\w\-])(S-1-5-21-\d{1,10}-\d{1,10}-\d{1,10}-\d{1,10})(?![\w\-])")

#: A bank identifier code has no checksum, so it is taken only beside its
#: label, and its country has to be one. Eight characters, or eleven with a
#: branch.
BIC_RE = re.compile(
    r"\b(?:BIC|SWIFT)\b(?:\s*(?:code|number))?[\s:.#-]*"
    r"([A-Za-z]{6}[A-Za-z0-9]{2}(?:[A-Za-z0-9]{3})?)(?![\w\-])",
    re.IGNORECASE,
)

#: The credential shapes `--redact` knows by their prefix, taken here as
#: identifiers: a key or a token in a document is a finding. Only the shapes
#: that prove themselves - a vendor prefix, a JWT's three segments - and not
#: the rules that go by the name beside a value, which stay redaction's
#: business. What is reported is the kind and a fingerprint, the same one
#: redaction writes, and never the value: a report that leaves the machine
#: must not become the place the secret was copied to.
_SECRET_KINDS = frozenset({"aws_access_key", "vendor_token", "jwt"})
_SECRET_PATTERNS = tuple(
    (kind, pattern, group) for kind, pattern, group in REDACT_PATTERNS if kind in _SECRET_KINDS
)

#: Every private key opens with the same line, and a scan that goes by the
#: line never sees the rest. So a key block's identity is where it is, not
#: what it holds, and all of them are the one fact.
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")
PRIVATE_KEY = "private key block"

#: Fields whose *name* says a person wrote this. Matched on the whole name,
#: namespace and all: XMP's `dc:creator` is the author, while a bare `Creator`
#: in a PDF or a PNG is the program that wrote it, which is why that one sits
#: in the software fields above. A name is never read out of prose - a
#: capitalised pair of words is a name, a town and a sign-off in equal
#: measure - and since a document body is addressed by line, it cannot
#: reach these tables by construction.
_PERSON_FIELDS = frozenset(
    {"author", "dc:creator", "artist", "by-line", "lastmodifiedby", "cp:lastmodifiedby"}
)

#: Mail headers carrying mailboxes, whose display names are people.
_MAILBOX_FIELDS = frozenset({"from", "to", "cc", "reply-to", "sender"})

#: Fields whose name says an organisation. `Source` is not here: it is an
#: agency in IPTC, a scanner in a PNG and something else again in RIFF.
_ORG_FIELDS = frozenset({"company", "credit"})

#: What an application writes where a name should go.
_NOBODY = frozenset(
    {
        "microsoft office user",
        "windows user",
        "office user",
        "user",
        "admin",
        "administrator",
        "unknown",
        "author",
        "owner",
        "default",
        "n/a",
        "none",
        "anonymous",
        "guest",
        "root",
        "system",
        "unnamed",
        "untitled",
    }
)

#: Where a URL is somebody's profile: the host, what to call the platform,
#: and what the path has to look like. `www.` and `m.` come off the host.
_PROFILE_PATH = {
    "x": re.compile(r"^/([A-Za-z0-9_]{1,15})/?$"),
    "instagram": re.compile(r"^/([A-Za-z0-9_.]{1,30})/?$"),
    "github": re.compile(r"^/([A-Za-z0-9][A-Za-z0-9\-]{0,38})/?$"),
    "linkedin": re.compile(r"^/in/([A-Za-z0-9\-%]+)/?$"),
    "telegram": re.compile(r"^/([A-Za-z0-9_]{5,32})/?$"),
    "tiktok": re.compile(r"^/@([A-Za-z0-9_.]+)/?$"),
    "youtube": re.compile(r"^/@([A-Za-z0-9_.\-]+)/?$"),
    "reddit": re.compile(r"^/(?:u|user)/([A-Za-z0-9_\-]+)/?$"),
    "facebook": re.compile(r"^/([A-Za-z0-9.]{5,})/?$"),
}
_PROFILE_HOSTS = {
    "x.com": "x",
    "twitter.com": "x",
    "instagram.com": "instagram",
    "github.com": "github",
    "linkedin.com": "linkedin",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube",
    "reddit.com": "reddit",
    "facebook.com": "facebook",
}

#: First path segments that are a site's own pages rather than somebody's.
_NOT_A_HANDLE = frozenset(
    {
        "home", "search", "login", "signup", "signin", "settings", "explore", "p",
        "reel", "reels", "stories", "orgs", "about", "help", "share", "sharer",
        "sharer.php", "groups", "pages", "events", "hashtag", "i", "intent",
        "profile.php", "topics", "marketplace", "watch", "tv", "status",
        "notifications", "messages", "privacy", "terms", "features", "pricing",
        "sponsors", "apps", "site", "new", "join", "trending", "live", "shorts",
        "feed", "dialog", "photo", "video", "videos", "posts", "tag", "tags",
        "channel", "user", "pub", "company", "jobs", "legal", "policies",
    }
)  # fmt: skip

#: A user's directory on the machine that made the file - `C:\Users\name`,
#: `/Users/name`, `/home/name` - as it turns up in a template path, a
#: recorded location or a command. The ones every machine has are nobody's.
USER_DIR_RE = re.compile(r"(?:^|[\\/])(?i:Users|home)[\\/]([^\\/\s:*?\"<>|]{1,64})(?=[\\/]|$)")
_SHARED_HOMES = frozenset(
    {"public", "default", "default user", "all users", "shared", "administrator"}
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
    # `.onion` is a special-use name (RFC 7686) that no resolver answers, and
    # an address there is its own identifier type, checksum and all. It is
    # not a domain here whatever the TLD list says - and it does say so.
    if cleaned.endswith(".onion"):
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


def _plain(name: str) -> str:
    """One spelling for one name: case and spacing folded, accents kept.

    `Kowalski, Jan` and `Jan Kowalski` stay two entries. Deciding they are one
    would be guessing, and a wrong merge is worse than a duplicate.
    """
    return " ".join(name.strip().strip("\"'").split()).casefold()


def _names(value: str) -> Iterator[str]:
    """The names in a field, which XMP and Office write `;`-separated."""
    for part in value.split(";"):
        name = part.strip().strip("\"'")
        plain = _plain(name)
        if len(plain) < 2 or plain in _NOBODY or not any(char.isalpha() for char in plain):
            continue
        if EMAIL_RE.fullmatch(name):
            continue  # already an email, and naming it twice says nothing new
        yield name


def _profile(url: str) -> tuple[str, str] | None:
    """(platform, user) if `url` is somebody's page on a platform this knows."""
    try:
        parts = urlsplit(url.rstrip(_TRAILING_PUNCT))
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    for prefix in ("www.", "m.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    platform = _PROFILE_HOSTS.get(host)
    if platform is None:
        return None
    match = _PROFILE_PATH[platform].match(parts.path)
    if match is None or match.group(1).lower() in _NOT_A_HANDLE:
        return None
    return platform, match.group(1)


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
        for found in record.evidence:
            arrival = category(found) == ORIGIN
            source = source_label(found)
            for label, value in (
                ("url", found.url),
                ("referrer", found.referrer),
                ("command", found.command),
                ("tool", found.tool),
                ("note", found.note),
                ("geo", found.geo),
                ("location", found.location),
            ):
                if value:
                    yield _Text(name, source, label, value, IN_METADATA, arrival)
            for label, value in found.fields.items():
                if value:
                    yield _Text(name, source, label, str(value), IN_METADATA, arrival)
        if content:
            # One yield per passage rather than one per file. Scanning them
            # apart is what lets a value carry the line, slide or chapter it
            # was on, and it costs about a fifth more than scanning the
            # document as one string.
            for passage in read_passages(Path(record.path)) or ():
                yield _Text(name, CONTENT_SOURCE, passage.place, passage.text, IN_CONTENT, False)


def extract(records: list[FileRecord], *, content: bool = False) -> list[Identifier]:
    """Every identifier in what the scan read, deduplicated across files.

    `content` widens the corpus from what the files record about themselves to
    what they say. The two are kept apart on each entry rather than merged, so
    a reader can tell a name in a document from a name in a download record -
    and see where one value is both.
    """
    found: dict[tuple[str, str], Identifier] = {}

    for source in _texts(records, content=content):
        place = f"{source.file}{PLACE}{source.source}{PLACE}{source.where}"
        for family, raw, normalized, private in _scan(source.text, source.where):
            key = (family, normalized)
            entry = found.get(key)
            if entry is None:
                entry = Identifier(type=family, value=raw, normalized=normalized, private=private)
                found[key] = entry
            entry.count += 1
            entry.corpora.add(source.corpus)
            entry.acquired = entry.acquired or source.acquired
            if place not in entry.where:
                if len(entry.where) < MAX_SAMPLES:
                    entry.where.append(place)

    for entry in found.values():
        entry.files = len({place.split(PLACE, 1)[0] for place in entry.where})

    return sorted(found.values(), key=lambda i: (i.type, -i.count, i.normalized))


def _scan(text: str, where: str) -> Iterator[tuple[str, str, str, bool | None]]:
    """Yield (type, raw, normalized, private) for one value."""
    hosts: set[str] = set()

    identifier = where.lower().rpartition(":")[2] in _MESSAGE_ID_FIELDS

    # Who the file says made it: read from the name of the field, never from
    # what the text looks like.
    named = where.lower()
    if named in _PERSON_FIELDS:
        for person in _names(text):
            yield "person", person, _plain(person), None
    elif named in _MAILBOX_FIELDS:
        for display, _address in getaddresses([text]):
            for person in _names(display):
                yield "person", person, _plain(person), None
    elif named in _ORG_FIELDS:
        for organisation in _names(text):
            yield "org", organisation, _plain(organisation), None

    for match in USER_DIR_RE.finditer(text):
        login = match.group(1)
        if login.lower() not in _SHARED_HOMES:
            yield "handle", f"home:{login}", f"home:{login.lower()}", None

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
        profile = _profile(match.group(0))
        if profile is not None:
            platform, user = profile
            yield "handle", f"{platform}:{user}", f"{platform}:{user.lower()}", None

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

    # The self-checking values. A wallet address is believed wherever it
    # stands; the tax numbers only beside their label, see the patterns.
    for match in BTC_LEGACY_RE.finditer(text):
        if is_base58check(match.group(1)):
            yield "btc", match.group(1), match.group(1), None

    for match in BTC_BECH32_RE.finditer(text):
        if bech32_version(match.group(1)) is not None:
            yield "btc", match.group(1), match.group(1).lower(), None

    for match in IBAN_RE.finditer(text):
        if is_iban(match.group(1)):
            yield "iban", match.group(1), "".join(match.group(1).split()), None

    for pattern in (NIP_LABELLED_RE, NIP_PREFIXED_RE):
        for match in pattern.finditer(text):
            digits = re.sub(r"\D", "", match.group(1))
            if is_nip(digits):
                yield "nip", match.group(1), digits, None

    for match in REGON_RE.finditer(text):
        if is_regon(match.group(1)):
            yield "regon", match.group(1), match.group(1), None

    for match in ONION_RE.finditer(text):
        label = match.group(1).lower()
        if is_onion(label):
            yield "onion", match.group(0), f"{label}.onion", None

    for match in MAC_RE.finditer(text):
        hardware = match.group(1).lower().replace("-", ":")
        if hardware not in _NOT_A_DEVICE:
            yield "mac", match.group(1), hardware, None

    for match in SID_RE.finditer(text):
        yield "sid", match.group(1), match.group(1), None

    for match in BIC_RE.finditer(text):
        code = match.group(1).upper()
        if code[4:6].lower() in known_tlds():
            yield "bic", match.group(1), code, None

    for kind, pattern, group in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            handle = f"{kind} {fingerprint(match.group(group))}"
            yield "secret", handle, handle, None

    for _ in PRIVATE_KEY_RE.finditer(text):
        yield "secret", PRIVATE_KEY, PRIVATE_KEY, None

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
