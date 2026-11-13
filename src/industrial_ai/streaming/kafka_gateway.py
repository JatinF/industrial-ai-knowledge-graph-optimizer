"""confluent-kafka is used only when a bootstrap address passes the gate.

Unset is not-run. A non-local host is blocked and the client is not constructed.
This workstation does not have a broker, so the default status is not-run.
"""

import json
import os
from typing import Any

from industrial_ai.runtime_gates import gate, require_contact


def _bootstrap() -> str | None:
    return os.environ.get("KAFKA_BOOTSTRAP") or os.environ.get("KAFKA_BOOTSTRAP_SERVERS")


def kafka_status() -> str:
    status = gate(_bootstrap())
    if status in {"not-run", "blocked"}:
        return status
    try:
        import confluent_kafka  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return "client-not-installed"
    return status


def publish_kafka(topic: str, payload: dict[str, Any]) -> str:
    status = kafka_status()
    if status != "local" and status != "remote":
        return status
    servers = require_contact(_bootstrap())
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": servers})
    producer.produce(topic, json.dumps(payload).encode("utf-8"))
    producer.flush(5.0)
    return "published"
