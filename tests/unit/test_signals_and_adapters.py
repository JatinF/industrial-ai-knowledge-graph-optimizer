"""Adapters, penalty order, and non-authoritative signals."""

from industrial_ai.domain.constraints import constraint_names
from industrial_ai.domain.events import parse_event
from industrial_ai.ingestion.erp_adapter import demand_event
from industrial_ai.ingestion.mes_adapter import machine_failure_event
from industrial_ai.ingestion.plm_adapter import requirement
from industrial_ai.ml.anomaly_detection import is_anomalous
from industrial_ai.ml.evaluation import mean_absolute_error
from industrial_ai.ml.forecasting import advisory_forecast
from industrial_ai.optimization.objectives import LATE_PENALTY, UNMET_PENALTY


def test_penalty_hierarchy_and_forecast_are_not_the_solver() -> None:
    assert UNMET_PENALTY > LATE_PENALTY * 10
    assert LATE_PENALTY > 3
    assert advisory_forecast() == 18.0
    assert is_anomalous(95.0) is True
    assert is_anomalous(16.0) is False
    assert mean_absolute_error([18.0, 20.0], [18.0, 19.0]) == 0.5
    assert "material_availability" in constraint_names()


def test_source_records_normalize_into_events() -> None:
    event = machine_failure_event(
        {
            "event_id": " evt-1001 ",
            "occurred_at": "2026-11-13T10:00:00Z",
            "factory_id": "PLANT-A",
            "machine_id": "PRESS-220",
            "new_status": "DOWN",
            "reason": "hydraulic_pressure_fault",
            "source_sequence": 2,
        }
    )
    parsed = parse_event(event)
    assert parsed.event_id == "evt-1001"
    assert parsed.source_system == "synthetic-mes"
    demand = demand_event(
        {
            "event_id": "evt-3001",
            "occurred_at": "2026-11-13T10:10:00Z",
            "order_id": "CO-2001",
            "product_id": "PRODUCT-A",
            "quantity": 20,
            "reason": "demand_surge",
            "source_sequence": 1,
        }
    )
    assert parse_event(demand).quantity == 20
    bom = requirement(
        {"product_id": "PRODUCT-A", "material_id": "SEAL-KIT-220", "quantity_per_unit": 1}
    )
    assert bom["quantity_per_unit"] == 1


def test_demo_prints_the_measured_plan() -> None:
    from industrial_ai.demo import run_demo

    text = run_demo(clock=lambda: "2026-11-12T15:00:00Z")
    assert "Solver status: OPTIMAL" in text
    assert "Objective: 72" in text
    assert "Unmet demand: 0" in text
    assert "Late: 2" in text
    assert "Decision status: REQUIRES_APPROVAL" in text
    assert "Constraint violations: 0" in text
    assert "No operational action performed before approval" in text
    assert "Simulated systems only" in text
    assert "Inventory lot LOT-1001 remains 14" in text
    assert "Normal objective: 54" in text
    assert "Name-order baseline objective: 74" in text
