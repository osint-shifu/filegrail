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

from pathlib import Path

from .models import ACQUISITION, INTERACTION, INTRINSIC, SOURCE_LABELS, FileRecord, Origin, kind
from .reconcile import (
    AGREEMENT,
    ATTRIBUTION_CONFLICT,
    NONE,
    PARTIAL,
    SINGLE,
    TIMELINE_CONFLICT,
    Verdict,
)


def questions(home: Path | None = None) -> tuple[tuple[str, str], ...]:
    """The three questions, in the order a reader asks them.

    Two of them name a machine, and which machine that is depends on whose
    traces were read. Under `--home` the answers come from a mounted image or a
    copied profile, and calling that `this machine` is not a turn of phrase -
    it is a false statement about where the evidence lives.
    """
    machine = "that machine" if home else "this machine"
    return (
        (ACQUISITION, f"how the file reached {machine}"),
        (INTRINSIC, "what the file records about its own earlier life"),
        (INTERACTION, f"what handled it {'there' if home else 'here'} afterwards"),
    )


#: The questions as asked about this machine, which is the ordinary case.
KINDS = questions()

_COUNTS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def grouped(record: FileRecord, home: Path | None = None) -> list[tuple[str, str, list]]:
    """Every claim, under the question it answers. Empty kinds are dropped."""
    out = []
    for name, question in questions(home):
        claims = [origin for origin in record.origins if kind(origin) == name]
        if claims:
            claims.sort(key=lambda origin: -origin.confidence)
            out.append((name, question, claims))
    return out


def conclusion(record: FileRecord, verdict: Verdict, home: Path | None = None) -> list[str]:
    """The reading of the evidence, in sentences, one idea each."""
    said: list[str] = []
    acquisition = [o for o in record.origins if kind(o) == ACQUISITION]
    intrinsic = [o for o in record.origins if kind(o) == INTRINSIC]
    interaction = [o for o in record.origins if kind(o) == INTERACTION]

    said.append(_arrival(verdict, acquisition, home))

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
        where = "there" if home else "here"
        who = ", ".join(sorted({o.tool for o in interaction if o.tool})) or f"something {where}"
        said.append(
            f"It was handled {where} by {who}, which proves contact and not arrival: the file "
            f"may have reached {'that' if home else 'this'} machine by any route at all "
            "before that."
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

    Not every pairing works that way, and the ones that do not are not made to.
    A PDF's two blocks are written by one producer, and an exporter stamps a
    fresh Info dictionary while carrying the XMP through from the source
    document, so the Info is as often the newer of the two as the older.
    """
    pairs = list(
        dict.fromkeys(
            (finding.sources, finding.maintained) for finding in contested if finding.sources
        )
    )
    if len(pairs) != 1:
        return (
            "An editor maintains the block it understands and copies the others through as "
            "it found them, so the ones it did not touch are the likelier to describe an "
            "earlier state"
        )
    (first, second), maintained = pairs[0]
    if maintained is None:
        return (
            f"One tool writes both the {first} and the {second}, and either can be the block "
            f"carried through from an earlier document, so neither is reliably the older"
        )
    older = first if maintained == second else second
    return (
        f"An editor maintains the {maintained} and leaves the {older} as it found it, so the "
        f"{older} is the likelier of the two to describe an earlier state"
    )


def _arrival(verdict: Verdict, acquisition: list, home: Path | None = None) -> str:
    count = _COUNTS.get(len(acquisition), str(len(acquisition)))

    if verdict.state == NONE:
        # The advice has to name the same machine the evidence would be on.
        # Sending a reader to survey their own laptop about somebody else's
        # profile wastes the one step that would have told them the truth.
        where = f"in the profile at {home}" if home else "on this machine"
        survey = f"filegrail doctor --home {home}" if home else "filegrail doctor"
        return (
            f"Nothing {where} recorded how the file arrived. Run `{survey}` to see whether "
            f"that evidence exists {'there' if home else 'here'} at all before reading it "
            "as absence."
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


def _only(acquisition: list[Origin]) -> str:
    if not acquisition:
        return "nothing"
    return SOURCE_LABELS.get(acquisition[0].source, acquisition[0].source)
