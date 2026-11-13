"""Write the deterministic catalog to CSV files and a Cypher seed."""

import csv
import json
from pathlib import Path

from industrial_ai.catalog import build_catalog
from industrial_ai.domain.entities import PRESS
from industrial_ai.graph.ontology import NODE_LABELS, RELATIONSHIPS
from industrial_ai.graph.repository import OperationalGraph


def _literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return "'" + escaped + "'"
    return "'" + json.dumps(value) + "'"


def to_cypher(graph: OperationalGraph) -> str:
    lines = [
        "// Generated from the deterministic catalog. Identifiers are synthetic.",
        "// The Neo4j driver path uses parameters. This file is the shell form.",
    ]
    for node in graph.nodes():
        if node.label not in NODE_LABELS:
            raise ValueError("label is not in the ontology")
        props = ", ".join(
            f"{key}: {_literal(value)}"
            for key, value in sorted(node.props.items())
            if isinstance(value, (str, int, bool))
        )
        lines.append(f"MERGE (:{node.label} {{id: {_literal(node.id)}, {props}}});")
    for edge in graph.edges:
        if edge.rel not in RELATIONSHIPS:
            raise ValueError("relationship is not in the ontology")
        lines.append(
            "MATCH (a {id: "
            + _literal(edge.src)
            + "}), (b {id: "
            + _literal(edge.dst)
            + "}) MERGE (a)-[:"
            + edge.rel
            + "]->(b);"
        )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def write_synthetic(root: Path) -> dict[str, int]:
    graph = build_catalog()
    folder = root / "datasets" / "synthetic"
    _write_csv(
        folder / "factories.csv",
        ["id", "location", "status", "cost_per_unit"],
        [
            [node.id, node.props["location"], node.props["status"], node.props["cost_per_unit"]]
            for node in graph.nodes("Factory")
        ],
    )
    _write_csv(
        folder / "machines.csv",
        ["id", "machine_type", "state", "alternate_for"],
        [
            [node.id, node.props["machine_type"], node.props["state"], node.props["alternate_for"]]
            for node in graph.nodes("Machine")
        ],
    )
    _write_csv(
        folder / "suppliers.csv",
        ["id", "lead_time_days", "reliability", "status"],
        [
            [node.id, node.props["lead_time_days"], node.props["reliability"], node.props["status"]]
            for node in graph.nodes("Supplier")
        ],
    )
    _write_csv(
        folder / "inventory.csv",
        ["id", "material_id", "quantity", "location", "expiry"],
        [
            [
                node.id,
                node.props["material_id"],
                node.props["quantity"],
                node.props["location"],
                node.props["expiry"],
            ]
            for node in graph.nodes("InventoryLot")
        ],
    )
    _write_csv(
        folder / "orders.csv",
        ["id", "product_id", "quantity", "destination", "due_date", "priority"],
        [
            [
                node.id,
                node.props["product_id"],
                node.props["quantity"],
                node.props["destination"],
                node.props["due_date"],
                node.props["priority"],
            ]
            for node in graph.nodes("CustomerOrder")
        ],
    )
    telemetry: list[list[object]] = []
    for machine in graph.nodes("Machine"):
        for hour, value in enumerate((10, 12, 14, 16)):
            telemetry.append([machine.id, f"2026-11-13T0{hour}:00:00Z", "vibration", value])
        if machine.id == PRESS:
            telemetry.append([PRESS, "2026-11-13T10:00:00Z", "vibration", 95])
    _write_csv(folder / "telemetry.csv", ["machine_id", "timestamp", "metric", "value"], telemetry)
    seed = root / "graph" / "seed.cypher"
    seed.write_text(to_cypher(graph), encoding="utf-8")
    return graph.counts()
