"""What a saved message says about how it travelled.

`Received:` headers are the only part of an email not written by the sender.
Each mail server prepends its own as the message passes through, so they read
from the bottom up, and the topmost was written by the recipient's own server -
the one hop nobody but the recipient could have forged. Every hop below it was
written by a machine the sender may control, which is why they are not ranked
alike: the chain is evidence, and how much of it to believe depends on where in
the chain you are reading.

Everything else - who it says it is from, what it says the subject was, which
client it says composed it - is the message describing itself, checked by
nobody, and it is kept apart from the delivery record for that reason.
"""

from __future__ import annotations

import re
from datetime import timezone
from email.parser import BytesHeaderParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from ..models import Origin

SUFFIXES = {".eml"}

#: Headers sit at the front. A message with more than this before its body is
#: not a message anybody sent.
_WINDOW = 512 * 1024

#: A mailing list legitimately adds a dozen hops. Hundreds is a message built to
#: make a report unreadable.
_MAX_HOPS = 40

_MAX_VALUE = 1024

#: What the sender says about the message, worth naming rather than dumping.
_HEADERS = (
    "From",
    "To",
    "Cc",
    "Reply-To",
    "Return-Path",
    "Sender",
    "Subject",
    "Date",
    "Message-ID",
    "In-Reply-To",
    "References",
    "X-Mailer",
    "User-Agent",
    "X-Originating-IP",
    "Content-Type",
    "List-Id",
)

#: The client that composed the message, under the two names clients use.
_COMPOSER = ("X-Mailer", "User-Agent")

_FROM = re.compile(r"\bfrom\s+([^\s(;]+)", re.I)
_BY = re.compile(r"\bby\s+([^\s(;]+)", re.I)
_WITH = re.compile(r"\bwith\s+([^\s(;]+)", re.I)
_ID = re.compile(r"\bid\s+([^\s(;]+)", re.I)
_FOR = re.compile(r"\bfor\s+<?([^>\s;]+)", re.I)

#: The address the receiving server actually saw, as against the name the
#: connecting host claimed for itself.
_ADDRESS = re.compile(r"\[(?:IPv6:)?([0-9A-Fa-f:.]{3,45})\]")


def read_mail(path: Path) -> list[Origin]:
    """Return the delivery record and the message's own headers."""
    if path.suffix.lower() not in SUFFIXES:
        return []
    try:
        with path.open("rb") as handle:
            message = BytesHeaderParser().parsebytes(handle.read(_WINDOW))
    except (OSError, ValueError):
        return []

    hops = message.get_all("Received") or []
    found = [
        _hop(value, "email-delivery" if position == 0 else "email-relay")
        for position, value in enumerate(hops[:_MAX_HOPS])
    ]
    if header := _self_description(message):
        found.append(header)
    return [origin for origin in found if origin is not None]


def _hop(value: str, source: str) -> Origin | None:
    """One server's note of taking the message from another."""
    said = " ".join(value.split())
    fields = {
        name: found.group(1)
        for name, pattern in (
            ("From", _FROM),
            ("By", _BY),
            ("With", _WITH),
            ("Id", _ID),
            ("For", _FOR),
        )
        if (found := pattern.search(said))
    }
    if address := _ADDRESS.search(said):
        fields["ConnectingAddress"] = address.group(1)
    if not fields:
        return None

    claimed = fields.get("From")
    seen = fields.get("ConnectingAddress")
    note = " from ".join(part for part in ("received", claimed) if part)
    if seen and seen != claimed:
        note = f"{note} at {seen}"

    return Origin(
        source=source,
        # The server that wrote the line, which is the one thing in it that
        # server knew first-hand.
        tool=fields.get("By"),
        at=_moment(said),
        note=note,
        fields=fields,
    )


def _self_description(message) -> Origin | None:
    """What the message says about itself, none of which anybody checked."""
    fields = {}
    for name in _HEADERS:
        value = message.get(name)
        if value and (text := " ".join(str(value).split())):
            fields[name] = text[:_MAX_VALUE]
    if not fields:
        return None

    subject = fields.get("Subject")
    return Origin(
        source="email-header",
        tool=next((fields[name] for name in _COMPOSER if name in fields), None),
        at=_moment(fields.get("Date", ""), whole=True),
        note=f"subject {subject}" if subject else None,
        fields=fields,
    )


def _moment(said: str, *, whole: bool = False) -> str | None:
    """The timestamp a header carries, in UTC.

    A `Received:` header puts it after the last semicolon, behind the `for`
    address which contains one of its own - so it is taken from the right rather
    than searched for.
    """
    stamp = said if whole else said.rpartition(";")[2]
    if not stamp.strip():
        return None
    try:
        when = parsedate_to_datetime(stamp.strip())
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        # `-0000` means the writer declined to say. UTC is the reading that
        # invents the least.
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
