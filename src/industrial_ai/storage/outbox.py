"""Transactional outbox rows are written with the operational change.

Publishing is a later step. A failed publish leaves the row unpublished so
recovery can send it once. Recovery does not apply the operational change again.
"""

import json
from typing import Any

from industrial_ai.storage.relational import OperationalStore


def unpublished(store: OperationalStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in store.pending_outbox():
        payload = json.loads(str(row["payload"]))
        if not isinstance(payload, dict):
            payload = {"raw": payload}
        rows.append(
            {"outbox_id": str(row["outbox_id"]), "topic": str(row["topic"]), "payload": payload}
        )
    return rows
