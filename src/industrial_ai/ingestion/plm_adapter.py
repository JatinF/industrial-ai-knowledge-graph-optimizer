"""PLM bill-of-materials rows become REQUIRES properties. No PLM host is contacted."""

from industrial_ai.ingestion.normalization import clean_id, clean_record


def requirement(record: dict[str, object]) -> dict[str, object]:
    row = clean_record(record)
    quantity = row.get("quantity_per_unit")
    if type(quantity) is not int or quantity < 1:
        raise ValueError("quantity_per_unit must be a positive integer")
    return {
        "product_id": clean_id(row.get("product_id"), "product_id"),
        "material_id": clean_id(row.get("material_id"), "material_id"),
        "quantity_per_unit": quantity,
        "source_system": "synthetic-plm",
    }
