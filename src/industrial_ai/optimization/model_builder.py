"""Snapshots the allocation model is allowed to see.

A snapshot is a copy. Later machine-state changes do not alter a plan that
was solved from an older revision.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlantCapacity:
    plant_id: str
    capacity: int
    cost_per_unit: int
    capacity_by_period: tuple[int, int] | None = None

    def cap(self, period: int) -> int:
        if self.capacity_by_period is None:
            return self.capacity
        return self.capacity_by_period[period]


@dataclass(frozen=True)
class AllocationSnapshot:
    revision: int
    product_id: str
    demand: int
    materials: int
    plants: tuple[PlantCapacity, ...]
    route_capacity: int
    transport_cost_per_unit: int
    allow_late: bool = True
    forbid_shortfall: bool = False
    down_machines: tuple[str, ...] = ()
    candidate_orders: tuple[str, ...] = ()


def starter_snapshot(
    *, max_a: int = 8, max_b: int = 6, demand: int = 16, materials: int = 14
) -> AllocationSnapshot:
    """The two-plant starter. One period of production, no lateness, no route."""

    return AllocationSnapshot(
        revision=0,
        product_id="PRODUCT-A",
        demand=demand,
        materials=materials,
        plants=(
            PlantCapacity("PLANT-A", max_a, 3),
            PlantCapacity("PLANT-B", max_b, 2),
        ),
        route_capacity=demand,
        transport_cost_per_unit=0,
        allow_late=False,
        forbid_shortfall=False,
    )
