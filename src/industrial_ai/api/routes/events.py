"""Ingest one operational event through the in-process bus."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from industrial_ai.api.deps import planner_of, platform_of
from industrial_ai.api.schemas.bodies import EventBody
from industrial_ai.domain.decisions import FlowError
from industrial_ai.execution.approvals import Actor

router = APIRouter()


@router.post("/events")
def post_event(
    body: EventBody,
    request: Request,
    actor: Annotated[Actor, Depends(planner_of)],
) -> dict[str, object]:
    return platform_of_event(request, body, actor)


def platform_of_event(request: Request, body: EventBody, actor: Actor) -> dict[str, object]:
    result = platform_of(request).submit_event(body.as_event(), actor)
    if result.get("accepted") or result.get("duplicate"):
        return result
    error = str(result.get("error") or "rejected")
    status = {"schema_rejected": 422, "stale_event": 409, "unresolved_entity": 422}.get(error, 400)
    raise FlowError(error, error, status)
