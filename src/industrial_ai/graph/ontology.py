"""Node labels and relationship types the operational graph is allowed to store."""

NODE_LABELS: frozenset[str] = frozenset(
    {
        "Factory",
        "ProductionLine",
        "Machine",
        "Supplier",
        "Material",
        "Warehouse",
        "InventoryLot",
        "Product",
        "ProductionOrder",
        "CustomerOrder",
        "TransportRoute",
        "MaintenanceEvent",
    }
)

RELATIONSHIPS: frozenset[str] = frozenset(
    {
        "HAS_LINE",
        "HAS_MACHINE",
        "PRODUCES",
        "REQUIRES",
        "SUPPLIES",
        "STORES",
        "OF_MATERIAL",
        "SCHEDULED_AT",
        "REQUESTS",
        "CONNECTS_TO",
        "AFFECTS",
        "DESTINED_TO",
        "USES",
    }
)

# DESTINED_TO and USES are extensions. The required operational relationships
# are the other names in this set. Cypher labels cannot be query parameters,
# so the Neo4j writer interpolates only values from these two sets.
