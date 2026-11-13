"""In-process publisher. A topic can be failed closed to simulate a disconnect."""

from typing import Any


class InProcessBus:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []
        self.cursor = 0
        self.fail_topics: set[str] = set()

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if topic in self.fail_topics:
            raise RuntimeError("bus unavailable")
        self.messages.append((topic, payload))

    def take_new(self) -> list[tuple[str, dict[str, Any]]]:
        rows = self.messages[self.cursor :]
        self.cursor = len(self.messages)
        return rows
