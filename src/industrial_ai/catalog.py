"""Deterministic operational catalog.

The hand scenario is the only network the allocation proof uses. The extra
products, machines, suppliers, and orders exist so dependency queries have a
realistic shape. Random choices use seed 7. Extra machines do not produce
PRODUCT-A, so they cannot change the hand-checked optimum.
"""

import random

from industrial_ai.domain.entities import (
    ALTERNATE,
    BACKUP,
    LINE_A,
    LOT,
    MATERIAL,
    ORDER,
    OTHER_ORDER,
    OVEN,
    PLANT_A,
    PLANT_B,
    PLANT_B_PRESS,
    PLANT_C,
    PRESS,
    PRODUCT_A,
    PRODUCT_B,
    PRODUCTION_ORDER,
    ROUTE,
    WAREHOUSE,
)
from industrial_ai.graph.repository import OperationalGraph

SEED = 7
EDGE_ATTR = {
    "valid_from": "2026-01-01",
    "valid_to": "",
    "source_system": "synthetic-catalog",
}


def _products() -> list[str]:
    names = [PRODUCT_A, PRODUCT_B, "PRODUCT-C"]
    names.extend(f"PRODUCT-{index:02d}" for index in range(4, 26))
    return names


def _materials() -> list[str]:
    names = [MATERIAL]
    names.extend(f"MAT-{index:02d}" for index in range(2, 26))
    return names


def _machines() -> list[tuple[str, str, str, str]]:
    rows = [
        (PRESS, PLANT_A, LINE_A, "press"),
        (BACKUP, PLANT_A, LINE_A, "press"),
        (ALTERNATE, PLANT_A, LINE_A, "mill"),
        (PLANT_B_PRESS, PLANT_B, "LINE-B1", "press"),
        (OVEN, PLANT_C, "LINE-C1", "oven"),
    ]
    for index in range(6, 21):
        plant = (PLANT_A, PLANT_B, PLANT_C)[(index - 6) % 3]
        line = {PLANT_A: LINE_A, PLANT_B: "LINE-B1", PLANT_C: "LINE-C1"}[plant]
        rows.append((f"MACH-{index:02d}", plant, line, "cell"))
    return rows


