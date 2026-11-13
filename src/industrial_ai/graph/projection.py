"""Build an allocation snapshot from the current graph projection.

The snapshot is a copy. A later machine update changes the graph and the
store revision, and it does not rewrite a plan that already captured this copy.
"""

from industrial_ai.domain.entities import (
    ALTERNATE,
    MATERIAL,
    PLANT_A,
    PLANT_B,
    PRESS,
    PRODUCT_A,
    ROUTE,
)
from industrial_ai.graph.impact_analysis import affected_orders
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.optimization.model_builder import AllocationSnapshot, PlantCapacity


def _as_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise TypeError(label)
    return value


def plant_product_capacity(graph: OperationalGraph, plant_id: str, product_id: str) -> int:
    total = 0
    for line in graph.outgoing(plant_id, "HAS_LINE"):
        for link in graph.outgoing(line.dst, "HAS_MACHINE"):
            machine = graph.get(link.dst)
            if machine.props.get("state") != "UP":
                continue
            for produced in graph.outgoing(machine.id, "PRODUCES"):
                if produced.dst != product_id:
                    continue
                total += _as_int(produced.props["capacity_per_shift"], machine.id)
    return total


def material_units(graph: OperationalGraph, material_id: str) -> int:
    total = 0
    for edge in graph.incoming(material_id, "OF_MATERIAL"):
        lot = graph.get(edge.src)
        total += _as_int(lot.props["quantity"], lot.id)
    for edge in graph.incoming(material_id, "SUPPLIES"):
        supplier = graph.get(edge.src)
        if supplier.props.get("status") == "DELAYED":
            continue
        inbound = edge.props.get("inbound_quantity", 0)
        if type(inbound) is int:
            total += inbound
    return total


def product_demand(graph: OperationalGraph, product_id: str) -> int:
    total = 0
    for edge in graph.incoming(product_id, "REQUESTS"):
        order = graph.get(edge.src)
        if order.label != "CustomerOrder":
            continue
        total += _as_int(order.props["quantity"], order.id)
    return total


def down_machines(graph: OperationalGraph) -> tuple[str, ...]:
    names = [node.id for node in graph.nodes("Machine") if node.props.get("state") == "DOWN"]
    return tuple(sorted(names))


def candidate_orders(graph: OperationalGraph, product_id: str) -> tuple[str, ...]:
    found: set[str] = set()
    for machine in down_machines(graph):
        for row in affected_orders(graph, machine):
            if row["affected_product"] != product_id:
                continue
            orders = row["candidate_orders"]
            if isinstance(orders, list):
                found.update(str(item) for item in orders)
    if not found:
        for edge in graph.incoming(product_id, "REQUESTS"):
            order = graph.get(edge.src)
            if order.label == "CustomerOrder":
                found.add(order.id)
    return tuple(sorted(found))


def alternate_available(graph: OperationalGraph) -> bool:
    if not graph.has(ALTERNATE):
        return False
    return graph.get(ALTERNATE).props.get("state") == "UP"


def press_down(graph: OperationalGraph) -> bool:
    if not graph.has(PRESS):
        return False
    return graph.get(PRESS).props.get("state") != "UP"


def build_snapshot(
    graph: OperationalGraph,
    *,
    revision: int,
    allow_late: bool,
    forbid_shortfall: bool,
    product_id: str = PRODUCT_A,
    material_id: str = MATERIAL,
) -> AllocationSnapshot:
    plants: list[PlantCapacity] = []
    for plant_id in (PLANT_A, PLANT_B):
        plant = graph.get(plant_id)
        plants.append(
            PlantCapacity(
                plant_id,
                plant_product_capacity(graph, plant_id, product_id),
                _as_int(plant.props["cost_per_unit"], plant_id),
            )
        )
    route = graph.get(ROUTE)
    per_unit = 1
    for edge in graph.outgoing(product_id, "REQUIRES"):
        if edge.dst == material_id:
            raw = edge.props.get("quantity_per_unit", 1)
            if type(raw) is int and raw > 0:
                per_unit = raw
    available = material_units(graph, material_id) // per_unit
    return AllocationSnapshot(
        revision=revision,
        product_id=product_id,
        demand=product_demand(graph, product_id),
        materials=available,
        plants=tuple(plants),
        route_capacity=_as_int(route.props["capacity"], ROUTE),
        transport_cost_per_unit=_as_int(route.props["cost"], ROUTE),
        allow_late=allow_late,
        forbid_shortfall=forbid_shortfall,
        down_machines=down_machines(graph),
        candidate_orders=candidate_orders(graph, product_id),
    )
