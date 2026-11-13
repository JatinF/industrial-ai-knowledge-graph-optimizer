"""IoT sensor identifiers resolve through the alias table. No broker is contacted."""

from industrial_ai.domain.entities import IOT
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.ingestion.entity_resolution import resolve
from industrial_ai.ingestion.normalization import clean_id


def canonical_machine(graph: OperationalGraph, sensor_id: str) -> str | None:
    return resolve(graph, IOT, clean_id(sensor_id, "sensor_id"))
