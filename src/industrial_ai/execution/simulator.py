"""Simulated ERP and inventory effects.

apply_execution writes the lot and the finished-good balance in the system of
record. It does not open a socket and it does not increment the controller
counter. A second call with the same plan id returns the stored effect.
"""

from typing import Any

from industrial_ai.storage.relational import OperationalStore


def produced_units(document: dict[str, Any]) -> int:
    allocation = document["allocation"]
    if not isinstance(allocation, dict):
        raise TypeError("allocation")
    total = 0
    for row in allocation["productions"]:
        total += int(row["quantity"])
    return total


def apply_simulated(
    store: OperationalStore,
    *,
    plan_id: str,
    expected_revision: int,
    lot_id: str,
    product_id: str,
    units: int,
    actor_id: str,
    applied_at: str,
    audit_id: str,
) -> dict[str, Any]:
    return store.apply_execution(
        plan_id=plan_id,
        expected_revision=expected_revision,
        lot_id=lot_id,
        consume=units,
        product_id=product_id,
        produce=units,
        actor_id=actor_id,
        applied_at=applied_at,
        audit_id=audit_id,
    )
