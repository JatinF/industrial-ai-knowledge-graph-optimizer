"""Request dependencies. State-changing routes require a synthetic bearer token."""

from typing import Annotated

from fastapi import Header, Request

from industrial_ai.execution.approvals import Actor, require_actor, require_role
from industrial_ai.platform import Platform


def platform_of(request: Request) -> Platform:
    found = request.app.state.platform
    if not isinstance(found, Platform):
        raise RuntimeError("platform not configured")
    return found


def actor_of(authorization: Annotated[str | None, Header()] = None) -> Actor:
    if authorization is None or not authorization.startswith("Bearer "):
        return require_actor(None)
    return require_actor(authorization.removeprefix("Bearer ").strip())


def planner_of(authorization: Annotated[str | None, Header()] = None) -> Actor:
    actor = actor_of(authorization)
    require_role(actor, "planner", "operator")
    return actor


def operator_of(authorization: Annotated[str | None, Header()] = None) -> Actor:
    actor = actor_of(authorization)
    require_role(actor, "operator")
    return actor
