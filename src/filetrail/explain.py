"""Why the report says what it says, for one file.

The report answers *what do we know*. This answers *why should I believe it*,
which is a different question and the one that decides whether a finding can be
used in anything that matters.

It adds no data. Everything here was already found; what is new is that the
records are laid out by the question they answer, the ones that support each
other are named, the ones that contradict each other are named, and the
conclusion is drawn out loud - so that a reader can disagree with it. A verdict
nobody can argue with is a verdict nobody should trust.
"""

from __future__ import annotations

from .models import ACQUISITION, INTERACTION, INTRINSIC, SOURCE_LABELS, FileRecord, kind
from .reconcile import (
    AGREEMENT,
    ATTRIBUTION_CONFLICT,
    NONE,
    PARTIAL,
    SINGLE,
    TIMELINE_CONFLICT,
    Verdict,
)

#: The three questions, in the order a reader asks them.
KINDS = (
    (ACQUISITION, "how the file reached this machine"),
    (INTRINSIC, "what the file records about its own earlier life"),
    (INTERACTION, "what handled it here afterwards"),
)

_COUNTS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def grouped(record: FileRecord) -> list[tuple[str, str, list]]:
    """Every claim, under the question it answers. Empty kinds are dropped."""
    out = []
    for name, question in KINDS:
        claims = [origin for origin in record.origins if kind(origin) == name]
        if claims:
            claims.sort(key=lambda origin: -origin.confidence)
            out.append((name, question, claims))
    return out


def conclusion(record: FileRecord, verdict: Verdict) -> list[str]:
    """The reading of the evidence, in sentences, one idea each."""
    said: list[str] = []
    acquisition = [o for o in record.origins if kind(o) == ACQUISITION]
    intrinsic = [o for o in record.origins if kind(o) == INTRINSIC]
    interaction = [o for o in record.origins if kind(o) == INTERACTION]

    said.append(_arrival(verdict, acquisition))

    contested = [f for f in verdict.findings if f.kind == ATTRIBUTION_CONFLICT]
    if intrinsic and not contested:
        tools = ", ".join(sorted({o.tool for o in intrinsic if o.tool})) or "itself"
        said.append(
            f"The file describes an earlier life of its own - {tools} - which says nothing "
            "about how it arrived and does not contest the record above."
        )
    elif contested:
        fields = ", ".join(finding.text.split(":")[0] for finding in contested)
        said.append(
            f"The file gives two accounts of itself and they disagree about {fields}. "
            f"{_which_is_stale(contested)} - but which was rewritten is a question this "
            "cannot answer, only raise."
        )

    if interaction and not acquisition:
        who = ", ".join(sorted({o.tool for o in interaction if o.tool})) or "something here"
        said.append(
            f"It was handled here by {who}, which proves contact and not arrival: the file "
            "may have reached this machine by any route at all before that."
        )

    if any(finding.kind == TIMELINE_CONFLICT for finding in verdict.findings):
        said.append(
            "The file also reports being created after it arrived, which cannot both be true. "
            "Either a clock was wrong, or the metadata was written after the fact."
        )
    return said


def _which_is_stale(contested: list) -> str:
    """Why one of the two blocks is the likelier to be out of date.

    Whichever block an editor understands is the one it rewrites; the other it
    copies through untouched. Naming them is the point - a conclusion about the
    IPTC block of a file that has none is describing evidence that is not there.
    """
    pairs = list(dict.fromkeys(finding.sources for finding in contested if finding.sources))
    if len(pairs) != 1:
        return (
            "An editor maintains the block it understands and copies the others through as "
            "it found them, so the ones it did not touch are the likelier to describe an "
            "earlier state"
        )
    older, newer = pairs[0]
    return (
        f"An editor maintains the {newer} and leaves the {older} as it found it, so the "
        f"{older} is the likelier of the two to describe an earlier state"
    )


def _arrival(verdict: Verdict, acquisition: list) -> str:
    count = _COUNTS.get(len(acquisition), str(len(acquisition)))

    if verdict.state == NONE:
        return (
            "Nothing on this machine recorded how the file arrived. Run `filetrail doctor` "
            "to see whether that evidence exists here at all before reading it as absence."
        )
    if verdict.state == SINGLE:
        return (
            f"One record explains how the file arrived, and nothing corroborates it. "
            f"That is the ordinary case, not a weakness, but it rests on {_only(acquisition)}."
        )
    if verdict.state == AGREEMENT:
        return (
            f"{count.capitalize()} independent records agree on where the file came from. "
            "Neither depends on the other, so together they are worth more than either alone."
        )
    if verdict.state == PARTIAL:
        return (
            "The records agree on the host but name different paths. That is usually one "
            "record keeping a redirect and another the address it landed on."
        )
    return (
        "The acquisition records do not agree. The file may have been downloaded more than "
        "once, copied after it arrived, or had its origin metadata replaced - and nothing "
        "here settles which."
    )


def _only(acquisition: list) -> str:
    if not acquisition:
        return "nothing"
    return SOURCE_LABELS.get(acquisition[0].source, acquisition[0].source)
