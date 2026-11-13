"""Pull messages the in-process producer has not yet handed to a handler."""

from typing import Any

from industrial_ai.streaming.producer import InProcessBus


def take_new(bus: InProcessBus) -> list[tuple[str, dict[str, Any]]]:
    return bus.take_new()
