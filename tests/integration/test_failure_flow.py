"""Disruption to a constraint-valid plan, then a single simulated execution."""

import socket

from industrial_ai.domain.entities import (
    IOT,
    LOT,
    OPERATOR_ID,
    ORDER,
    OTHER_ORDER,
    PLANNER_ID,
    PRESS,
    PRODUCT_A,
)
from industrial_ai.execution.approvals import Actor
from industrial_ai.optimization.allocation_solver import AllocationResult
from industrial_ai.platform import Platform

CLOCK = "2026-11-12T15:00:00Z"
FAILURE = {
    "schema_version": 1,
    "event_id": "evt-1001",
    "event_type": "MachineFailureDetected",
    "occurred_at": "2026-11-13T10:00:00Z",
    "source_system": "synthetic-mes",
    "factory_id": "PLANT-A",
    "machine_id": PRESS,
    "new_status": "DOWN",
    "reason": "hydraulic_pressure_fault",
    "source_sequence": 2,
}


def _platform() -> Platform:
    return Platform(clock=lambda: CLOCK)


def _people() -> tuple[Actor, Actor]:
    return Actor(PLANNER_ID, "planner"), Actor(OPERATOR_ID, "operator")


def test_failure_changes_the_plan_and_waits_for_approval() -> None:
    platform = _platform()
    planner, operator = _people()
    normal = platform.run_scenario("normal_operations", planner)
    failed = platform.run_scenario("machine_failure", planner)
    assert normal["objective"] == 54
    assert normal["operational_requirement_met"] is True
    assert failed["objective"] == 72
    assert failed["solver_status"] == "OPTIMAL"
    assert failed["decision_status"] == "REQUIRES_APPROVAL"
    assert failed["unmet_demand"] == 0
    assert failed["late"] == 2
    assert failed["on_time"] == 8
    assert failed["constraint_violations"] == []
    assert failed["operational_requirement_met"] is False
    assert failed["candidate_orders"] == [ORDER]
    assert OTHER_ORDER not in failed["candidate_orders"]
    assert failed["baseline_objective"] == 74
    assert failed["objective"] < failed["baseline_objective"]
    assert failed["schedule"]["makespan"] == 7
    assert {row["machine_id"] for row in failed["schedule"]["assignments"]} == {"MILL-110"}
    assert failed["event"]["occurred_at"] == "2026-11-13T10:00:00Z"
    assert failed["event"]["ingested_at"] == CLOCK
    assert failed["event"]["occurred_at"] != failed["event"]["ingested_at"]
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    assert platform.graph.has("FAIL-001")
    assert platform.store.lot_quantity(LOT) == 14
    approved = platform.approve(failed["plan_id"], operator)
    assert approved["status"] == "APPROVED"
    assert platform.store.lot_quantity(LOT) == 14
    effect = platform.execute(failed["plan_id"], operator)
    assert effect["lot_quantity"] == 4
    assert effect["finished_quantity"] == 10
    assert effect["idempotent"] is False
    assert effect["controller_calls"] == 0
    again = platform.execute(failed["plan_id"], operator)
    assert again["idempotent"] is True
    assert platform.store.lot_quantity(LOT) == 4
    assert platform.store.finished_quantity(PRODUCT_A) == 10
    assert platform.controller_calls == 0


def test_supplier_delay_and_demand_surge_and_infeasible() -> None:
    planner, _operator = _people()
    delayed = _platform().run_scenario("supplier_delay", planner)
    assert delayed["solver_status"] == "OPTIMAL"
    assert delayed["unmet_demand"] == 6
    assert delayed["on_time"] == 4
    assert delayed["objective"] == 6020
    assert delayed["operational_requirement_met"] is False
    surge = _platform().run_scenario("demand_surge", planner)
    assert surge["on_time"] == 14
    assert surge["unmet_demand"] == 6
    assert surge["objective"] == 6078
    blocked = _platform().run_scenario("infeasible_schedule", planner)
    assert blocked["solver_status"] == "INFEASIBLE"
    assert blocked["decision_status"] == "INFEASIBLE"
    try:
        _platform_for = _platform()
        plan = _platform_for.run_scenario("infeasible_schedule", planner)
        _platform_for.approve(plan["plan_id"], _people()[1])
    except Exception as exc:
        assert getattr(exc, "code", "") == "not_approvable"
    else:
        raise AssertionError("infeasible plan was approved")


def test_duplicate_stale_and_schema_do_not_double_apply() -> None:
    platform = _platform()
    planner, _operator = _people()
    platform.reset("machine_failure")
    first = platform.ingest(FAILURE, actor_id=planner.user_id)
    assert first["accepted"] is True
    assert first["state_changed"] is True
    revision = first["revision"]
    duplicate = platform.ingest(FAILURE, actor_id=planner.user_id)
    assert duplicate["duplicate"] is True
    assert duplicate["state_changed"] is False
    assert platform.store.revision() == revision
    stale = dict(FAILURE)
    stale["event_id"] = "evt-1001-old"
    stale["source_sequence"] = 1
    stale["new_status"] = "UP"
    stale["occurred_at"] = "2026-11-13T09:00:00Z"
    rejected = platform.ingest(stale, actor_id=planner.user_id)
    assert rejected["accepted"] is False
    assert rejected["error"] == "stale_event"
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    assert platform.store.revision() == revision
    unsupported = dict(FAILURE)
    unsupported["event_id"] = "evt-new-schema"
    unsupported["schema_version"] = 2
    bad = platform.ingest(unsupported, actor_id=planner.user_id)
    assert bad["error"] == "schema_rejected"
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    sensor = dict(FAILURE)
    sensor["event_id"] = "evt-sensor"
    sensor["source_system"] = IOT
    sensor["machine_id"] = "SYN-SENSOR-220"
    sensor["source_sequence"] = 3
    sensor["new_status"] = "DOWN"
    resolved = platform.ingest(sensor, actor_id=planner.user_id)
    assert resolved["accepted"] is True
    assert resolved["entity_id"] == PRESS


