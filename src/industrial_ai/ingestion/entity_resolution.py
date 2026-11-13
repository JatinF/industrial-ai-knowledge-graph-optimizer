"""Map a source identifier onto one canonical asset.

The original source identifier stays on the node. PRESS-220 from MES and
SYN-SENSOR-220 from IoT are the same machine.
"""

from industrial_ai.graph.repository import OperationalGraph


def bind_alias(
    graph: OperationalGraph,
    *,
    source_system: str,
    source_id: str,
    canonical_id: str,
) -> None:
    node = graph.get(canonical_id)
    graph.aliases[(source_system, source_id)] = canonical_id
    current = node.props.get("source_identifiers")
    rows: list[object]
    if isinstance(current, list):
        rows = list(current)
    else:
        rows = []
    entry: dict[str, str] = {"source_system": source_system, "source_id": source_id}
    if entry not in rows:
        rows.append(entry)
    node.props["source_identifiers"] = rows


def resolve(graph: OperationalGraph, source_system: str, source_id: str) -> str | None:
    canonical = graph.aliases.get((source_system, source_id))
    if canonical is not None:
        return canonical
    if graph.has(source_id):
        return source_id
    return None
