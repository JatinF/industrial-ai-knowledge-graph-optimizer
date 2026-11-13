"""Independent check of an allocation result against its snapshot.

The solver is not asked to grade its own answer. These checks recompute
capacity, material, route, lead time, and the objective identity.
"""

from industrial_ai.optimization.allocation_solver import AllocationResult
from industrial_ai.optimization.model_builder import AllocationSnapshot
from industrial_ai.optimization.objectives import LATE_PENALTY, STARTER_UNMET_PENALTY, UNMET_PENALTY


def constraint_violations(snapshot: AllocationSnapshot, result: AllocationResult) -> list[str]:
    if result.status not in {"OPTIMAL", "FEASIBLE"}:
        return []
    problems: list[str] = []
    if result.on_time < 0 or result.late < 0 or result.unmet < 0:
        problems.append("negative fulfillment variable")
    if result.on_time + result.late + result.unmet != snapshot.demand:
        problems.append("fulfillment does not balance demand")
    if not snapshot.allow_late and result.late != 0:
        problems.append("late fulfillment was forbidden")
    produced = 0
    shipped_by_period = {0: 0, 1: 0}
    for row in result.productions:
        produced += row.quantity
        plant = next(item for item in snapshot.plants if item.plant_id == row.plant_id)
        if row.quantity > plant.cap(row.period):
            problems.append(f"{row.plant_id} period {row.period} exceeds capacity")
        if row.quantity < 0:
            problems.append("negative production")
    for shipment in result.shipments:
        period_total = shipped_by_period.get(shipment.period, 0) + shipment.quantity
        shipped_by_period[shipment.period] = period_total
        if shipment.arrives_period != shipment.period + 1:
            problems.append("shipment lead time is not 1 period")
        match = next(
            item
            for item in result.productions
            if item.plant_id == shipment.plant_id and item.period == shipment.period
        )
        if match.quantity != shipment.quantity:
            problems.append("shipment does not match production")
    if produced > snapshot.materials:
        problems.append("material consumption exceeds availability")
    for period, qty in shipped_by_period.items():
        if qty > snapshot.route_capacity:
            problems.append(f"route capacity exceeded in period {period}")
    if shipped_by_period.get(0, 0) != result.on_time:
        problems.append("on-time quantity is not the period-0 shipment")
    if snapshot.allow_late and shipped_by_period.get(1, 0) != result.late:
        problems.append("late quantity is not the period-1 shipment")
    starter = snapshot.transport_cost_per_unit == 0 and snapshot.demand == 16
    weight = STARTER_UNMET_PENALTY if starter else UNMET_PENALTY
    expected = (
        weight * result.unmet
        + LATE_PENALTY * result.late
        + result.transport_cost
        + result.production_cost
    )
    if result.objective != expected:
        problems.append(f"objective {result.objective} != recomputed {expected}")
    return problems
