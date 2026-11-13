"""Threshold detector for synthetic vibration readings.

A reading at or above the threshold is flagged. The flag is not a machine state
and it does not change capacity.
"""


def is_anomalous(value: float, *, threshold: float = 80.0) -> bool:
    return value >= threshold


def advisory_anomaly() -> bool:
    return is_anomalous(95.0)
