import json
from pathlib import Path

from filegrail.identify import MAX_RELATION_PLACES
from filegrail.models import EvidenceRecord, FileRecord
from filegrail.report import render_json


def _record(path: str, *evidence: EvidenceRecord) -> FileRecord:
    return FileRecord(path=path, size=10, mtime="2026-09-17T12:00:00Z", evidence=list(evidence))


def test_graph_is_emitted_with_pivots_and_keeps_structured_evidence():
    path = "/case/report.pdf"
    record = _record(
        path,
        EvidenceRecord(
            source="document-metadata",
            at="2026-09-17T11:00:00Z",
            fields={"Author": "analyst@example.org"},
        ),
    )

    payload = json.loads(render_json([record], Path("/case"), identify=True))

    nodes = {node["id"]: node for node in payload["graph"]["nodes"]}
    assert nodes["email:analyst@example.org"] == {
        "id": "email:analyst@example.org",
        "type": "email",
        "value": "analyst@example.org",
        "normalized": "analyst@example.org",
    }
    assert nodes[f"file:{path}"] == {"id": f"file:{path}", "type": "file", "value": path}

    relationship = next(
        edge
        for edge in payload["graph"]["relationships"]
        if edge["target"] == "email:analyst@example.org"
    )
    assert relationship == {
        "source": f"file:{path}",
        "target": "email:analyst@example.org",
        "kind": "has identifier",
        "count": 1,
        "evidence": [
            {
                "source": "document-metadata",
                "place": "document metadata · Author",
                "corpus": "metadata",
                "count": 1,
                "category": "metadata",
                "match": {"method": "embedded"},
                "at": "2026-09-17T11:00:00Z",
            }
        ],
    }


def test_one_file_to_identifier_edge_groups_independent_evidence():
    path = "/case/report.pdf"
    record = _record(
        path,
        EvidenceRecord(source="browser-download", url="https://example.org/report.pdf"),
        EvidenceRecord(source="document-metadata", fields={"Company": "example.org"}),
    )

    graph = json.loads(render_json([record], Path("/case"), identify=True))["graph"]
    relationship = next(
        edge for edge in graph["relationships"] if edge["target"] == "domain:example.org"
    )

    assert relationship["count"] == 2
    assert [item["source"] for item in relationship["evidence"]] == [
        "browser-download",
        "document-metadata",
    ]
    assert [item["category"] for item in relationship["evidence"]] == [
        "origin",
        "metadata",
    ]


def test_relationship_count_survives_a_shortened_place_list():
    path = "/case/list.txt"
    fields = {f"field-{number}": "ops@example.org" for number in range(MAX_RELATION_PLACES + 1)}
    record = _record(path, EvidenceRecord(source="document-metadata", fields=fields))

    graph = json.loads(render_json([record], Path("/case"), identify=True))["graph"]
    relationship = next(
        edge for edge in graph["relationships"] if edge["target"] == "email:ops@example.org"
    )

    assert relationship["count"] == MAX_RELATION_PLACES + 1
    assert len(relationship["evidence"]) == MAX_RELATION_PLACES


def test_graph_is_absent_without_pivots():
    payload = json.loads(render_json([_record("/case/a.txt")], Path("/case")))

    assert "graph" not in payload
