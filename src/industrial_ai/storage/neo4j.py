"""Neo4j adapter.

The driver is constructed only after the URL gate returns local or remote.
Schema statements come from graph/schema.cypher. The impact query is the
parameterized text in graph/queries/affected_orders.cypher. Labels and
relationship types are whitelisted before they are interpolated, because
Cypher cannot parameterize them. Identifiers and properties are parameters.
"""

import json
import os
from typing import Any

from industrial_ai.graph.ontology import NODE_LABELS, RELATIONSHIPS
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.paths import repo_root
from industrial_ai.runtime_gates import gate, require_contact


def _statements(name: str) -> list[str]:
    raw = (repo_root() / "graph" / name).read_text(encoding="utf-8")
    kept = [line for line in raw.splitlines() if not line.strip().startswith("//")]
    return [part.strip() for part in "\n".join(kept).split(";") if part.strip()]


def _props(props: dict[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {}
    for key, value in props.items():
        if isinstance(value, str) or type(value) in {int, float, bool}:
            flat[key] = value
        else:
            flat[key] = json.dumps(value)
    return flat


def neo4j_status() -> str:
    return gate(os.environ.get("NEO4J_URI"))


def load_and_impact(graph: OperationalGraph, machine_id: str) -> dict[str, object]:
    status = neo4j_status()
    if status in {"not-run", "blocked"}:
        return {"status": status, "rows": []}
    url = require_contact(os.environ.get("NEO4J_URI"))
    user = os.environ.get("NEO4J_USER") or "neo4j"
    password = os.environ.get("NEO4J_PASSWORD") or ""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(url, auth=(user, password))
    try:
        with driver.session() as session:
            for statement in _statements("schema.cypher"):
                session.run(statement)

            def write(tx: Any) -> None:
                for node in graph.nodes():
                    if node.label not in NODE_LABELS:
                        raise RuntimeError("label is not in the ontology")
                    tx.run(
                        f"MERGE (n:{node.label} {{id: $id}}) SET n += $props",
                        id=node.id,
                        props=_props(node.props),
                    )
                for edge in graph.edges:
                    if edge.rel not in RELATIONSHIPS:
                        raise RuntimeError("relationship is not in the ontology")
                    statement = (
                        "MATCH (a {id: $src}), (b {id: $dst}) "
                        f"MERGE (a)-[r:{edge.rel}]->(b) SET r += $props"
                    )
                    tx.run(
                        statement,
                        src=edge.src,
                        dst=edge.dst,
                        props=_props(edge.props),
                    )

            session.execute_write(write)
            query = (repo_root() / "graph" / "queries" / "affected_orders.cypher").read_text(
                encoding="utf-8"
            )
            records = session.run(query, machine_id=machine_id).data()
        return {"status": "contacted", "rows": records}
    except Exception as exc:
        raise RuntimeError("neo4j request failed") from exc
    finally:
        driver.close()
