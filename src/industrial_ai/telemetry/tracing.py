"""Correlation id carried from ingest through the plan response.

The id is generated here. OpenTelemetry packages may be installed with FastAPI.
This process does not export spans to a collector.
"""

from uuid import uuid4


def new_trace_id() -> str:
    return "trace-" + uuid4().hex[:16]
