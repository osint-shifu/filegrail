from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ElementTree

from filegrail.graph import Graph, Node, Relationship, RelationshipEvidence
from filegrail.graph_export import render_graph_csv, render_graphml

GRAPHML = "http://graphml.graphdrawing.org/xmlns"


def _graph() -> Graph:
    evidence = RelationshipEvidence(
        source="document-metadata",
        place="document metadata · Author",
        corpus="metadata",
        count=1,
        category="metadata",
        match="embedded",
    )
    return Graph(
        nodes=(
            Node("file:/case/My Report.pdf", "file", "/case/My Report.pdf"),
            Node("email:anna@example.org", "email", "Anna@Example.org", "anna@example.org"),
        ),
        relationships=(
            Relationship(
                "file:/case/My Report.pdf",
                "email:anna@example.org",
                "has identifier",
                1,
                (evidence,),
            ),
        ),
    )


def test_graphml_uses_safe_export_ids_and_keeps_original_ids_as_data():
    root = ElementTree.fromstring(render_graphml(_graph()))
    nodes = root.findall(f".//{{{GRAPHML}}}node")
    edges = root.findall(f".//{{{GRAPHML}}}edge")

    assert [node.get("id") for node in nodes] == ["n0", "n1"]
    assert edges[0].get("source") == "n0"
    assert edges[0].get("target") == "n1"
    data = {
        item.get("key"): item.text for node in nodes for item in node.findall(f"{{{GRAPHML}}}data")
    }
    assert data["node_id"] == "email:anna@example.org"


def test_graphml_edge_evidence_is_machine_readable_json():
    root = ElementTree.fromstring(render_graphml(_graph()))
    edge = root.find(f".//{{{GRAPHML}}}edge")
    assert edge is not None
    data = {item.get("key"): item.text for item in edge.findall(f"{{{GRAPHML}}}data")}

    evidence = json.loads(data["edge_evidence"] or "[]")
    assert evidence[0]["source"] == "document-metadata"
    assert evidence[0]["match"] == {"method": "embedded"}


def test_csv_has_one_relationship_per_row_with_endpoint_data():
    rows = list(csv.DictReader(io.StringIO(render_graph_csv(_graph()))))

    assert len(rows) == 1
    assert rows[0]["source_id"] == "file:/case/My Report.pdf"
    assert rows[0]["source_type"] == "file"
    assert rows[0]["target_id"] == "email:anna@example.org"
    assert rows[0]["kind"] == "has identifier"
    assert json.loads(rows[0]["evidence"])[0]["category"] == "metadata"
