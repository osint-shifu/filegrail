"""Evidence-backed relationships between files and investigative pivots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .identify import Identifier, IdentifierEvidence
from .models import FileRecord

HAS_IDENTIFIER = "has identifier"


@dataclass(frozen=True, slots=True)
class Node:
    """One file or normalized identifier in an investigation graph."""

    id: str
    type: str
    value: str
    normalized: str | None = None
    private: bool | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"id": self.id, "type": self.type, "value": self.value}
        if self.normalized is not None:
            data["normalized"] = self.normalized
        if self.private is not None:
            data["private"] = self.private
        return data


@dataclass(frozen=True, slots=True)
class RelationshipEvidence:
    """Why one relationship is present in the graph."""

    source: str
    place: str
    corpus: str
    count: int
    category: str | None = None
    match: str | None = None
    at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "source": self.source,
            "place": self.place,
            "corpus": self.corpus,
            "count": self.count,
        }
        if self.category is not None:
            data["category"] = self.category
        if self.match is not None:
            data["match"] = {"method": self.match}
        if self.at is not None:
            data["at"] = self.at
        return data


@dataclass(frozen=True, slots=True)
class Relationship:
    """A directed edge whose evidence can be checked in the source file."""

    source: str
    target: str
    kind: str
    count: int
    evidence: tuple[RelationshipEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "count": self.count,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class Graph:
    """The graph section added to scan JSON."""

    nodes: tuple[Node, ...]
    relationships: tuple[Relationship, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "relationships": [relationship.to_dict() for relationship in self.relationships],
        }


def file_node_id(path: str) -> str:
    return f"file:{path}"


def identifier_node_id(identifier: Identifier) -> str:
    return f"{identifier.type}:{identifier.normalized}"


def build_graph(records: list[FileRecord], identifiers: list[Identifier]) -> Graph:
    """Build file and identifier nodes plus their evidence-backed edges."""
    nodes = [Node(file_node_id(record.path), "file", record.path) for record in records]
    nodes.extend(
        Node(
            identifier_node_id(identifier),
            identifier.type,
            identifier.value,
            identifier.normalized,
            identifier.private,
        )
        for identifier in identifiers
    )

    relationships = []
    for identifier in identifiers:
        target = identifier_node_id(identifier)
        for path, count in identifier.holders.items():
            found = identifier.evidence.get(path, {})
            evidence = tuple(
                _relationship_evidence(place, occurrences)
                for place, occurrences in sorted(found.items(), key=_evidence_sort_key)
            )
            relationships.append(
                Relationship(file_node_id(path), target, HAS_IDENTIFIER, count, evidence)
            )

    return Graph(
        tuple(sorted(nodes, key=lambda node: node.id)),
        tuple(sorted(relationships, key=lambda edge: (edge.source, edge.target, edge.kind))),
    )


def _evidence_sort_key(item: tuple[IdentifierEvidence, int]) -> tuple[str, ...]:
    place, _count = item
    return (
        place.source,
        place.category or "",
        place.match or "",
        place.place,
        place.corpus,
        place.at or "",
    )


def _relationship_evidence(place: IdentifierEvidence, occurrences: int) -> RelationshipEvidence:
    return RelationshipEvidence(
        source=place.source,
        category=place.category,
        match=place.match,
        place=place.place,
        corpus=place.corpus,
        count=occurrences,
        at=place.at,
    )
