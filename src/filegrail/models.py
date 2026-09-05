from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # a Link is attached by `lineage`, which imports this module
    from .lineage import Link

# How much a source is trusted when several disagree. Higher wins.
CONFIDENCE: dict[str, int] = {
    "browser-download": 90,
    # A mail server on the recipient's side wrote this down as the message
    # arrived. Independent of the sender, like a download record - and unlike
    # one it travels inside the file it describes, which is why it sits below
    # the attributes an operating system keeps outside the bytes.
    "email-delivery": 78,
    "windows-zone-identifier": 85,
    "macos-wherefroms": 85,
    # Written by LaunchServices at download time, the same authority as a
    # where-from attribute and recorded beside it rather than instead of it.
    "macos-quarantine": 85,
    "xdg-xattr": 80,
    # Written by the program that fetched the bytes, and it names the page
    # they came from. Below the attributes an operating system attaches to the
    # file itself, because a sidecar is a separate file paired to the media by
    # name alone: a copy that brings one and not the other, or a rename, breaks
    # that pairing in a way an extended attribute cannot be broken.
    "ytdlp-sidecar": 75,
    "archive-member": 70,
    # A torrent lists its members by name and exact size, and a file matching
    # both was very likely one of them. The same strength of inference as an
    # archive member, and the same way of being wrong: two files can share a
    # name and a size without being the same file.
    "torrent": 70,
    # A purpose-built provenance standard, but the signature is not verified here.
    "c2pa": 60,
    "device-metadata": 55,
    # Structured and purpose-built for editing history, but free text an editor
    # writes about itself: weaker than a camera naming its own model, stronger
    # than a bare document property.
    "xmp": 52,
    "xmp-history": 52,
    # The same kind of self-description as XMP and the older of the two. Modern
    # tools maintain XMP and leave the IIM block as it was, so a byline here is
    # often a record of an earlier state rather than the current one.
    "iptc": 51,
    "document-metadata": 50,
    # Metadata read from a file inside an archive, restated as a claim about
    # the archive. One number is a simplification: what was read is as strong
    # as it would be on disk - a camera naming itself is a camera naming
    # itself - but what it establishes here is only what the container holds.
    "archive-content": 50,
    # A hop the sender may have written in full before sending. Recorded by
    # something, but not by anything the recipient has reason to trust.
    "email-relay": 45,
    # A file inside a folder a client keeps in step with an account. The
    # containment is a fact and the configuration is authoritative about it;
    # what it implies about origin is nothing, because sync runs both ways.
    "sync-folder": 38,
    "shell-history": 40,
    # A file name, and nothing else. Both clients write a fixed pattern and a
    # file carrying one usually did come through that client - but a name is
    # typed as easily as it is written, survives no scrutiny on its own, and is
    # lost the moment somebody renames the file. Below an application having
    # opened it, which at least happened.
    "messenger-name": 25,
    # An application opening a file proves contact, not acquisition.
    # A Windows shortcut says the same thing and records the size of what it
    # pointed at, which is one check more than the desktop list offers.
    "windows-recent": 36,
    "recent-documents": 35,
    # The weakest self-description there is: forging a From line takes nothing
    # but typing it.
    "email-header": 30,
    "filesystem": 10,
}

#: How each source reads in prose. Data about sources, so it lives beside the
#: confidence table rather than in the renderer - reconciliation needs to name a
#: source too, and importing the renderer to do it would be a cycle.
SOURCE_LABELS: dict[str, str] = {
    "browser-download": "browser download",
    "email-delivery": "mail delivery",
    "email-relay": "mail relay",
    "email-header": "mail headers",
    "windows-zone-identifier": "Windows zone",
    "macos-wherefroms": "macOS where-from",
    "macos-quarantine": "macOS quarantine",
    "xdg-xattr": "XDG attribute",
    "ytdlp-sidecar": "yt-dlp sidecar",
    "archive-member": "archive member",
    "torrent": "torrent",
    "c2pa": "content credentials",
    "device-metadata": "device metadata",
    "xmp": "XMP",
    "xmp-history": "XMP history",
    "iptc": "IPTC",
    "document-metadata": "document metadata",
    "archive-content": "archive content",
    "shell-history": "shell history",
    "messenger-name": "messenger file name",
    "recent-documents": "recent documents",
    "sync-folder": "sync folder",
    "windows-recent": "recent shortcut",
    "filesystem": "filesystem",
}

