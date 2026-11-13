"""Decide whether a configured service URL may be contacted.

Unset means not-run. A localhost URL may be contacted. Any other host is
blocked unless INDUSTRIAL_AI_ALLOW_REMOTE=1, which is the switch a composed
deployment sets on purpose. Blocked calls do not open a socket and do not
include the URL in the error text.
"""

import os

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def endpoint_host(value: str) -> str:
    rest = value.split("://", 1)[-1]
    rest = rest.split("/", 1)[0]
    if "@" in rest:
        rest = rest.split("@", 1)[1]
    return rest.split(":", 1)[0].strip("[]")


def gate(value: str | None, *, allow_remote: bool | None = None) -> str:
    if value is None or value.strip() == "":
        return "not-run"
    if allow_remote is None:
        allow_remote = os.environ.get("INDUSTRIAL_AI_ALLOW_REMOTE") == "1"
    host = endpoint_host(value)
    if host in LOCAL_HOSTS:
        return "local"
    if allow_remote:
        return "remote"
    return "blocked"


def require_contact(value: str | None) -> str:
    """Return the URL only after the gate allows it. Raise without echoing it."""

    status = gate(value)
    if status in {"local", "remote"}:
        if value is None:
            raise RuntimeError("endpoint missing")
        return value
    if status == "not-run":
        raise RuntimeError("endpoint not-run")
    raise RuntimeError("remote endpoint blocked")


def adapter_report() -> dict[str, str]:
    kafka = os.environ.get("KAFKA_BOOTSTRAP") or os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
    database = os.environ.get("DATABASE_URL")
    return {
        "neo4j": gate(os.environ.get("NEO4J_URI")),
        "kafka": gate(kafka),
        "postgres": "sqlite-default" if not database else gate(database),
    }
