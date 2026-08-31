"""Whether the acquisition records for a file agree with each other.

One record is a claim. Two that agree are corroboration, and worth more than
either alone. Two that disagree are a finding in their own right - a file
downloaded twice, a file copied after it arrived, or origin metadata that was
replaced afterwards - and a report that quietly prints the higher-scoring one
has destroyed that finding rather than reported it.

Nothing here decides which record is true. It says what the records do, and
leaves the reading of it to whoever is reading the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .identify import normalize_url
from .models import ACQUISITION, INTRINSIC, SOURCE_LABELS, FileRecord, Origin

#: No acquisition record at all: nothing said how the file got here.
NONE = "no acquisition record"

#: Exactly one. The ordinary case, and not a finding either way.
SINGLE = "single source"

#: Two or more independent records naming the same address.
AGREEMENT = "agreement"

#: Same host, different path. Often one record kept a redirect and another the
#: landing page, which is agreement about where but not about what.
PARTIAL = "partial agreement"

#: Different hosts. Something happened that the records do not jointly explain.
CONFLICT = "conflict"


@dataclass(slots=True)
class Verdict:
    state: str
    reasons: list[str] = field(default_factory=list)

    @property
    def notable(self) -> bool:
        """Whether this is worth a line in the report.

        A single uncorroborated record is the common case. Annotating it would
        put a label on almost every entry, and a label on everything says
        nothing.
        """
        return self.state in (AGREEMENT, PARTIAL, CONFLICT) or bool(self.reasons)

    def to_dict(self) -> dict[str, object]:
        return {"state": self.state, "reasons": self.reasons}


def reconcile(record: FileRecord) -> Verdict:
    """Compare everything that claims to say how `record` arrived."""
    acquisition = [origin for origin in record.origins if origin.source in ACQUISITION]
    addressed = [origin for origin in acquisition if origin.url]

    verdict = Verdict(state=_state(addressed))
    verdict.reasons.extend(_address_reasons(addressed, verdict.state))
    verdict.reasons.extend(_time_reasons(record))
    verdict.reasons.extend(_match_reasons(acquisition))
    return verdict


def _state(addressed: list[Origin]) -> str:
    if not addressed:
        return NONE
    if len(addressed) == 1:
        return SINGLE

    normalised = {_address(origin) for origin in addressed}
    if len(normalised) == 1:
        return AGREEMENT
    if len({host for _, host in normalised if host}) == 1:
        return PARTIAL
    return CONFLICT


def _address(origin: Origin) -> tuple[str, str | None]:
    """The URL reduced to what two records have to share to be the same."""
    parsed = normalize_url(origin.url or "")
    if parsed is None:
        return (origin.url or "").rstrip("/").lower(), None
    normalized, host = parsed
    return normalized.rstrip("/"), host


def _address_reasons(addressed: list[Origin], state: str) -> list[str]:
    if state == AGREEMENT:
        names = ", ".join(_label(origin) for origin in addressed)
        return [f"{len(addressed)} records name the same address: {names}"]

    if state in (PARTIAL, CONFLICT):
        return [f"{_label(origin)} says {origin.url}" for origin in addressed]
    return []


def _time_reasons(record: FileRecord) -> list[str]:
    """Flag a file that claims to have been authored after it arrived.

    The reverse - created long before it was downloaded - is the normal order of
    events and says nothing, so it is not reported.
    """
    arrived = min(
        (o.at for o in record.origins if o.source in ACQUISITION and o.at),
        default=None,
    )
    authored = max((o.at for o in record.origins if o.source in INTRINSIC and o.at), default=None)

    if arrived and authored and authored > arrived:
        return [f"the file reports being created at {authored}, after it arrived at {arrived}"]
    return []


def _match_reasons(acquisition: list[Origin]) -> list[str]:
    """Say when a record was tied to this file by its name alone.

    A name match survives the file being moved, which is why it is made, but it
    also matches a different file that happens to share the name.
    """
    reasons = []
    for origin in acquisition:
        note = origin.note or ""
        if "size differs" in note or "recorded size differs" in note:
            reasons.append(f"{_label(origin)} matched by name, but its recorded size differs")
        elif "matched by file name and size" in note:
            reasons.append(f"{_label(origin)} matched by name, and its recorded size agrees")
        elif "matched by file name" in note:
            reasons.append(f"{_label(origin)} was matched by file name, not by path")
    return reasons


def _label(origin: Origin) -> str:
    return SOURCE_LABELS.get(origin.source, origin.source)