#: How each block reads in prose, where naming it says more than the source
#: does. Only a `document-metadata` claim is renamed by it: that source names a
#: category rather than a thing - nine readers answer to it - so a reader told
#: only that has been told the claim is self-reported and nothing else. Every
#: other source already names something specific, and a camera naming its own
#: model is `device metadata`, which says more than `EXIF`.
BLOCK_LABELS: dict[str, str] = {
    "pdf-info": "PDF Info",
    "ooxml-properties": "OOXML properties",
    "odf-meta": "ODF meta",
    "epub-package": "EPUB package",
    "rtf-generator": "RTF generator",
    "svg-metadata": "SVG metadata",
    "notebook-kernel": "notebook kernel",
    "exif": "EXIF",
    "isobmff": "movie metadata",
    "png-text": "PNG text",
    "ole-summary": "OLE summary",
    "riff": "RIFF",
    "id3": "ID3",
    "matroska": "Matroska",
    "vorbis-comment": "Vorbis comment",
}


def label(origin: Origin) -> str:
    """What to call the source of this claim, in the words the report uses."""
    if origin.source == "document-metadata" and origin.block in BLOCK_LABELS:
        return BLOCK_LABELS[origin.block]
    return SOURCE_LABELS.get(origin.source, origin.source)


#: Commands that plausibly fetch a file. Kept here rather than in the shell
#: reader because deciding what kind of claim an origin makes is a question
#: about sources, and the reader imports this module rather than the reverse.
FETCH_TOOLS = frozenset(
    {
        "curl",
        "wget",
        "aria2c",
        "yt-dlp",
        "youtube-dl",
        "git",
        "scp",
        "rsync",
        "s3cmd",
        "aws",
        "gh",
        "gallery-dl",
        "wpull",
        "httrack",
        "monolith",
    }
)

#: How the file reached this machine. Another system wrote it down at the time.
ACQUISITION = "acquisition"

#: Something on this machine handled the file afterwards. It proves contact and
#: says nothing about where the bytes came from - an application opening a file
#: did not put it there, and presenting the two as one kind of claim invites
#: exactly that misreading.
INTERACTION = "interaction"

#: What the file records about its own earlier life: who made it, with what,
#: when and where. It travelled with the bytes.
INTRINSIC = "intrinsic"

_KINDS = {
    "browser-download": ACQUISITION,
    "windows-zone-identifier": ACQUISITION,
    "macos-wherefroms": ACQUISITION,
    "macos-quarantine": ACQUISITION,
    "xdg-xattr": ACQUISITION,
    "ytdlp-sidecar": ACQUISITION,
    "email-delivery": ACQUISITION,
    "email-relay": ACQUISITION,
    "archive-member": ACQUISITION,
    "torrent": ACQUISITION,
    "messenger-name": ACQUISITION,
    "filesystem": ACQUISITION,
    "recent-documents": INTERACTION,
    "sync-folder": INTERACTION,
    "windows-recent": INTERACTION,
    "c2pa": INTRINSIC,
    "device-metadata": INTRINSIC,
    "xmp": INTRINSIC,
    "xmp-history": INTRINSIC,
    "iptc": INTRINSIC,
    "email-header": INTRINSIC,
    "document-metadata": INTRINSIC,
    "archive-content": INTRINSIC,
}


def kind(origin: Origin) -> str:
    """Which of the three questions this claim answers.

    Shell history is the one source that answers either, and which one is
    already in the record: `curl -o` fetched the bytes, `cat` merely touched
    them. Deciding per origin rather than per source keeps a `cat` from being
    reported as though it explained where a file came from.
    """
    if origin.source == "shell-history":
        return ACQUISITION if (origin.tool or "") in FETCH_TOOLS else INTERACTION
    return _KINDS.get(origin.source, INTERACTION)


