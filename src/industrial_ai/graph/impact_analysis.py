"""Impact queries.

These return candidate orders and resources. They do not decide the plan.
The optimizer still has to look at remaining capacity, inventory, routes,
and deadlines. The shapes match the parameterized Cypher files.
"""

from industrial_ai.graph.repository import OperationalGraph


def affected_orders(graph: OperationalGraph, machine_id: str) -> list[dict[str, object]]:
    if not graph.has(machine_id):
        return []
    rows: list[dict[str, object]] = []
    for edge in graph.outgoing(machine_id, "PRODUCES"):
        product = graph.get(edge.dst)
        if product.label != "Product":
            continue
        orders: list[str] = []
        for request in graph.incoming(product.id, "REQUESTS"):
            order = graph.get(request.src)
            if order.label == "CustomerOrder":
                orders.append(order.id)
        rows.append(
            {
                "failed_machine": machine_id,
                "affected_product": product.id,
                "candidate_orders": sorted(set(orders)),
            }
        )
    return rows


def supplier_impact(graph: OperationalGraph, supplier_id: str) -> list[dict[str, object]]:
    if not graph.has(supplier_id):
        return []
    rows: list[dict[str, object]] = []
    for supply in graph.outgoing(supplier_id, "SUPPLIES"):
        material = graph.get(supply.dst)
        if material.label != "Material":
            continue
        for requires in graph.incoming(material.id, "REQUIRES"):
            product = graph.get(requires.src)
            if product.label != "Product":
                continue
            orders = [
                graph.get(request.src).id
                for request in graph.incoming(product.id, "REQUESTS")
                if graph.get(request.src).label == "CustomerOrder"
            ]
            rows.append(
                {
                    "supplier_id": supplier_id,
                    "material_id": material.id,
                    "product_id": product.id,
                    "candidate_orders": sorted(set(orders)),
                }
            )
    return rows


def material_shortage(graph: OperationalGraph, material_id: str) -> list[dict[str, object]]:
    if not graph.has(material_id):
        return []
    rows: list[dict[str, object]] = []
    for requires in graph.incoming(material_id, "REQUIRES"):
        product = graph.get(requires.src)
        if product.label != "Product":
            continue
        orders = [
            graph.get(request.src).id
            for request in graph.incoming(product.id, "REQUESTS")
            if graph.get(request.src).label == "CustomerOrder"
        ]
        rows.append(
            {
                "material_id": material_id,
                "product_id": product.id,
                "candidate_orders": sorted(set(orders)),
            }
        )
    return rows


def transport_disruption(graph: OperationalGraph, route_id: str) -> list[dict[str, object]]:
    if not graph.has(route_id):
        return []
    rows: list[dict[str, object]] = []
    for link in graph.outgoing(route_id, "CONNECTS_TO"):
        warehouse = graph.get(link.dst)
        if warehouse.label != "Warehouse":
            continue
        orders = [
            graph.get(edge.src).id
            for edge in graph.incoming(warehouse.id, "DESTINED_TO")
            if graph.get(edge.src).label == "CustomerOrder"
        ]
        rows.append(
            {
                "route_id": route_id,
                "warehouse_id": warehouse.id,
                "candidate_orders": sorted(set(orders)),
            }
        )
    return rows