def build_catalog() -> OperationalGraph:
    rng = random.Random(SEED)
    graph = OperationalGraph()
    products = _products()
    materials = _materials()
    non_a = [item for item in products if item != PRODUCT_A]
    costs = {PLANT_A: 3, PLANT_B: 2, PLANT_C: 5}
    for plant, location in ((PLANT_A, "harbor"), (PLANT_B, "inland"), (PLANT_C, "south")):
        graph.add_node(
            "Factory",
            plant,
            location=location,
            status="UP",
            cost_per_unit=costs[plant],
            source_system="synthetic-erp",
        )
    for plant, line, shift in (
        (PLANT_A, LINE_A, "A"),
        (PLANT_B, "LINE-B1", "A"),
        (PLANT_C, "LINE-C1", "B"),
    ):
        graph.add_node(
            "ProductionLine", line, shift=shift, status="UP", source_system="synthetic-mes"
        )
        graph.add_edge(plant, "HAS_LINE", line, **EDGE_ATTR)
    for machine_id, plant, line, kind in _machines():
        graph.add_node(
            "Machine",
            machine_id,
            machine_type=kind,
            state="UP",
            source_sequence=0,
            occurred_at="",
            source_system="synthetic-mes",
            alternate_for=PRESS if machine_id == ALTERNATE else "",
        )
        graph.add_edge(line, "HAS_MACHINE", machine_id, **EDGE_ATTR)
    for index, material in enumerate(materials):
        graph.add_node(
            "Material",
            material,
            unit="each",
            cost=10 + index,
            source_system="synthetic-erp",
        )
    for product in products:
        graph.add_node("Product", product, product_id=product, source_system="synthetic-plm")
    graph.add_edge(PRESS, "PRODUCES", PRODUCT_A, capacity_per_shift=6, **EDGE_ATTR)
    graph.add_edge(BACKUP, "PRODUCES", PRODUCT_A, capacity_per_shift=2, **EDGE_ATTR)
    graph.add_edge(PLANT_B_PRESS, "PRODUCES", PRODUCT_A, capacity_per_shift=6, **EDGE_ATTR)
    for offset, product in enumerate(non_a[:10]):
        graph.add_edge(OVEN, "PRODUCES", product, capacity_per_shift=4, **EDGE_ATTR)
        graph.add_edge(
            ALTERNATE,
            "PRODUCES",
            non_a[(offset + 10) % len(non_a)],
            capacity_per_shift=5,
            **EDGE_ATTR,
        )
    for machine_id, _plant, _line, _kind in _machines():
        if machine_id in {PRESS, BACKUP, PLANT_B_PRESS, OVEN, ALTERNATE}:
            continue
        for product in non_a:
            graph.add_edge(machine_id, "PRODUCES", product, capacity_per_shift=1, **EDGE_ATTR)
    graph.add_edge(PRODUCT_A, "REQUIRES", MATERIAL, quantity_per_unit=1, **EDGE_ATTR)
    for index, product in enumerate(non_a):
        for slot in range(8):
            material = materials[(index + slot) % len(materials)]
            if product == PRODUCT_A:
                continue
            graph.add_edge(product, "REQUIRES", material, quantity_per_unit=1, **EDGE_ATTR)
    for index in range(1, 9):
        supplier = f"SUP-{index:03d}"
        reliability = 90 + (index % 5)
        graph.add_node(
            "Supplier",
            supplier,
            lead_time_days=3 + index,
            reliability=reliability,
            status="AVAILABLE",
            source_sequence=0,
            occurred_at="",
            source_system="synthetic-erp",
        )
        for material in materials:
            inbound = 0
            graph.add_edge(
                supplier,
                "SUPPLIES",
                material,
                inbound_quantity=inbound,
                **EDGE_ATTR,
            )
    warehouses = [WAREHOUSE, "WH-SOUTH", "WH-EAST"]
    for name, location in zip(warehouses, ("north", "south", "east"), strict=True):
        graph.add_node(
            "Warehouse",
            name,
            location=location,
            storage_capacity=1000,
            source_system="synthetic-erp",
        )
    graph.add_node(
        "InventoryLot",
        LOT,
        quantity=14,
        expiry="2027-06-01",
        location=WAREHOUSE,
        material_id=MATERIAL,
        source_system="synthetic-erp",
    )
    graph.add_edge(WAREHOUSE, "STORES", LOT, **EDGE_ATTR)
    graph.add_edge(LOT, "OF_MATERIAL", MATERIAL, **EDGE_ATTR)
    for index, material in enumerate(materials[1:], start=2):
        lot_id = f"LOT-{1000 + index}"
        warehouse = warehouses[index % len(warehouses)]
        graph.add_node(
            "InventoryLot",
            lot_id,
            quantity=20 + rng.randrange(10),
            expiry="2027-06-01",
            location=warehouse,
            material_id=material,
            source_system="synthetic-erp",
        )
        graph.add_edge(warehouse, "STORES", lot_id, **EDGE_ATTR)
        graph.add_edge(lot_id, "OF_MATERIAL", material, **EDGE_ATTR)
    for index, product in enumerate(products):
        order_id = f"PO-{1001 + index}"
        plant = PLANT_A if product == PRODUCT_A else (PLANT_A, PLANT_B, PLANT_C)[index % 3]
        graph.add_node(
            "ProductionOrder",
            order_id,
            quantity=10,
            priority=1 if order_id == PRODUCTION_ORDER else 3,
            deadline="2026-11-20",
            product_id=product,
            source_system="synthetic-erp",
        )
        graph.add_edge(order_id, "PRODUCES", product, **EDGE_ATTR)
        graph.add_edge(order_id, "SCHEDULED_AT", plant, **EDGE_ATTR)
        machine = PRESS if product == PRODUCT_A else _machines()[index % 20][0]
        if machine in {PRESS, BACKUP, PLANT_B_PRESS} and product != PRODUCT_A:
            machine = OVEN
        graph.add_edge(order_id, "USES", machine, **EDGE_ATTR)
    graph.add_node(
        "CustomerOrder",
        ORDER,
        quantity=10,
        destination=WAREHOUSE,
        due_date="2026-11-14",
        priority=1,
        product_id=PRODUCT_A,
        source_sequence=0,
        occurred_at="",
        source_system="synthetic-erp",
    )
    graph.add_edge(ORDER, "REQUESTS", PRODUCT_A, **EDGE_ATTR)
    graph.add_edge(ORDER, "DESTINED_TO", WAREHOUSE, **EDGE_ATTR)
    graph.add_node(
        "CustomerOrder",
        OTHER_ORDER,
        quantity=4,
        destination="WH-SOUTH",
        due_date="2026-11-18",
        priority=2,
        product_id=PRODUCT_B,
        source_sequence=0,
        occurred_at="",
        source_system="synthetic-erp",
    )
    graph.add_edge(OTHER_ORDER, "REQUESTS", PRODUCT_B, **EDGE_ATTR)
    graph.add_edge(OTHER_ORDER, "DESTINED_TO", "WH-SOUTH", **EDGE_ATTR)
    for seq in range(2003, 2051):
        order_id = f"CO-{seq}"
        product = non_a[(seq - 2003) % len(non_a)]
        warehouse = warehouses[seq % len(warehouses)]
        graph.add_node(
            "CustomerOrder",
            order_id,
            quantity=1 + rng.randrange(5),
            destination=warehouse,
            due_date="2026-11-21",
            priority=3,
            product_id=product,
            source_sequence=0,
            occurred_at="",
            source_system="synthetic-erp",
        )
        graph.add_edge(order_id, "REQUESTS", product, **EDGE_ATTR)
        graph.add_edge(order_id, "DESTINED_TO", warehouse, **EDGE_ATTR)
    routes = (
        (ROUTE, WAREHOUSE, 20, 3, 1),
        ("ROUTE-02", "WH-SOUTH", 12, 4, 2),
        ("ROUTE-03", "WH-EAST", 12, 5, 2),
    )
    for route_id, warehouse, capacity, cost, lead in routes:
        graph.add_node(
            "TransportRoute",
            route_id,
            lead_time=lead,
            capacity=capacity,
            cost=cost,
            source_system="synthetic-logistics",
        )
        graph.add_edge(route_id, "CONNECTS_TO", warehouse, **EDGE_ATTR)
    return graph
