"""Load a scenario file. Inputs live in the file. Expected objectives live in tests."""

import json
from dataclasses import dataclass
from typing import Any

from industrial_ai.domain.decisions import FlowError
from industrial_ai.paths import repo_root

SCENARIO_IDS: tuple[str, ...] = (
    "normal_operations",
    "machine_failure",
    "supplier_delay",
    "demand_surge",
    "infeasible_schedule",
)


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    title: str
    factory_id: str
    asset_id: str
    on_hand: int
    inbound: int
    base_demand: int
    allow_late: bool
    forbid_shortfall: bool
    event: dict[str, Any] | None


def _as_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise FlowError("scenario_invalid", f"{field} must be an integer", 500)
    return value


def load_scenario(scenario_id: str) -> ScenarioSpec:
    if scenario_id not in SCENARIO_IDS:
        raise FlowError("not_found", "unknown scenario", 404)
    path = repo_root() / "datasets" / "scenarios" / f"{scenario_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FlowError("scenario_invalid", "scenario file must be an object", 500)
    event = raw.get("event")
    if event is not None and not isinstance(event, dict):
        raise FlowError("scenario_invalid", "event must be an object", 500)
    return ScenarioSpec(
        scenario_id=str(raw["id"]),
        title=str(raw["title"]),
        factory_id=str(raw["factory_id"]),
        asset_id=str(raw["asset_id"]),
        on_hand=_as_int(raw["on_hand"], "on_hand"),
        inbound=_as_int(raw["inbound"], "inbound"),
        base_demand=_as_int(raw["base_demand"], "base_demand"),
        allow_late=bool(raw["allow_late"]),
        forbid_shortfall=bool(raw["forbid_shortfall"]),
        event=event,
    )
