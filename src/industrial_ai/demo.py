"""Print the machine-failure demonstration from a real solver run.

The numbers are checked against the hand calculation before they are printed.
The demonstration does not approve the plan and does not change inventory.
"""

from dataclasses import replace

from industrial_ai.domain.entities import LOT, PLANNER_ID, PRESS
from industrial_ai.execution.approvals import Actor
from industrial_ai.execution.validation import snapshot_from_document
from industrial_ai.graph.projection import build_snapshot
from industrial_ai.optimization.allocation_solver import solve_allocation
from industrial_ai.platform import Platform


def run_demo(clock: object | None = None) -> str:
    platform = Platform(clock=clock) if clock is not None else Platform()
    normal_snapshot = build_snapshot(
        platform.graph,
        revision=platform.store.revision(),
        allow_late=True,
        forbid_shortfall=False,
    )
    normal = solve_allocation(normal_snapshot)
    planner = Actor(PLANNER_ID, "planner")
    plan = platform.run_scenario("machine_failure", planner)
    stored = snapshot_from_document(platform.get_plan(str(plan["plan_id"])))
    on_time_only = solve_allocation(replace(stored, allow_late=False))
    lot = platform.store.lot_quantity(LOT)
    if normal.objective != 54 or normal.unmet != 0:
        raise RuntimeError("normal plan does not match the hand calculation")
    if (
        plan["objective"] != 72
        or plan["unmet_demand"] != 0
        or plan["late"] != 2
        or plan["on_time"] != 8
    ):
        raise RuntimeError("failure plan does not match the hand calculation")
    if plan["solver_status"] != "OPTIMAL" or plan["constraint_violations"] != []:
        raise RuntimeError("failure plan is not a clean optimum")
    if plan["decision_status"] != "REQUIRES_APPROVAL":
        raise RuntimeError("failure plan was not left for approval")
    if on_time_only.unmet != 2 or on_time_only.objective != 2042:
        raise RuntimeError("on-time-only variant does not match the hand calculation")
    if lot != 14 or platform.controller_calls != 0:
        raise RuntimeError("demo changed inventory or called a controller")
    if plan["candidate_orders"] != ["CO-2001"] or plan["down_machines"] != [PRESS]:
        raise RuntimeError("impact did not name CO-2001 on PRESS-220")
    lines = [
        "Industrial AI Operational Optimization Demo",
        "-------------------------------------------",
        "Scenario: Machine Failure",
        "Factory: PLANT-A",
        "Asset: PRESS-220",
        "",
        "1. Event received and validated",
        "2. Operational graph updated",
        "3. Affected customer orders identified: CO-2001",
        "4. Optimization snapshot created",
        "5. Revised production plan computed",
        "6. Capacity and material constraints checked",
        "7. Proposed plan awaiting operator approval",
        "",
        "Result:",
        f"  Decision status: {plan['decision_status']}",
        f"  Solver status: {plan['solver_status']}",
        f"  Constraint violations: {len(plan['constraint_violations'])}",
        f"  Unmet demand: {plan['unmet_demand']}",
        f"  Late: {plan['late']}",
        f"  On time: {plan['on_time']}",
        f"  Objective: {plan['objective']}",
        f"  Normal objective: {normal.objective}",
        f"  Name-order baseline objective: {plan['baseline_objective']}",
        "  Operational requirement met: no",
        f"  On-time-only unmet demand, not proposed: {on_time_only.unmet}",
        "",
        "Execution:",
        "  No operational action performed before approval",
        "  Simulated systems only",
        f"  Inventory lot LOT-1001 remains {lot}",
        f"  Controller calls: {platform.controller_calls}",
    ]
    return "\n".join(lines) + "\n"
