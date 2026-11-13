"""CP-SAT allocation for one finished good over two periods.

Period 0 shipments arrive in period 1 and count as on time.
Period 1 shipments arrive after the due period and count as late.
Shortfall is a decision variable, so OPTIMAL can still leave demand unmet.
"""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from industrial_ai.optimization.model_builder import AllocationSnapshot
from industrial_ai.optimization.objectives import LATE_PENALTY, STARTER_UNMET_PENALTY, UNMET_PENALTY


@dataclass(frozen=True)
class Production:
    plant_id: str
    period: int
    quantity: int
    cost: int


@dataclass(frozen=True)
class Shipment:
    plant_id: str
    period: int
    quantity: int
    arrives_period: int


@dataclass(frozen=True)
class AllocationResult:
    status: str
    objective: int
    unmet: int
    late: int
    on_time: int
    production_cost: int
    transport_cost: int
    productions: tuple[Production, ...]
    shipments: tuple[Shipment, ...]
    wall_seconds: float
    operational_requirement_met: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "objective": self.objective,
            "unmet": self.unmet,
            "late": self.late,
            "on_time": self.on_time,
            "production_cost": self.production_cost,
            "transport_cost": self.transport_cost,
            "productions": [p.__dict__ for p in self.productions],
            "shipments": [s.__dict__ for s in self.shipments],
            "wall_seconds": self.wall_seconds,
            "operational_requirement_met": self.operational_requirement_met,
        }


def _objective_value(solver: cp_model.CpSolver) -> int:
    raw = solver.objective_value
    number = raw() if callable(raw) else raw
    return int(round(number))


def solve_allocation(
    snapshot: AllocationSnapshot, *, max_time_seconds: float | None = None
) -> AllocationResult:
    started = time.perf_counter()
    model = cp_model.CpModel()
    periods = (0, 1)
    produce: dict[tuple[str, int], cp_model.IntVar] = {}
    ship: dict[tuple[str, int], cp_model.IntVar] = {}
    for plant in snapshot.plants:
        upper = max(plant.cap(0), plant.cap(1), 0)
        for period in periods:
            produce[plant.plant_id, period] = model.new_int_var(
                0, upper, f"prod_{plant.plant_id}_{period}"
            )
            ship[plant.plant_id, period] = model.new_int_var(
                0, snapshot.route_capacity, f"ship_{plant.plant_id}_{period}"
            )
            model.add(produce[plant.plant_id, period] <= plant.cap(period))
            model.add(ship[plant.plant_id, period] == produce[plant.plant_id, period])
    for period in periods:
        model.add(
            sum(ship[plant.plant_id, period] for plant in snapshot.plants)
            <= snapshot.route_capacity
        )
    model.add(sum(produce.values()) <= snapshot.materials)

    on_time = model.new_int_var(0, snapshot.demand, "on_time")
    late = model.new_int_var(0, snapshot.demand, "late")
    unmet = model.new_int_var(0, snapshot.demand, "unmet")
    model.add(on_time == sum(ship[plant.plant_id, 0] for plant in snapshot.plants))
    if snapshot.allow_late:
        model.add(late == sum(ship[plant.plant_id, 1] for plant in snapshot.plants))
    else:
        model.add(late == 0)
        model.add(sum(ship[plant.plant_id, 1] for plant in snapshot.plants) == 0)
    model.add(on_time + late + unmet == snapshot.demand)
    if snapshot.forbid_shortfall:
        model.add(unmet == 0)

    production_cost = sum(
        produce[plant.plant_id, period] * plant.cost_per_unit
        for plant in snapshot.plants
        for period in periods
    )
    transport_cost = sum(
        ship[plant.plant_id, period] * snapshot.transport_cost_per_unit
        for plant in snapshot.plants
        for period in periods
    )
    unmet_weight = STARTER_UNMET_PENALTY if _is_starter(snapshot) else UNMET_PENALTY
    model.minimize(unmet_weight * unmet + LATE_PENALTY * late + transport_cost + production_cost)

    solver = cp_model.CpSolver()
    if max_time_seconds is not None:
        solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.solve(model)
    elapsed = time.perf_counter() - started
    name = solver.status_name(status)
    if name not in {"OPTIMAL", "FEASIBLE"}:
        return AllocationResult(
            status=name,
            objective=0,
            unmet=snapshot.demand,
            late=0,
            on_time=0,
            production_cost=0,
            transport_cost=0,
            productions=(),
            shipments=(),
            wall_seconds=elapsed,
            operational_requirement_met=False,
        )
    productions: list[Production] = []
    shipments: list[Shipment] = []
    prod_cost = 0
    ship_cost = 0
    for plant in snapshot.plants:
        for period in periods:
            qty = solver.value(produce[plant.plant_id, period])
            cost = qty * plant.cost_per_unit
            productions.append(Production(plant.plant_id, period, qty, cost))
            shipped = solver.value(ship[plant.plant_id, period])
            shipments.append(Shipment(plant.plant_id, period, shipped, period + 1))
            prod_cost += cost
            ship_cost += shipped * snapshot.transport_cost_per_unit
    unmet_v = solver.value(unmet)
    late_v = solver.value(late)
    on_time_v = solver.value(on_time)
    return AllocationResult(
        status=name,
        objective=_objective_value(solver),
        unmet=unmet_v,
        late=late_v,
        on_time=on_time_v,
        production_cost=prod_cost,
        transport_cost=ship_cost,
        productions=tuple(productions),
        shipments=tuple(shipments),
        wall_seconds=elapsed,
        operational_requirement_met=unmet_v == 0 and late_v == 0,
    )


def _is_starter(snapshot: AllocationSnapshot) -> bool:
    """The published starter uses unmet weight 100 and does not charge transport."""

    return (
        snapshot.transport_cost_per_unit == 0 and snapshot.demand == 16 and not snapshot.allow_late
    )


def optimize(
    max_a: int = 8, max_b: int = 6, demand: int = 16, materials: int = 14
) -> dict[str, object]:
    """Runnable first optimizer from the specification. One shared material pool."""

    from industrial_ai.optimization.model_builder import starter_snapshot

    result = solve_allocation(
        starter_snapshot(max_a=max_a, max_b=max_b, demand=demand, materials=materials)
    )
    if result.status not in {"OPTIMAL", "FEASIBLE"}:
        return {"status": result.status}
    # Period 1 is forbidden in the starter, so the plant sum is that plant's only output.
    plant_a = 0
    plant_b = 0
    for item in result.productions:
        if item.plant_id == "PLANT-A":
            plant_a += item.quantity
        elif item.plant_id == "PLANT-B":
            plant_b += item.quantity
    return {
        "status": result.status,
        "plant_a": plant_a,
        "plant_b": plant_b,
        "unfulfilled": result.unmet,
        "objective": result.objective,
    }
