"""Contact localhost Neo4j or PostgreSQL only when the job set those URLs.

Unset means not-run. This file skips on the workstation. GitHub Actions sets
the localhost URLs for the integration job.
"""

import os
import time

import pytest

from industrial_ai.catalog import build_catalog
from industrial_ai.domain.entities import ORDER, OTHER_ORDER, PLANNER_ID, PRESS
from industrial_ai.execution.approvals import Actor
from industrial_ai.platform import Platform
from industrial_ai.runtime_gates import gate
from industrial_ai.storage.neo4j import load_and_impact
from industrial_ai.storage.postgres import postgres_store_from_env


def test_neo4j_impact_query_when_local() -> None:
    if gate(os.environ.get("NEO4J_URI")) != "local":
        pytest.skip("neo4j not-run")
    graph = build_catalog()
    last: Exception | None = None
    result: dict[str, object] = {}
    for _attempt in range(8):
        try:
            result = load_and_impact(graph, PRESS)
            break
        except RuntimeError as exc:
            last = exc
            time.sleep(3)
    else:
        if last is not None:
            raise last
        raise RuntimeError("neo4j request failed")
    assert result["status"] == "contacted"
    rows = result["rows"]
    assert isinstance(rows, list)
    orders: list[object] = []
    for row in rows:
        assert isinstance(row, dict)
        found = row.get("candidate_orders")
        if isinstance(found, list):
            orders.extend(found)
    assert ORDER in orders
    assert OTHER_ORDER not in orders


def test_postgres_failure_plan_when_local() -> None:
    if gate(os.environ.get("DATABASE_URL")) != "local":
        pytest.skip("postgres not-run")
    store = postgres_store_from_env()
    platform = Platform(store=store, clock=lambda: "2026-11-12T15:00:00Z")
    plan = platform.run_scenario("machine_failure", Actor(PLANNER_ID, "planner"))
    assert plan["objective"] == 72
    assert plan["unmet_demand"] == 0
    assert plan["late"] == 2
    assert store.kind == "postgres"
