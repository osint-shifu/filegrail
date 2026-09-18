"""A picture of the evidence graph: which nodes to draw, and where.

The whole graph is in the JSON and the exports. A picture of all of it would
be a hairball, so this draws the part that carries the shape: the files, the
people and devices, and the identifiers shared between files, up to a fixed
number of nodes. Positions come from a force-directed layout run the same way
every time, so the same case draws the same picture.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .graph import Graph

#: Enough to show how a case hangs together; past this a picture stops being
#: readable and the table below it is the better tool.
MAX_NODES = 120

WIDTH = 960
HEIGHT = 560
_MARGIN = 36
_ITERATIONS = 90

#: Node types drawn before identifiers of the same degree: a person or a
#: camera in a case is worth a place in the picture more than one more URL.
_PRIORITY = {"file": 0, "person": 1, "device": 1, "camera_model": 1, "org": 1, "handle": 1}


@dataclass(slots=True)
class Drawn:
    id: str
    type: str
    value: str
    degree: int
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class Picture:
    nodes: list[Drawn]
    #: Pairs of indexes into `nodes`, with the relationship kind.
    edges: list[tuple[int, int, str]]
    #: How many connected nodes the picture leaves to the table.
    left_out: int


def picture(graph: Graph) -> Picture | None:
    """The drawable part of the graph, laid out, or None when there is nothing to draw."""
    if not graph.relationships:
        return None
    degree: Counter[str] = Counter()
    for edge in graph.relationships:
        degree[edge.source] += 1
        degree[edge.target] += 1
    by_id = {node.id: node for node in graph.nodes}

    ranked = sorted(
        degree,
        key=lambda node_id: (
            -degree[node_id],
            _PRIORITY.get(by_id[node_id].type, 2) if node_id in by_id else 2,
            node_id,
        ),
    )
    kept = [node_id for node_id in ranked[:MAX_NODES] if node_id in by_id]
    index = {node_id: at for at, node_id in enumerate(kept)}
    edges = _edges(graph, index)
    touched = {a for a, _, _ in edges} | {b for _, b, _ in edges}
    if not touched:
        return None

    # A node whose only neighbour was left out is left out too: alone in the
    # picture it would say nothing.
    kept = [node_id for node_id in kept if index[node_id] in touched]
    index = {node_id: at for at, node_id in enumerate(kept)}
    nodes = [
        Drawn(node_id, by_id[node_id].type, by_id[node_id].value, degree[node_id])
        for node_id in kept
    ]
    edges = _edges(graph, index)
    _layout(nodes, [(a, b) for a, b, _ in edges])
    return Picture(nodes, edges, len(degree) - len(nodes))


def _edges(graph: Graph, index: dict[str, int]) -> list[tuple[int, int, str]]:
    return sorted(
        {
            (index[edge.source], index[edge.target], edge.kind)
            for edge in graph.relationships
            if edge.source in index and edge.target in index and edge.source != edge.target
        }
    )


def _layout(nodes: list[Drawn], edges: list[tuple[int, int]]) -> None:
    """Fruchterman-Reingold, seeded by order rather than by chance."""
    count = len(nodes)
    if count == 1:
        nodes[0].x, nodes[0].y = WIDTH / 2, HEIGHT / 2
        return
    area = (WIDTH - 2 * _MARGIN) * (HEIGHT - 2 * _MARGIN)
    k = math.sqrt(area / count)
    xs = [WIDTH / 2 + math.cos(2 * math.pi * at / count) * (WIDTH / 3) for at in range(count)]
    ys = [HEIGHT / 2 + math.sin(2 * math.pi * at / count) * (HEIGHT / 3) for at in range(count)]
    heat = WIDTH / 8
    cooling = heat / (_ITERATIONS + 1)

    for _ in range(_ITERATIONS):
        dx = [0.0] * count
        dy = [0.0] * count
        for a in range(count):
            for b in range(a + 1, count):
                ddx = xs[a] - xs[b]
                ddy = ys[a] - ys[b]
                dist = math.hypot(ddx, ddy) or 0.01
                push = k * k / dist
                dx[a] += ddx / dist * push
                dy[a] += ddy / dist * push
                dx[b] -= ddx / dist * push
                dy[b] -= ddy / dist * push
        for a, b in edges:
            ddx = xs[a] - xs[b]
            ddy = ys[a] - ys[b]
            dist = math.hypot(ddx, ddy) or 0.01
            pull = dist * dist / k
            dx[a] -= ddx / dist * pull
            dy[a] -= ddy / dist * pull
            dx[b] += ddx / dist * pull
            dy[b] += ddy / dist * pull
        # A mild pull to the centre keeps disconnected components from drifting apart.
        for at in range(count):
            dx[at] -= (xs[at] - WIDTH / 2) * 0.02
            dy[at] -= (ys[at] - HEIGHT / 2) * 0.02
            length = math.hypot(dx[at], dy[at]) or 0.01
            step = min(length, heat)
            xs[at] = min(WIDTH - _MARGIN, max(_MARGIN, xs[at] + dx[at] / length * step))
            ys[at] = min(HEIGHT - _MARGIN, max(_MARGIN, ys[at] + dy[at] / length * step))
        heat -= cooling

    # Fill the frame: the layout tends to leave the corners empty.
    low_x, high_x = min(xs), max(xs)
    low_y, high_y = min(ys), max(ys)
    span_x = (high_x - low_x) or 1.0
    span_y = (high_y - low_y) or 1.0
    for at, node in enumerate(nodes):
        node.x = round(_MARGIN + (xs[at] - low_x) / span_x * (WIDTH - 2 * _MARGIN), 1)
        node.y = round(_MARGIN + (ys[at] - low_y) / span_y * (HEIGHT - 2 * _MARGIN), 1)
