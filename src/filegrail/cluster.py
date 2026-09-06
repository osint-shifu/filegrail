"""Which files in one scan came from the same place.

A directory is a list of files. A case is the smaller number of sources that
produced them, and the difference between those two readings is what this is
for: twelve files naming three authors is a picture, twelve rows is not.

Nothing here says two files came from one person or one camera. It says they
name the same thing, and on which axis - because the axes are not equally
strong and presenting them alike would be the lie in the middle of an
otherwise useful summary. A body serial names one physical camera. A make and
model names a product that thousands of people own. A name in an author field
is text somebody typed, and two people can type the same one.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .models import BLOCK_LABELS, FileRecord, label
from .overview import AUTHOR_FIELDS

#: A name in a field meant for one: text a person or a program wrote down.
AUTHOR = "author"

#: One physical camera. A body serial is assigned per unit, so two files
#: carrying the same one were taken by the same machine.
DEVICE = "device"

#: A make and model. It says what kind of camera, and deliberately not which:
#: the two are a different claim and are never merged, because a reader told
#: that two photographs "came from the same camera" on the strength of a model
#: name has been told something the metadata does not support.
MODEL = "model"

#: The axes in the order the report reads them: what took the picture before
#: what kind of thing it was, and both before a name somebody typed. Strongest
#: identification first, so a section cut short keeps the part that identifies
#: most.
AXES = (DEVICE, MODEL, AUTHOR)

#: Where a camera writes the serial of the body itself.
_SERIAL_FIELDS = ("BodySerialNumber", "SerialNumber", "InternalSerialNumber")

#: How these formats write more than one author into a field meant for one.
#: OOXML, the PDF `Info` dictionary and Dublin Core all use it, and the value
#: read whole is a person nobody is - which hides every real author in it.
#: A comma is deliberately not a separator: `Smith, John` is one person written
#: surname first, and splitting there would invent two people per document.
_AUTHOR_SEPARATOR = ";"

#: The make and the model, which are one answer written in two fields.
_MAKE, _MODEL = "Make", "Model"

#: How a basis joins the block to the field inside it.
_BASIS = " \u00b7 "


@dataclass(slots=True)
class Group:
    """The files in a scan that named one value on one axis."""

    axis: str
    name: str
    paths: list[str]

    #: The block and field the value was read from - `EXIF · BodySerialNumber`.
    #: A cluster without it says four files share a serial and leaves a reader
    #: to guess which tag that was, which is the first thing anybody checks.
    basis: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"axis": self.axis, "name": self.name, "basis": self.basis, "paths": self.paths}


def cluster(records: list[FileRecord]) -> list[Group]:
    """Group the scanned files by every identifying value they share."""
    found: dict[tuple[str, str], list[str]] = {}
    bases: dict[tuple[str, str], str] = {}
    for record in records:
        for axis, name, basis in _names(record):
            paths = found.setdefault((axis, name), [])
            bases.setdefault((axis, name), basis)
            if record.path not in paths:
                paths.append(record.path)
    groups = [
        Group(axis, name, paths, bases[(axis, name)]) for (axis, name), paths in found.items()
    ]
    groups.sort(key=lambda group: (AXES.index(group.axis), -len(group.paths), group.name))
    return groups


def _model(fields: dict[str, str]) -> str | None:
    """`NIKON COOLPIX P6000` out of the two fields that spell it.

    A make with no model is dropped rather than grouped on: `NIKON` alone puts
    every Nikon in the scan in one bucket, which is a fact about the shop
    rather than about the case.
    """
    model = (fields.get(_MODEL) or "").strip()
    if not model:
        return None
    make = (fields.get(_MAKE) or "").strip()
    if make and not model.upper().startswith(make.upper()):
        return f"{make} {model}"
    return model


def _names(record: FileRecord) -> Iterator[tuple[str, str, str]]:
    """Every identifying value this file carries, the axis it sits on, and the
    field it was read from."""
    for found in record.evidence:
        block = BLOCK_LABELS.get(found.block or "", label(found))
        for field in AUTHOR_FIELDS.get(found.block or "", ()):
            for name in (found.fields.get(field) or "").split(_AUTHOR_SEPARATOR):
                if name.strip():
                    yield AUTHOR, name.strip(), f"{block}{_BASIS}{field}"

        for field in _SERIAL_FIELDS:
            serial = (found.fields.get(field) or "").strip()
            if serial:
                yield DEVICE, serial, f"{block}{_BASIS}{field}"
                break

        model = _model(found.fields)
        if model:
            named = _MODEL if _MAKE not in found.fields else f"{_MAKE} + {_MODEL}"
            yield MODEL, model, f"{block}{_BASIS}{named}"