def test_spec_example_without_sequence_is_accepted() -> None:
    platform = _platform()
    event = {
        "schema_version": 1,
        "event_id": "evt-1001",
        "event_type": "MachineFailureDetected",
        "occurred_at": "2026-11-13T10:00:00Z",
        "source_system": "synthetic-mes",
        "factory_id": "PLANT-A",
        "machine_id": "PRESS-220",
        "new_status": "DOWN",
        "reason": "hydraulic_pressure_fault",
    }
    result = platform.ingest(event, actor_id=PLANNER_ID)
    assert result["accepted"] is True
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    older = dict(event)
    older["event_id"] = "evt-earlier"
    older["occurred_at"] = "2026-11-13T09:00:00Z"
    older["new_status"] = "UP"
    assert platform.ingest(older, actor_id=PLANNER_ID)["error"] == "stale_event"
    assert platform.graph.get(PRESS).props["state"] == "DOWN"


def test_rejected_and_stale_plans_do_not_execute() -> None:
    platform = _platform()
    planner, operator = _people()
    plan = platform.run_scenario("machine_failure", planner)
    platform.reject(plan["plan_id"], operator)
    try:
        platform.execute(plan["plan_id"], operator)
    except Exception as exc:
        assert getattr(exc, "code", "") == "not_approved"
    else:
        raise AssertionError("rejected plan executed")
    assert platform.store.lot_quantity(LOT) == 14
    fresh = _platform()
    proposed = fresh.run_scenario("machine_failure", planner)
    fresh.approve(proposed["plan_id"], operator)
    later = dict(FAILURE)
    later["event_id"] = "evt-1002"
    later["source_sequence"] = 4
    fresh.ingest(later, actor_id=planner.user_id)
    try:
        fresh.execute(proposed["plan_id"], operator)
    except Exception as exc:
        assert getattr(exc, "code", "") == "stale_snapshot"
    else:
        raise AssertionError("stale plan executed")
    assert fresh.store.lot_quantity(LOT) == 14


def test_same_identity_cannot_approve_and_planner_cannot_execute() -> None:
    platform = _platform()
    _planner, operator = _people()
    plan = platform.run_scenario("machine_failure", operator)
    try:
        platform.approve(plan["plan_id"], operator)
    except Exception as exc:
        assert getattr(exc, "code", "") == "forbidden"
    else:
        raise AssertionError("requester approved the plan")
    try:
        platform.execute(plan["plan_id"], Actor(PLANNER_ID, "planner"))
    except Exception as exc:
        assert getattr(exc, "code", "") == "forbidden"
    else:
        raise AssertionError("planner executed a plan")
    assert platform.store.lot_quantity(LOT) == 14


def test_projection_reconcile_and_outbox_recovery() -> None:
    platform = _platform()
    platform.bus.fail_topics.add("industrial.replanning.v1")
    result = platform.ingest(FAILURE, actor_id=PLANNER_ID)
    assert result["accepted"] is True
    assert result["outbox_published"] is False
    assert len(platform.store.pending_outbox()) == 1
    platform.graph.update(PRESS, state="UP")
    platform.reconcile()
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    platform.bus.fail_topics.clear()
    recovered = platform.recover()
    assert recovered["pending_after"] == 0
    assert platform.store.get_event("evt-1001") is not None
    assert (
        len([row for row in platform.store.list_audit() if row["action"] == "event_accepted"]) == 1
    )


def test_projection_failure_is_reconciled_from_the_store() -> None:
    platform = _platform()
    platform.fail_next_projection = True
    result = platform.ingest(FAILURE, actor_id=PLANNER_ID)
    assert result["projection_reconciled"] is True
    assert platform.graph.get(PRESS).props["state"] == "DOWN"
    assert platform.store.get_entity(PRESS)["status"] == "DOWN"


def test_unknown_solver_status_cannot_execute(monkeypatch: object) -> None:
    def stopped(snapshot: object, max_time_seconds: float | None = None) -> AllocationResult:
        del snapshot, max_time_seconds
        return AllocationResult(
            status="UNKNOWN",
            objective=0,
            unmet=10,
            late=0,
            on_time=0,
            production_cost=0,
            transport_cost=0,
            productions=(),
            shipments=(),
            wall_seconds=0.0,
            operational_requirement_met=False,
        )

    monkeypatch.setattr("industrial_ai.platform.solve_allocation", stopped)  # type: ignore[attr-defined]
    platform = _platform()
    planner, operator = _people()
    plan = platform.solve(planner)
    assert plan["decision_status"] == "SOLVER_STOPPED"
    try:
        platform.approve(plan["plan_id"], operator)
    except Exception as exc:
        assert getattr(exc, "code", "") == "not_approvable"
    else:
        raise AssertionError("timed-out plan was approved")
    assert platform.store.lot_quantity(LOT) == 14


def test_flow_does_not_open_a_socket(monkeypatch: object) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("live socket")

    monkeypatch.setattr(socket, "create_connection", blocked)  # type: ignore[attr-defined]
    platform = _platform()
    planner, operator = _people()
    plan = platform.run_scenario("machine_failure", planner)
    platform.approve(plan["plan_id"], operator)
    platform.execute(plan["plan_id"], operator)
    assert platform.controller_calls == 0
