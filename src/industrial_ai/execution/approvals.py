"""Synthetic bearer identities. This is not an external identity provider.

lab-planner maps to SYN-USER-PLANNER. lab-operator maps to SYN-USER-OPERATOR.
Comparison is constant-time and rejects a different length before compare_digest.
An approval is a role and an identity. A JSON field named approved is not an approval.
"""

import secrets
from dataclasses import dataclass

from industrial_ai.domain.decisions import FlowError
from industrial_ai.domain.entities import OPERATOR_ID, OPERATOR_TOKEN, PLANNER_ID, PLANNER_TOKEN


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: str


_FIXTURES: tuple[tuple[str, Actor], ...] = (
    (PLANNER_TOKEN, Actor(PLANNER_ID, "planner")),
    (OPERATOR_TOKEN, Actor(OPERATOR_ID, "operator")),
)


def _matches(presented: str, expected: str) -> bool:
    if len(presented) != len(expected):
        return False
    return secrets.compare_digest(presented, expected)


def authenticate(token: str) -> Actor | None:
    for expected, actor in _FIXTURES:
        if _matches(token, expected):
            return actor
    return None


def require_actor(token: str | None) -> Actor:
    if token is None or token.strip() == "":
        raise FlowError("unauthorized", "bearer token required", 401)
    actor = authenticate(token.strip())
    if actor is None:
        raise FlowError("unauthorized", "unknown token", 401)
    return actor


def require_role(actor: Actor, *roles: str) -> None:
    if actor.role not in roles:
        raise FlowError("forbidden", "role not permitted", 403)
