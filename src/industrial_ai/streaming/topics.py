"""Kafka topic names. The same names are used on the in-process bus."""

TELEMETRY = "industrial.telemetry.v1"
INVENTORY = "industrial.inventory.v1"
SUPPLIER = "industrial.supplier.v1"
ORDERS = "industrial.orders.v1"
REPLANNING = "industrial.replanning.v1"
DECISIONS = "industrial.decisions.v1"
DEAD_LETTER = "industrial.dead-letter.v1"

ALL_TOPICS: tuple[str, ...] = (
    TELEMETRY,
    INVENTORY,
    SUPPLIER,
    ORDERS,
    REPLANNING,
    DECISIONS,
    DEAD_LETTER,
)


def topic_for_event_type(event_type: object) -> str:
    if event_type == "MachineFailureDetected":
        return TELEMETRY
    if event_type == "SupplierDelayDetected":
        return SUPPLIER
    if event_type == "DemandChanged":
        return ORDERS
    return DEAD_LETTER
