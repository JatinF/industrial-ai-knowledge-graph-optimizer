"""Prometheus text exposition for process-local counters and observations."""


class Metrics:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.observations: dict[str, list[float]] = {}

    def inc(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def observe(self, name: str, value: float) -> None:
        self.observations.setdefault(name, []).append(value)

    def render(self) -> str:
        lines: list[str] = []
        for name in sorted(self.counters):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {self.counters[name]}")
        for name in sorted(self.observations):
            values = self.observations[name]
            total = sum(values)
            lines.append(f"# TYPE {name} summary")
            lines.append(f"{name}_count {len(values)}")
            lines.append(f"{name}_sum {total}")
        return "\n".join(lines) + "\n"
