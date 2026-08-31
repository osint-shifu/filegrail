from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

# How much a source is trusted when several disagree. Higher wins.
CONFIDENCE = {
    "browser-download": 90,
    "windows-zone-identifier": 85,
    "macos-wherefroms": 85,
    "xdg-xattr": 80,
    "archive-member": 70,
    # A purpose-built provenance standard, but the signature is not verified here.
    "c2pa": 60,
    "device-metadata": 55,
    "document-metadata": 50,
    "shell-history": 40,
    "filesystem": 10,
}


@dataclass(slots=True)
class Origin:
    """One claim about where a file came from, made by one source."""

    source: str
    url: str | None = None
    referrer: str | None = None
    tool: str | None = None
    command: str | None = None
    at: str | None = None
    location: str | None = None
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

    @property
    def best(self) -> Origin | None:
        if not self.origins:
            return None
        return max(self.origins, key=lambda o: (o.confidence, o.at or ""))

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
        }
