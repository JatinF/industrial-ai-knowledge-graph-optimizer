from industrial_ai.optimization.allocation_solver import optimize, solve_allocation
from industrial_ai.optimization.feasibility import constraint_violations
from industrial_ai.optimization.greedy import plan_greedy
from industrial_ai.optimization.model_builder import AllocationSnapshot, PlantCapacity
from industrial_ai.optimization.scheduling_solver import solve_schedule


def _hand(
    *,
    cap_a: int = 8,
    cap_b: int = 6,
    demand: int = 10,
    materials: int = 14,
    route: int = 20,
    allow_late: bool = True,
    forbid: bool = False,
    block_period0: bool = False,
) -> AllocationSnapshot:
    period_a = (0, cap_a) if block_period0 else None
    period_b = (0, cap_b) if block_period0 else None
    return AllocationSnapshot(
        revision=1,
        product_id="PRODUCT-A",
        demand=demand,
        materials=materials,
        plants=(
            PlantCapacity("PLANT-A", cap_a, 3, period_a),
            PlantCapacity("PLANT-B", cap_b, 2, period_b),
        ),
        route_capacity=route,
        transport_cost_per_unit=3,
        allow_late=allow_late,
        forbid_shortfall=forbid,
        down_machines=() if cap_a == 8 else ("PRESS-220",),
        candidate_orders=("CO-2001",),
    )


def test_starter_matches_the_published_asserts() -> None:
    baseline = optimize()
    after = optimize(max_b=2)
    assert baseline["unfulfilled"] == 2
    assert after["unfulfilled"] == 6
    assert baseline["plant_a"] == 8
    assert baseline["plant_b"] == 6
    assert baseline["objective"] == 236
    assert after["plant_a"] == 8
    assert after["plant_b"] == 2
    assert after["objective"] == 628
    assert baseline["status"] == "OPTIMAL"


def test_two_period_normal_and_press_failure() -> None:
    normal = solve_allocation(_hand())
    failed = solve_allocation(_hand(cap_a=2))
    assert constraint_violations(_hand(), normal) == []
    assert constraint_violations(_hand(cap_a=2), failed) == []
    assert normal.status == "OPTIMAL"
    assert normal.unmet == 0 and normal.late == 0 and normal.on_time == 10
    assert normal.objective == 54
    assert failed.unmet == 0 and failed.late == 2 and failed.on_time == 8
    assert failed.objective == 72
    assert failed.operational_requirement_met is False
    assert normal.operational_requirement_met is True


def test_on_time_only_failure_reports_shortage() -> None:
    failed = solve_allocation(_hand(cap_a=2, allow_late=False))
    assert failed.status == "OPTIMAL"
    assert failed.unmet == 2 and failed.late == 0 and failed.on_time == 8
    assert failed.objective == 2042
    assert constraint_violations(_hand(cap_a=2, allow_late=False), failed) == []


def test_period_one_production_is_not_on_time() -> None:
    blocked = solve_allocation(_hand(block_period0=True))
    assert blocked.on_time == 0
    assert blocked.late == 10
    assert blocked.unmet == 0
    assert blocked.objective == 154


def test_route_capacity_limits_each_period() -> None:
    capped = solve_allocation(_hand(route=5))
    assert capped.on_time == 5
    assert capped.late == 5
    assert capped.unmet == 0


def test_material_shortage_is_optimal_and_still_short() -> None:
    short = solve_allocation(_hand(materials=4))
    assert short.status == "OPTIMAL"
    assert short.unmet == 6 and short.on_time == 4 and short.late == 0
    assert short.objective == 6020
    hard = solve_allocation(_hand(materials=4, allow_late=False, forbid=True))
    assert hard.status == "INFEASIBLE"


def test_solver_beats_name_order_on_cost_without_breaking_constraints() -> None:
    snapshot = _hand(cap_a=2)
    solved = solve_allocation(snapshot)
    greedy = plan_greedy(snapshot)
    assert constraint_violations(snapshot, solved) == []
    assert solved.unmet <= greedy.unmet
    assert solved.production_cost < greedy.production_cost
    assert solved.objective < greedy.objective


def test_schedule_moves_off_the_down_press() -> None:
    clear = solve_schedule(maintenance=False, alternate_available=True)
    down = solve_schedule(maintenance=True, alternate_available=True)
    stuck = solve_schedule(maintenance=True, alternate_available=False)
    assert clear.makespan == 7
    assert down.makespan == 7
    assert {row.machine_id for row in down.assignments} == {"MILL-110"}
    assert stuck.makespan == 12
    assert {row.machine_id for row in stuck.assignments} == {"PRESS-220"}
    press = [row for row in stuck.assignments if row.job_id == "JOB-1"][0]
    assert press.start >= 5
    job1 = [row for row in down.assignments if row.job_id == "JOB-1"][0]
    job2 = [row for row in down.assignments if row.job_id == "JOB-2"][0]
    assert job2.start >= job1.end
