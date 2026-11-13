"""Read the audit log the store already wrote inside the same transaction."""

from typing import Any

from industrial_ai.storage.relational import OperationalStore


def records(store: OperationalStore) -> list[dict[str, Any]]:
    return store.list_audit()
