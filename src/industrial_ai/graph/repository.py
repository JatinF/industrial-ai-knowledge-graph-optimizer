"""Property graph held in process.

Neo4j is used when a local server is actually contacted. This graph is the
one the workstation demo and the unit tests walk. Machine identifiers are
unique, matching the Cypher uniqueness constraint.
"""

from dataclasses import dataclass, field

from industrial_ai.graph.ontology import NODE_LABELS, RELATIONSHIPS


@dataclass
class Node:
    label: str
    id: str
    props: dict[str, object] = field(default_factory=dict)


@dataclass
class Edge:
    src: str
    rel: str
    dst: str
    props: dict[str, object] = field(default_factory=dict)


class OperationalGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.aliases: dict[tuple[str, str], str] = {}
        self._out: dict[tuple[str, str], list[int]] = {}
        self._in: dict[tuple[str, str], list[int]] = {}

    def add_node(self, label: str, node_id: str, **props: object) -> Node:
        if label not in NODE_LABELS:
            raise ValueError(f"unknown label {label}")
        if node_id in self._nodes:
            raise ValueError(f"duplicate node id {node_id}")
        node = Node(label, node_id, dict(props))
        self._nodes[node_id] = node
        return node

    def update(self, node_id: str, **props: object) -> Node:
        node = self._nodes[node_id]
        node.props.update(props)
        return node

    def add_edge(self, src: str, rel: str, dst: str, **props: object) -> Edge:
        if rel not in RELATIONSHIPS:
            raise ValueError(f"unknown relationship {rel}")
        if src not in self._nodes or dst not in self._nodes:
            raise KeyError("edge endpoint is missing")
        edge = Edge(src, rel, dst, dict(props))
        index = len(self.edges)
        self.edges.append(edge)
        self._out.setdefault((src, rel), []).append(index)
        self._in.setdefault((dst, rel), []).append(index)
        return edge

    def get(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def has(self, node_id: str) -> bool:
        return node_id in self._nodes

    def nodes(self, label: str | None = None) -> list[Node]:
        rows = list(self._nodes.values())
        if label is None:
            return rows
        return [row for row in rows if row.label == label]

    def outgoing(self, node_id: str, rel: str) -> list[Edge]:
        return [self.edges[index] for index in self._out.get((node_id, rel), [])]

    def incoming(self, node_id: str, rel: str) -> list[Edge]:
        return [self.edges[index] for index in self._in.get((node_id, rel), [])]

    def counts(self) -> dict[str, int]:
        by_label: dict[str, int] = {}
        for node in self._nodes.values():
            by_label[node.label] = by_label.get(node.label, 0) + 1
        return {
            "entities": len(self._nodes),
            "relationships": len(self.edges),
            **{f"label_{name}": count for name, count in sorted(by_label.items())},
        }
