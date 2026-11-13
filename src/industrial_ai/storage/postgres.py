"""PostgreSQL is optional. Unset DATABASE_URL stays on SQLite and is not contacted."""

import os

from industrial_ai.runtime_gates import gate, require_contact
from industrial_ai.storage.relational import OperationalStore


def postgres_store_from_env(url: str | None = None) -> OperationalStore:
    chosen = os.environ.get("DATABASE_URL") if url is None else url
    status = gate(chosen)
    if status == "not-run":
        raise RuntimeError("postgres not-run")
    if status == "blocked":
        raise RuntimeError("remote database blocked")
    safe = require_contact(chosen)
    try:
        return OperationalStore(safe)
    except Exception as exc:
        raise RuntimeError("postgres connection failed") from exc
