"""Duplicate detection is the event id, which does not change when a source retries."""

from industrial_ai.storage.relational import OperationalStore


def already_stored(store: OperationalStore, event_id: str) -> bool:
    return store.get_event(event_id) is not None
