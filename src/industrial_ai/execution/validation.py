"""Rebuild a stored snapshot and grade the stored allocation again before execute."""

from typing import Any

from industrial_ai.optimization.allocation_solver import AllocationResult, Production, Shipment
from industrial_ai.optimization.feasibility import constraint_violations
from industrial_ai.optimization.model_builder import AllocationSnapshot, PlantCapacity


def snapshot_from_document(document: dict[str, Any]) -> AllocationSnapshot:
    raw = document["snapshot"]
    if not isinstance(raw, dict):
        raise TypeError("snapshot")
    plants = tuple(
        PlantCapacity(str(row["plant_id"]), int(row["capacity"]), int(row["cost_per_unit"]))
        for row in raw["plants"]
    )
    return AllocationSnapshot(
        revision=int(raw["revision"]),
        product_id=str(raw["product_id"]),
        demand=int(raw["demand"]),
        materials=int(raw["materials"]),
        plants=plants,
        route_capacity=int(raw["route_capacity"]),
        transport_cost_per_unit=int(raw["transport_cost_per_unit"]),
        allow_late=bool(raw["allow_late"]),
        forbid_shortfall=bool(raw["forbid_shortfall"]),
        down_machines=tuple(str(item) for item in raw["down_machines"]),
        candidate_orders=tuple(str(item) for item in raw["candidate_orders"]),
    )


def result_from_document(document: dict[str, Any]) -> AllocationResult:
    raw = document["allocation"]
    if not isinstance(raw, dict):
        raise TypeError("allocation")
    productions = tuple(
        Production(str(row["plant_id"]), int(row["period"]), int(row["quantity"]), int(row["cost"]))
        for row in raw["productions"]
    )
    shipments = tuple(
        Shipment(
            str(row["plant_id"]),
            int(row["period"]),
            int(row["quantity"]),
            int(row["arrives_period"]),
        )
        for row in raw["shipments"]
    )
    return AllocationResult(
        status=str(raw["status"]),
        objective=int(raw["objective"]),
        unmet=int(raw["unmet"]),
        late=int(raw["late"]),
        on_time=int(raw["on_time"]),
        production_cost=int(raw["production_cost"]),
        transport_cost=int(raw["transport_cost"]),
        productions=productions,
        shipments=shipments,
        wall_seconds=float(raw["wall_seconds"]),
        operational_requirement_met=bool(raw["operational_requirement_met"]),
    )


def recheck(document: dict[str, Any]) -> list[str]:
    return constraint_violations(snapshot_from_document(document), result_from_document(document))
