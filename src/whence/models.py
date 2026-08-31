from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# How much a source is trusted when several disagree. Higher wins.
CONFIDENCE = {
    "browser-download": 90,
    "windows-zone-identifier": 85,
    "macos-wherefroms": 85,
    "xdg-xattr": 80,
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
    bytes: int | None = None
    mime: str | None = None
    sha256: str | None = None
    note: str | None = None

    @property
    def confidence(self) -> int:
        return CONFIDENCE.get(self.source, 0)

    def to_dict(self) -> dict[str, Any]:
        data = {k: v for k, v in asdict(self).items() if v is not None}
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "btime": self.btime,
            "sha256": self.sha256,
            "origins": [o.to_dict() for o in self.origins],
        }
