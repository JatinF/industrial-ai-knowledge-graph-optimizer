"""Solve and read plans. Approval and execution live on the approvals router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from industrial_ai.api.deps import planner_of, platform_of
from industrial_ai.api.schemas.bodies import SolveBody
from industrial_ai.execution.approvals import Actor
from industrial_ai.platform import plan_public

router = APIRouter()


@router.post("/plans/solve")
def solve(
    request: Request,
    actor: Annotated[Actor, Depends(planner_of)],
    body: SolveBody | None = None,
) -> dict[str, Any]:
    platform = platform_of(request)
    if body is not None and body.scenario_id is not None:
        return plan_public(platform.run_scenario(body.scenario_id, actor))
    return plan_public(platform.solve(actor))


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, request: Request) -> dict[str, Any]:
    return plan_public(platform_of(request).get_plan(plan_id))
