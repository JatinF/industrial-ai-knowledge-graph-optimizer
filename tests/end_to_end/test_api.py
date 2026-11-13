"""HTTP proof of the failure flow. Reads are open. Writes require a bearer role."""

from fastapi.testclient import TestClient

from industrial_ai.api.main import create_app
from industrial_ai.domain.entities import LOT, PRESS

PLANNER = {"Authorization": "Bearer lab-planner"}
OPERATOR = {"Authorization": "Bearer lab-operator"}
FAILURE = {
    "schema_version": 1,
    "event_id": "evt-1001",
    "event_type": "MachineFailureDetected",
    "occurred_at": "2026-11-13T10:00:00Z",
    "source_system": "synthetic-mes",
    "factory_id": "PLANT-A",
    "machine_id": "PRESS-220",
    "new_status": "DOWN",
    "reason": "hydraulic_pressure_fault",
    "source_sequence": 2,
}


def test_http_failure_approval_and_idempotent_execute(monkeypatch: object) -> None:
    monkeypatch.delenv("NEO4J_URI", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("DATABASE_URL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("KAFKA_BOOTSTRAP", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)  # type: ignore[attr-defined]
    app = create_app()
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["simulation"] is True
    assert body["store"] == "sqlite"
    assert body["adapters"]["neo4j"] == "not-run"
    assert body["controller_calls"] == 0
    denied = client.post("/api/v1/scenarios/machine_failure/run")
    assert denied.status_code == 401
    run = client.post("/api/v1/scenarios/machine_failure/run", headers=PLANNER)
    assert run.status_code == 200
    plan = run.json()
    assert plan["objective"] == 72
    assert plan["solver_status"] == "OPTIMAL"
    assert plan["decision_status"] == "REQUIRES_APPROVAL"
    assert plan["unmet_demand"] == 0
    assert plan["late"] == 2
    assert plan["constraint_violations"] == []
    assert plan["candidate_orders"] == ["CO-2001"]
    assert "CO-2002" not in plan["candidate_orders"]
    assert plan["signals"]["authoritative"] is False
    trace = plan["trace_id"]
    assert trace.startswith("trace-")
    fetched = client.get(f"/api/v1/plans/{plan['plan_id']}")
    assert fetched.json()["objective"] == 72
    impact = client.get(f"/api/v1/graph/impact/{PRESS}")
    assert impact.status_code == 200
    assert impact.json()["impact"][0]["candidate_orders"] == ["CO-2001"]
    assets = client.get("/api/v1/assets")
    assert any(row["id"] == PRESS for row in assets.json()["assets"])
    assert client.post(f"/api/v1/plans/{plan['plan_id']}/approve").status_code == 401
    assert (
        client.post(f"/api/v1/plans/{plan['plan_id']}/approve", headers=PLANNER).status_code == 403
    )
    forged = client.post(
        f"/api/v1/plans/{plan['plan_id']}/approve",
        headers=OPERATOR,
        json={"approved": True},
    )
    assert forged.status_code == 422
    assert app.state.platform.store.lot_quantity(LOT) == 14
    approved = client.post(
        f"/api/v1/plans/{plan['plan_id']}/approve",
        headers=OPERATOR,
        json={"note": "reviewed"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert app.state.platform.store.lot_quantity(LOT) == 14
    executed = client.post(f"/api/v1/plans/{plan['plan_id']}/execute", headers=OPERATOR)
    assert executed.status_code == 200
    assert executed.json()["lot_quantity"] == 4
    assert executed.json()["idempotent"] is False
    replay = client.post(f"/api/v1/plans/{plan['plan_id']}/execute", headers=OPERATOR)
    assert replay.json()["idempotent"] is True
    assert app.state.platform.store.lot_quantity(LOT) == 4
    assert app.state.platform.store.finished_quantity("PRODUCT-A") == 10
    audit = client.get("/api/v1/audit/events")
    actions = [row["action"] for row in audit.json()["events"]]
    assert "plan_approved" in actions
    assert "plan_executed" in actions
    assert trace == plan["trace_id"]
    metrics = client.get("/metrics")
    assert "industrial_plans_executed_total 1" in metrics.text


def test_rejected_plan_and_bad_event_and_duplicate() -> None:
    app = create_app()
    client = TestClient(app)
    run = client.post("/api/v1/scenarios/normal_operations/run", headers=PLANNER)
    plan_id = run.json()["plan_id"]
    rejected = client.post(f"/api/v1/plans/{plan_id}/reject", headers=OPERATOR, json={})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    execute = client.post(f"/api/v1/plans/{plan_id}/execute", headers=OPERATOR)
    assert execute.status_code == 409
    assert app.state.platform.store.lot_quantity(LOT) == 14
    first = client.post("/api/v1/events", headers=PLANNER, json=FAILURE)
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    second = client.post("/api/v1/events", headers=PLANNER, json=FAILURE)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    stale = dict(FAILURE)
    stale["event_id"] = "evt-stale"
    stale["source_sequence"] = 1
    stale["new_status"] = "UP"
    assert client.post("/api/v1/events", headers=PLANNER, json=stale).status_code == 409
    assert app.state.platform.graph.get(PRESS).props["state"] == "DOWN"
    bad = dict(FAILURE)
    bad["event_id"] = "evt-version"
    bad["schema_version"] = 2
    assert client.post("/api/v1/events", headers=PLANNER, json=bad).status_code == 422
    missing = client.get("/api/v1/plans/PLAN-missing")
    assert missing.status_code == 404


def test_openapi_lists_the_contract() -> None:
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for path in (
        "/health",
        "/api/v1/scenarios/reset",
        "/api/v1/scenarios/{scenario_id}/run",
        "/api/v1/assets",
        "/api/v1/graph/dependencies/{asset_id}",
        "/api/v1/graph/impact/{asset_id}",
        "/api/v1/events",
        "/api/v1/plans/solve",
        "/api/v1/plans/{plan_id}",
        "/api/v1/plans/{plan_id}/approve",
        "/api/v1/plans/{plan_id}/reject",
        "/api/v1/plans/{plan_id}/execute",
        "/api/v1/audit/events",
    ):
        assert path in paths
