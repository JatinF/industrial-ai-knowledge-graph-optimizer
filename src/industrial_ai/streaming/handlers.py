"""Route a bus message to ingestion. Replanning notices are not ingested as events."""

from typing import Any

from industrial_ai.streaming.topics import DEAD_LETTER, ORDERS, REPLANNING, SUPPLIER, TELEMETRY


def classify(topic: str) -> str:
    if topic in {TELEMETRY, SUPPLIER, ORDERS}:
        return "ingest"
    if topic == REPLANNING:
        return "notice"
    if topic == DEAD_LETTER:
        return "dead-letter"
    return "ignore"


def dead_letter_body(reason: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"reason": reason, "payload": payload}
