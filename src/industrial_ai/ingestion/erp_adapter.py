"""ERP order rows become DemandChanged events. No ERP host is contacted."""

from industrial_ai.ingestion.normalization import clean_id, clean_record


def demand_event(record: dict[str, object]) -> dict[str, object]:
    row = clean_record(record)
    quantity = row.get("quantity")
    if type(quantity) is not int:
        raise ValueError("quantity must be an integer")
    return {
        "schema_version": 1,
        "event_id": clean_id(row.get("event_id"), "event_id"),
        "event_type": "DemandChanged",
        "occurred_at": clean_id(row.get("occurred_at"), "occurred_at"),
        "source_system": "synthetic-erp",
        "order_id": clean_id(row.get("order_id"), "order_id"),
        "product_id": clean_id(row.get("product_id"), "product_id"),
        "quantity": quantity,
        "reason": clean_id(row.get("reason"), "reason"),
        "source_sequence": row.get("source_sequence"),
    }
