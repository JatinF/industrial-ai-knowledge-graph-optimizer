"""Measure the in-process path on this workstation.

Stretch graph sizes and the two-second event-to-plan figure are targets.
This module records what this process actually did. Price is none.
"""

from __future__ import annotations

import json
import math
import os
import platform
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from industrial_ai.catalog import build_catalog
from industrial_ai.domain.entities import LOT, OPERATOR_ID, PLANNER_ID, PRESS
from industrial_ai.execution.approvals import Actor
from industrial_ai.graph.impact_analysis import affected_orders
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.platform import Platform
from industrial_ai.runtime_gates import adapter_report


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _hardware() -> dict[str, object]:
    processor = platform.processor()
    cores: int | None = None
    logical = os.cpu_count()
    try:
        import subprocess

        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 "
                "Name, NumberOfCores, NumberOfLogicalProcessors | ConvertTo-Json -Compress)",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            info = json.loads(completed.stdout)
            if isinstance(info, dict):
                name = info.get("Name")
                if isinstance(name, str) and name.strip():
                    processor = name.strip()
                core_count = info.get("NumberOfCores")
                if isinstance(core_count, int):
                    cores = core_count
                logical_count = info.get("NumberOfLogicalProcessors")
                if isinstance(logical_count, int):
                    logical = logical_count
    except (OSError, json.JSONDecodeError, TimeoutError):
        pass
    return {
        "processor": processor,
        "cores": cores,
        "logical_processors": logical,
        "python": platform.python_version(),
        "ortools": version("ortools"),
        "system": platform.system(),
    }


def _scale_graph() -> tuple[OperationalGraph, float]:
    started = time.perf_counter()
    graph = OperationalGraph()
    products = [f"SCALE-P-{index}" for index in range(5000)]
    for product_id in products:
        graph.add_node("Product", product_id)
    for machine_index in range(2000):
        machine_id = f"SCALE-M-{machine_index}"
        graph.add_node("Machine", machine_id, state="UP")
        for slot in range(50):
            graph.add_edge(
                machine_id,
                "PRODUCES",
                products[(machine_index * 3 + slot) % 5000],
                capacity_per_shift=1,
            )
    for order_index in range(10000):
        order_id = f"SCALE-O-{order_index}"
        graph.add_node("CustomerOrder", order_id, quantity=1)
        graph.add_edge(order_id, "REQUESTS", products[order_index % 5000])
    return graph, time.perf_counter() - started


def run_benchmark(*, repeats: int = 40) -> dict[str, Any]:
    catalog = build_catalog()
    counts = catalog.counts()
    impact_samples: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        affected_orders(catalog, PRESS)
        impact_samples.append(time.perf_counter() - started)
    scale, scale_build = _scale_graph()
    scale_started = time.perf_counter()
    scale_rows = affected_orders(scale, "SCALE-M-0")
    scale_query = time.perf_counter() - scale_started
    planner = Actor(PLANNER_ID, "planner")
    operator = Actor(OPERATOR_ID, "operator")
    platform = Platform(clock=lambda: "2026-11-12T15:00:00Z")
    latencies: list[float] = []
    solver_walls: list[float] = []
    plan: dict[str, Any] = {}
    for index in range(repeats):
        platform.reset("normal_operations")
        event = {
            "schema_version": 1,
            "event_id": f"evt-bench-{index}",
            "event_type": "MachineFailureDetected",
            "occurred_at": "2026-11-13T10:00:00Z",
            "source_system": "synthetic-mes",
            "factory_id": "PLANT-A",
            "machine_id": PRESS,
            "new_status": "DOWN",
            "reason": "hydraulic_pressure_fault",
            "source_sequence": index + 1,
        }
        started = time.perf_counter()
        ingested = platform.ingest(event, actor_id=planner.user_id)
        plan = platform.solve(planner, trace_id=str(ingested["trace_id"]))
        latencies.append(time.perf_counter() - started)
        solver_walls.append(float(plan["allocation"]["wall_seconds"]))
        if plan["objective"] != 72 or plan["constraint_violations"] != []:
            raise RuntimeError("benchmark plan left the hand calculation")
    if "plan_id" not in plan:
        raise RuntimeError("no benchmark sample")
    platform.approve(plan["plan_id"], operator)
    first = platform.execute(plan["plan_id"], operator)
    second = platform.execute(plan["plan_id"], operator)
    invalid = 0
    if first["lot_quantity"] != 4 or second["idempotent"] is not True:
        invalid = 1
    if platform.store.lot_quantity(LOT) != 4:
        invalid = 1
    event_p95 = _percentile(latencies, 0.95)
    report: dict[str, Any] = {
        "price": "none",
        "hardware": _hardware(),
        "store": "sqlite",
        "graph": "in-memory",
        "adapters": adapter_report(),
        "solver_time_limit_seconds": 5.0,
        "repeats": repeats,
        "dataset": {
            "entities": counts["entities"],
            "relationships": counts["relationships"],
            "factories": counts["label_Factory"],
            "suppliers": counts["label_Supplier"],
            "warehouses": counts["label_Warehouse"],
            "machines": counts["label_Machine"],
            "products": counts["label_Product"],
            "customer_orders": counts["label_CustomerOrder"],
            "seed": 7,
        },
        "graph_query_p95_seconds": _percentile(impact_samples, 0.95),
        "event_to_plan_p95_seconds": event_p95,
        "event_to_plan_target_seconds": 2.0,
        "event_to_plan_target_met": event_p95 <= 2.0,
        "solver_wall_seconds": {
            "min": min(solver_walls),
            "p50": _percentile(solver_walls, 0.50),
            "max": max(solver_walls),
        },
        "invalid_executed_plans": invalid,
        "invalid_executed_plans_target": 0,
        "invalid_executed_plans_target_met": invalid == 0,
        "scale_in_memory": {
            "entities": scale.counts()["entities"],
            "relationships": scale.counts()["relationships"],
            "build_seconds": scale_build,
            "impact_seconds": scale_query,
            "candidate_products": len(scale_rows),
            "neo4j": "not-run",
        },
        "notes": [
            "Event-to-plan time is ingest plus solve on the hand scenario after reset.",
            "The scale graph is in-process. It was not loaded into Neo4j.",
            "Targets are acceptance bars for this small scenario, not stretch-scale results.",
        ],
    }
    return report


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
