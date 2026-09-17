"""GraphML and CSV serialization for an investigation graph."""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ElementTree

from .graph import Graph

_GRAPHML = "http://graphml.graphdrawing.org/xmlns"
ElementTree.register_namespace("", _GRAPHML)


def render_graphml(graph: Graph) -> str:
    """Serialize ``graph`` as dependency-free, interoperable GraphML."""
    root = ElementTree.Element(f"{{{_GRAPHML}}}graphml")
    for key, scope, name, value_type in (
        ("node_id", "node", "id", "string"),
        ("node_type", "node", "type", "string"),
        ("node_value", "node", "value", "string"),
        ("node_normalized", "node", "normalized", "string"),
        ("node_private", "node", "private", "boolean"),
        ("edge_kind", "edge", "kind", "string"),
        ("edge_count", "edge", "count", "int"),
        ("edge_evidence", "edge", "evidence", "string"),
    ):
        ElementTree.SubElement(
            root,
            f"{{{_GRAPHML}}}key",
            {"id": key, "for": scope, "attr.name": name, "attr.type": value_type},
        )

    document = ElementTree.SubElement(
        root, f"{{{_GRAPHML}}}graph", {"id": "filegrail", "edgedefault": "directed"}
    )
    exported_ids = {node.id: f"n{position}" for position, node in enumerate(graph.nodes)}
    for node in graph.nodes:
        element = ElementTree.SubElement(
            document, f"{{{_GRAPHML}}}node", {"id": exported_ids[node.id]}
        )
        _data(element, "node_id", node.id)
        _data(element, "node_type", node.type)
        _data(element, "node_value", node.value)
        if node.normalized is not None:
            _data(element, "node_normalized", node.normalized)
        if node.private is not None:
            _data(element, "node_private", str(node.private).lower())

    for position, relationship in enumerate(graph.relationships):
        edge = ElementTree.SubElement(
            document,
            f"{{{_GRAPHML}}}edge",
            {
                "id": f"e{position}",
                "source": exported_ids[relationship.source],
                "target": exported_ids[relationship.target],
            },
        )
        _data(edge, "edge_kind", relationship.kind)
        _data(edge, "edge_count", str(relationship.count))
        _data(
            edge,
            "edge_evidence",
            json.dumps(
                [item.to_dict() for item in relationship.evidence],
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )

    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(root, encoding="unicode", xml_declaration=True)


def render_graph_csv(graph: Graph) -> str:
    """Serialize one relationship per CSV row, including both endpoint nodes."""
    nodes = {node.id: node for node in graph.nodes}
    output = io.StringIO(newline="")
    fields = (
        "source_id",
        "source_type",
        "source_value",
        "target_id",
        "target_type",
        "target_value",
        "kind",
        "count",
        "evidence",
    )
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for relationship in graph.relationships:
        source = nodes[relationship.source]
        target = nodes[relationship.target]
        writer.writerow(
            {
                "source_id": source.id,
                "source_type": source.type,
                "source_value": source.value,
                "target_id": target.id,
                "target_type": target.type,
                "target_value": target.value,
                "kind": relationship.kind,
                "count": relationship.count,
                "evidence": json.dumps(
                    [item.to_dict() for item in relationship.evidence],
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            }
        )
    return output.getvalue()


def _data(parent: ElementTree.Element, key: str, value: str) -> None:
    ElementTree.SubElement(parent, f"{{{_GRAPHML}}}data", {"key": key}).text = value
