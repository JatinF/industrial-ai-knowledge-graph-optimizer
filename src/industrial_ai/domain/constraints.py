"""Names of the constraints the allocation checker recomputes."""

ALLOCATION_CONSTRAINTS: tuple[str, ...] = (
    "non_negative_quantities",
    "fulfillment_balances_demand",
    "late_forbidden_when_disabled",
    "plant_period_capacity",
    "material_availability",
    "shipment_matches_production",
    "lead_time_one_period",
    "route_capacity",
    "on_time_is_period_zero",
    "objective_identity",
)


def constraint_names() -> tuple[str, ...]:
    return ALLOCATION_CONSTRAINTS