@dataclass(slots=True)
class Origin:
    """One claim about where a file came from, made by one source."""

    source: str

    #: The metadata block these values were decoded from: `pdf-info`, `exif`,
    #: `png-text`. `source` names what the reader *found* - a camera, a bare
    #: document - which is the axis confidence and colour turn on, and one
    #: reader answers it two ways depending on what the file happened to hold.
    #: This names what it *read*, which is the axis a mirrored self-description
    #: turns on: whether IIM or a PDF Info dictionary applies is a question
    #: about the standard. A record that decoded no metadata block leaves it
    #: unset rather than naming one nobody read.
    block: str | None = None

    url: str | None = None
    referrer: str | None = None
    tool: str | None = None
    command: str | None = None
    at: str | None = None

    #: Where the file says it comes from, written as a place: "Firenze, Italy".
    #: A newsroom types this by hand, so it is a claim like any other text.
    location: str | None = None

    #: A latitude/longitude pair this tool decoded itself, from EXIF or an ISO
    #: 6709 atom. Kept apart from `location` because a decoded fix and a typed
    #: place name are not the same kind of fact, and only one of them can be
    #: put on a map without believing anybody.
    geo: str | None = None
    bytes: int | None = None
    mime: str | None = None
    sha256: str | None = None
    note: str | None = None

    #: Everything the reader decoded, named rather than numbered, beyond the
    #: handful of fields the report summarises. An investigation cannot know in
    #: advance which one matters, so nothing decoded is thrown away.
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def confidence(self) -> int:
        return CONFIDENCE.get(self.source, 0)

    def redacted(self) -> Origin:
        """Return a copy with credentials removed from every free-text field."""
        from .redact import redact_text, redact_url

        def clean(value: str) -> str:
            # A tag like UserComment is free text: it can hold a URL, a command
            # or a bare token, so it goes through both sweeps.
            return redact_url(redact_text(value))

        return replace(
            self,
            url=clean(self.url) if self.url else None,
            referrer=clean(self.referrer) if self.referrer else None,
            command=redact_text(self.command) if self.command else None,
            location=clean(self.location) if self.location else None,
            note=clean(self.note) if self.note else None,
            fields={name: clean(value) for name, value in self.fields.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        data = {k: v for k, v in asdict(self).items() if v}
        data["confidence"] = self.confidence
        return data


@dataclass(slots=True)
class FileRecord:
    """Everything known about one file on disk."""

    path: str
    size: int
    mtime: str
    btime: str | None = None
    sha256: str | None = None
    origins: list[Origin] = field(default_factory=list)

    #: How this file relates to the others in the same scan, from the
    #: identifiers XMP carries for it. Not an origin: an origin is one source's
    #: claim about where this file came from, and a link is a relation between
    #: two records that only exists because both were scanned together.
    links: list[Link] = field(default_factory=list)

    @property
    def best(self) -> Origin | None:
        """The single strongest claim, whatever kind it is.

        Used for grouping and counting, where one file needs one answer. It is
        not what the report prints: see `acquisition` and `intrinsic`.
        """
        if not self.origins:
            return None
        return max(self.origins, key=lambda o: (o.confidence, o.at or ""))

    @property
    def acquisition(self) -> Origin | None:
        """The strongest claim about how the file got here."""
        return self._strongest(ACQUISITION)

    @property
    def interaction(self) -> Origin | None:
        """The strongest claim that something here handled the file."""
        return self._strongest(INTERACTION)

    @property
    def intrinsic(self) -> Origin | None:
        """The strongest claim the file makes about its own earlier life.

        Kept apart from `acquisition` because they answer different questions.
        Ranking them against each other lets a download record delete a camera's
        GPS fix, which is the more valuable of the two far more often than not.
        """
        return self._strongest(INTRINSIC)

    def _strongest(self, wanted: str) -> Origin | None:
        candidates = [origin for origin in self.origins if kind(origin) == wanted]
        if not candidates:
            return None
        return max(candidates, key=lambda o: (o.confidence, o.at or ""))

    def redacted(self) -> FileRecord:
        return replace(self, origins=[origin.redacted() for origin in self.origins])

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "btime": self.btime,
            "sha256": self.sha256,
            "origins": [o.to_dict() for o in self.origins],
            "links": [link.to_dict() for link in self.links],
        }
