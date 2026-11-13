"""Name-order planner used only as a baseline.

Plants are filled in plant-id order, not cost order. Period 0 is filled
before period 1. This is not a solver.
"""

from industrial_ai.optimization.allocation_solver import AllocationResult, Production, Shipment
from industrial_ai.optimization.model_builder import AllocationSnapshot
from industrial_ai.optimization.objectives import LATE_PENALTY, UNMET_PENALTY


def plan_greedy(snapshot: AllocationSnapshot) -> AllocationResult:
    remaining = snapshot.demand
    material = snapshot.materials
    productions: list[Production] = []
    shipments: list[Shipment] = []
    on_time = 0
    late = 0
    production_cost = 0
    transport_cost = 0
    periods = (0, 1) if snapshot.allow_late else (0,)
    for period in periods:
        route_left = snapshot.route_capacity
        for plant in sorted(snapshot.plants, key=lambda item: item.plant_id):
            take = min(plant.cap(period), material, route_left, remaining)
            cost = take * plant.cost_per_unit
            productions.append(Production(plant.plant_id, period, take, cost))
            shipments.append(Shipment(plant.plant_id, period, take, period + 1))
            material -= take
            route_left -= take
            remaining -= take
            production_cost += cost
            transport_cost += take * snapshot.transport_cost_per_unit
            if period == 0:
                on_time += take
            else:
                late += take
    if not snapshot.allow_late:
        for plant in snapshot.plants:
            productions.append(Production(plant.plant_id, 1, 0, 0))
            shipments.append(Shipment(plant.plant_id, 1, 0, 2))
    unmet = remaining
    objective = UNMET_PENALTY * unmet + LATE_PENALTY * late + transport_cost + production_cost
    return AllocationResult(
        status="GREEDY",
        objective=objective,
        unmet=unmet,
        late=late,
        on_time=on_time,
        production_cost=production_cost,
        transport_cost=transport_cost,
        productions=tuple(productions),
        shipments=tuple(shipments),
        wall_seconds=0.0,
        operational_requirement_met=unmet == 0 and late == 0,
    )
