"""Bodies that must not carry an approval flag.

extra=forbid rejects a client field named approved. Approval is the operator
token on the approve route, not a boolean in the payload.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteBody(StrictBody):
    note: str = ""


class SolveBody(StrictBody):
    scenario_id: str | None = None


class EventBody(StrictBody):
    schema_version: int
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    source_sequence: int | None = None
    factory_id: str | None = None
    machine_id: str | None = None
    new_status: str | None = None
    reason: str | None = None
    supplier_id: str | None = None
    material_id: str | None = None
    order_id: str | None = None
    product_id: str | None = None
    quantity: int | None = None

    def as_event(self) -> dict[str, Any]:
        return {key: value for key, value in self.model_dump().items() if value is not None}
