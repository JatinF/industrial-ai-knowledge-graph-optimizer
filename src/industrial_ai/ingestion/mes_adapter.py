"""MES equipment records become MachineFailureDetected events. No socket is opened."""

from industrial_ai.domain.entities import MES
from industrial_ai.ingestion.normalization import clean_id, clean_record


def machine_failure_event(record: dict[str, object]) -> dict[str, object]:
    row = clean_record(record)
    return {
        "schema_version": 1,
        "event_id": clean_id(row.get("event_id"), "event_id"),
        "event_type": "MachineFailureDetected",
        "occurred_at": clean_id(row.get("occurred_at"), "occurred_at"),
        "source_system": MES,
        "factory_id": clean_id(row.get("factory_id"), "factory_id"),
        "machine_id": clean_id(row.get("machine_id"), "machine_id"),
        "new_status": clean_id(row.get("new_status"), "new_status"),
        "reason": clean_id(row.get("reason"), "reason"),
        "source_sequence": row.get("source_sequence"),
    }
