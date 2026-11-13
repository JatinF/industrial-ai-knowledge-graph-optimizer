"""Operational graph shape, entity resolution, and candidate-order impact."""

from pathlib import Path

from industrial_ai.catalog import build_catalog
from industrial_ai.domain.entities import (
    IOT,
    LOT,
    MATERIAL,
    MES,
    ORDER,
    OTHER_ORDER,
    PLANT_A,
    PRESS,
    PRODUCT_A,
    PRODUCT_B,
    ROUTE,
    SUPPLIER,
)
from industrial_ai.graph.impact_analysis import (
    affected_orders,
    material_shortage,
    supplier_impact,
    transport_disruption,
)
from industrial_ai.graph.projection import build_snapshot, plant_product_capacity
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.graph.traversals import production_dependencies
from industrial_ai.ingestion.entity_resolution import bind_alias, resolve
from industrial_ai.ingestion.iot_adapter import canonical_machine
from industrial_ai.paths import repo_root


def test_catalog_counts_and_hand_relationships() -> None:
    graph = build_catalog()
    counts = graph.counts()
    assert counts["entities"] == 190
    assert counts["relationships"] == 1027
    assert counts["label_Factory"] == 3
    assert counts["label_Supplier"] == 8
    assert counts["label_Warehouse"] == 3
    assert counts["label_Machine"] == 20
    assert counts["label_Product"] == 25
    assert counts["label_CustomerOrder"] == 50
    assert plant_product_capacity(graph, PLANT_A, PRODUCT_A) == 8
    assert plant_product_capacity(graph, "PLANT-B", PRODUCT_A) == 6
    assert plant_product_capacity(graph, "PLANT-C", PRODUCT_A) == 0
    assert graph.get(LOT).props["quantity"] == 14
    assert any(edge.rel == "HAS_LINE" and edge.src == PLANT_A for edge in graph.edges)
    assert any(
        edge.rel == "REQUIRES" and edge.src == PRODUCT_A and edge.dst == MATERIAL
        for edge in graph.edges
    )
    assert any(
        edge.rel == "SUPPLIES" and edge.src == SUPPLIER and edge.dst == MATERIAL
        for edge in graph.edges
    )
    assert any(edge.rel == "CONNECTS_TO" and edge.src == ROUTE for edge in graph.edges)


def test_machine_identifier_is_unique() -> None:
    graph = OperationalGraph()
    graph.add_node("Machine", PRESS, state="UP")
    try:
        graph.add_node("Machine", PRESS, state="DOWN")
    except ValueError as exc:
        assert PRESS in str(exc)
    else:
        raise AssertionError("duplicate machine id was accepted")


def test_entity_resolution_keeps_both_source_identifiers() -> None:
    graph = build_catalog()
    bind_alias(graph, source_system=MES, source_id=PRESS, canonical_id=PRESS)
    bind_alias(graph, source_system=IOT, source_id="SYN-SENSOR-220", canonical_id=PRESS)
    assert resolve(graph, MES, PRESS) == PRESS
    assert resolve(graph, IOT, "SYN-SENSOR-220") == PRESS
    assert canonical_machine(graph, "SYN-SENSOR-220") == PRESS
    sources = graph.get(PRESS).props["source_identifiers"]
    assert isinstance(sources, list)
    assert {"source_system": MES, "source_id": PRESS} in sources
    assert {"source_system": IOT, "source_id": "SYN-SENSOR-220"} in sources
    assert len(graph.nodes("Machine")) == 20


def test_press_failure_candidates_exclude_the_other_product() -> None:
    graph = build_catalog()
    rows = affected_orders(graph, PRESS)
    assert len(rows) == 1
    assert rows[0]["affected_product"] == PRODUCT_A
    assert rows[0]["candidate_orders"] == [ORDER]
    assert OTHER_ORDER not in rows[0]["candidate_orders"]
    product_a = next(
        row for row in material_shortage(graph, MATERIAL) if row["product_id"] == PRODUCT_A
    )
    assert product_a["candidate_orders"] == [ORDER]
    supplier_rows = [
        row
        for row in supplier_impact(graph, SUPPLIER)
        if row["material_id"] == MATERIAL and row["product_id"] == PRODUCT_A
    ]
    assert supplier_rows[0]["candidate_orders"] == [ORDER]
    route_rows = transport_disruption(graph, ROUTE)
    assert ORDER in route_rows[0]["candidate_orders"]
    assert OTHER_ORDER not in route_rows[0]["candidate_orders"]
    produced = next(
        row for row in production_dependencies(graph) if row["production_order"] == "PO-1001"
    )
    assert produced["product_id"] == PRODUCT_A
    assert PRESS in produced["machines"]


def test_snapshot_uses_only_up_machines() -> None:
    graph = build_catalog()
    bind_alias(graph, source_system=MES, source_id=PRESS, canonical_id=PRESS)
    healthy = build_snapshot(graph, revision=1, allow_late=True, forbid_shortfall=False)
    assert healthy.demand == 10
    assert healthy.materials == 14
    assert {plant.plant_id: plant.capacity for plant in healthy.plants} == {
        "PLANT-A": 8,
        "PLANT-B": 6,
    }
    graph.update(PRESS, state="DOWN")
    failed = build_snapshot(graph, revision=2, allow_late=True, forbid_shortfall=False)
    assert {plant.plant_id: plant.capacity for plant in failed.plants} == {
        "PLANT-A": 2,
        "PLANT-B": 6,
    }
    assert failed.candidate_orders == (ORDER,)
    assert PRODUCT_B not in failed.candidate_orders


def test_cypher_files_are_parameterized() -> None:
    root = repo_root()
    affected = (root / "graph" / "queries" / "affected_orders.cypher").read_text(encoding="utf-8")
    assert "$machine_id" in affected
    assert "PRODUCES" in affected
    assert "REQUESTS" in affected
    schema = (root / "graph" / "schema.cypher").read_text(encoding="utf-8")
    assert "CREATE CONSTRAINT machine_id_unique IF NOT EXISTS" in schema
    assert "REQUIRE m.id IS UNIQUE" in schema
    for name in (
        "dependencies.cypher",
        "supplier_impact.cypher",
        "material_shortage.cypher",
        "transport_disruption.cypher",
        "production_dependencies.cypher",
    ):
        text = (root / "graph" / "queries" / name).read_text(encoding="utf-8")
        assert "$" in text
        assert "MATCH" in text
    assert Path(root / "graph" / "schema.cypher").is_file()
