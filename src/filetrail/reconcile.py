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
from .models import ACQUISITION, INTRINSIC, SOURCE_LABELS, FileRecord, Origin, kind

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

#: What a single finding is about. Typed, so a consumer reading the JSON does
#: not have to pattern-match English to tell one problem from another - and so
#: the two conflicts, which are genuinely different classes of problem, stay
#: distinguishable after the sentence has been translated or reworded.
CORROBORATION = "corroboration"
SOURCE_CONFLICT = "source_conflict"
PATH_DISAGREEMENT = "path_disagreement"
TIMELINE_CONFLICT = "timeline_conflict"
WEAK_MATCH = "weak_match"
SIZE_MISMATCH = "size_mismatch"
SIZE_CORROBORATION = "size_corroboration"


@dataclass(slots=True)
class Finding:
    kind: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "text": self.text}


@dataclass(slots=True)
class Verdict:
    state: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        return [finding.text for finding in self.findings]

    @property
    def notable(self) -> bool:
        """Whether this is worth a line in the report.

        A single uncorroborated record is the common case. Annotating it would
        put a label on almost every entry, and a label on everything says
        nothing.
        """
        return self.state in (AGREEMENT, PARTIAL, CONFLICT) or bool(self.findings)

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def reconcile(record: FileRecord) -> Verdict:
    """Compare everything that claims to say how `record` arrived."""
    acquisition = [origin for origin in record.origins if kind(origin) == ACQUISITION]
    addressed = [origin for origin in acquisition if origin.url]

    verdict = Verdict(state=_state(addressed))
    verdict.findings.extend(_address_findings(addressed, verdict.state))
    verdict.findings.extend(_time_findings(record))
    verdict.findings.extend(_match_findings(acquisition))
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


def _address_findings(addressed: list[Origin], state: str) -> list[Finding]:
    if state == AGREEMENT:
        names = ", ".join(_label(origin) for origin in addressed)
        return [Finding(CORROBORATION, f"{len(addressed)} records name the same address: {names}")]

    if state in (PARTIAL, CONFLICT):
        which = PATH_DISAGREEMENT if state == PARTIAL else SOURCE_CONFLICT
        return [Finding(which, f"{_label(origin)} says {origin.url}") for origin in addressed]
    return []


def _time_findings(record: FileRecord) -> list[Finding]:
    """Flag a file that claims to have been authored after it arrived.

    The reverse - created long before it was downloaded - is the normal order of
    events and says nothing, so it is not reported.
    """
    arrived = min(
        (o.at for o in record.origins if kind(o) == ACQUISITION and o.at),
        default=None,
    )
    authored = max((o.at for o in record.origins if kind(o) == INTRINSIC and o.at), default=None)

    if arrived and authored and authored > arrived:
        return [
            Finding(
                TIMELINE_CONFLICT,
                f"the file reports being created at {authored}, after it arrived at {arrived}",
            )
        ]
    return []


def _match_findings(acquisition: list[Origin]) -> list[Finding]:
    """Say when a record was tied to this file by its name alone.

    A name match survives the file being moved, which is why it is made, but it
    also matches a different file that happens to share the name.
    """
    found = []
    for origin in acquisition:
        note = origin.note or ""
        if "recorded size differs" in note:
            found.append(
                Finding(
                    SIZE_MISMATCH,
                    f"{_label(origin)} matched by name, but its recorded size differs",
                )
            )
        elif "matched by file name and size" in note:
            found.append(
                Finding(
                    SIZE_CORROBORATION,
                    f"{_label(origin)} matched by name, and its recorded size agrees",
                )
            )
        elif "matched by file name" in note:
            found.append(
                Finding(WEAK_MATCH, f"{_label(origin)} was matched by file name, not by path")
            )
    return found


def _label(origin: Origin) -> str:
    return SOURCE_LABELS.get(origin.source, origin.source)
