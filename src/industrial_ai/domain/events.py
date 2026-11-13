"""Versioned operational events.

schema_version 1 is the only accepted contract. occurred_at is the source
time. The store records ingestion time separately.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MachineFailureDetected(_Strict):
    schema_version: Literal[1]
    event_id: str = Field(min_length=1)
    event_type: Literal["MachineFailureDetected"]
    occurred_at: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    factory_id: str = Field(min_length=1)
    machine_id: str = Field(min_length=1)
    new_status: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_sequence: int | None = None


class SupplierDelayDetected(_Strict):
    schema_version: Literal[1]
    event_id: str = Field(min_length=1)
    event_type: Literal["SupplierDelayDetected"]
    occurred_at: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    new_status: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_sequence: int | None = None


class DemandChanged(_Strict):
    schema_version: Literal[1]
    event_id: str = Field(min_length=1)
    event_type: Literal["DemandChanged"]
    occurred_at: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    reason: str = Field(min_length=1)
    source_sequence: int | None = None


ParsedEvent = MachineFailureDetected | SupplierDelayDetected | DemandChanged


def parse_event(payload: object) -> ParsedEvent:
    if not isinstance(payload, dict):
        raise ValueError("event payload must be an object")
    version = payload.get("schema_version")
    if version != 1:
        raise ValueError("unsupported schema_version")
    event_type = payload.get("event_type")
    if event_type == "MachineFailureDetected":
        return MachineFailureDetected.model_validate(payload)
    if event_type == "SupplierDelayDetected":
        return SupplierDelayDetected.model_validate(payload)
    if event_type == "DemandChanged":
        return DemandChanged.model_validate(payload)
    raise ValueError("unsupported event_type")
