"""Reset and run one named synthetic scenario. Nothing is approved here."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from industrial_ai.api.deps import planner_of, platform_of
from industrial_ai.execution.approvals import Actor
from industrial_ai.platform import plan_public

router = APIRouter()


@router.post("/scenarios/reset")
def reset(
    request: Request,
    actor: Annotated[Actor, Depends(planner_of)],
    scenario_id: str = "normal_operations",
) -> dict[str, Any]:
    del actor
    return platform_of(request).reset(scenario_id)


@router.post("/scenarios/{scenario_id}/run")
def run(
    scenario_id: str,
    request: Request,
    actor: Annotated[Actor, Depends(planner_of)],
) -> dict[str, Any]:
    return plan_public(platform_of(request).run_scenario(scenario_id, actor))
