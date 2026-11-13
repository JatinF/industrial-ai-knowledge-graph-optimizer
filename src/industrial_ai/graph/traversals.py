"""Dependency walks used by the asset API and the production-dependency query."""

from industrial_ai.graph.repository import OperationalGraph


def dependencies(graph: OperationalGraph, asset_id: str) -> list[dict[str, str]]:
    if not graph.has(asset_id):
        return []
    rows: list[dict[str, str]] = []
    for edge in graph.edges:
        if edge.src == asset_id:
            other = graph.get(edge.dst)
            rows.append(
                {
                    "asset_id": asset_id,
                    "direction": "out",
                    "relationship": edge.rel,
                    "other_id": other.id,
                    "other_label": other.label,
                }
            )
        elif edge.dst == asset_id:
            other = graph.get(edge.src)
            rows.append(
                {
                    "asset_id": asset_id,
                    "direction": "in",
                    "relationship": edge.rel,
                    "other_id": other.id,
                    "other_label": other.label,
                }
            )
    return rows


def production_dependencies(graph: OperationalGraph) -> list[dict[str, object]]:
    """Production order, the product it makes, and machines that also make it."""

    rows: list[dict[str, object]] = []
    for order in graph.nodes("ProductionOrder"):
        products = [edge.dst for edge in graph.outgoing(order.id, "PRODUCES")]
        for product_id in products:
            machines = [edge.src for edge in graph.incoming(product_id, "PRODUCES")]
            machines = [item for item in machines if graph.get(item).label == "Machine"]
            rows.append(
                {
                    "production_order": order.id,
                    "product_id": product_id,
                    "machines": sorted(set(machines)),
                }
            )
    return rows
