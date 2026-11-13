"""Operator approval, rejection, execution, and the audit read."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from industrial_ai.api.deps import operator_of, platform_of
from industrial_ai.api.schemas.bodies import NoteBody
from industrial_ai.execution.approvals import Actor
from industrial_ai.platform import plan_public

router = APIRouter()


@router.post("/plans/{plan_id}/approve")
def approve(
    plan_id: str,
    request: Request,
    actor: Annotated[Actor, Depends(operator_of)],
    body: NoteBody | None = None,
) -> dict[str, Any]:
    del body
    return plan_public(platform_of(request).approve(plan_id, actor))


@router.post("/plans/{plan_id}/reject")
def reject(
    plan_id: str,
    request: Request,
    actor: Annotated[Actor, Depends(operator_of)],
    body: NoteBody | None = None,
) -> dict[str, Any]:
    del body
    return plan_public(platform_of(request).reject(plan_id, actor))


@router.post("/plans/{plan_id}/execute")
def execute(
    plan_id: str,
    request: Request,
    actor: Annotated[Actor, Depends(operator_of)],
) -> dict[str, Any]:
    return platform_of(request).execute(plan_id, actor)


@router.get("/audit/events")
def audit(request: Request) -> dict[str, object]:
    return {"events": platform_of(request).audit()}
