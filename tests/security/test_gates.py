"""Remote URLs are blocked before a client is constructed. Values are not echoed."""

import neo4j

from industrial_ai.runtime_gates import gate
from industrial_ai.storage.neo4j import load_and_impact
from industrial_ai.storage.postgres import postgres_store_from_env
from industrial_ai.streaming.kafka_gateway import kafka_status


def test_unset_adapters_are_not_run(monkeypatch: object) -> None:
    monkeypatch.delenv("NEO4J_URI", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("DATABASE_URL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("KAFKA_BOOTSTRAP", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)  # type: ignore[attr-defined]
    assert gate(None) == "not-run"
    assert kafka_status() == "not-run"


def test_remote_neo4j_does_not_construct_a_driver(monkeypatch: object) -> None:
    calls: list[str] = []

    def boom(*_args: object, **_kwargs: object) -> None:
        calls.append("driver")
        raise AssertionError("driver constructed")

    monkeypatch.setattr(neo4j.GraphDatabase, "driver", boom)  # type: ignore[attr-defined]
    monkeypatch.setenv("NEO4J_URI", "bolt://remote.example:7687")  # type: ignore[attr-defined]
    result = load_and_impact(
        __import__("industrial_ai.catalog", fromlist=["build_catalog"]).build_catalog(), "PRESS-220"
    )
    assert result["status"] == "blocked"
    assert calls == []
    assert "remote.example" not in str(result)


def test_remote_postgres_and_kafka_are_blocked(monkeypatch: object) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)  # type: ignore[attr-defined]
    try:
        postgres_store_from_env("postgresql+psycopg://lab:lab@remote.example:5432/labdb")
    except RuntimeError as exc:
        assert "blocked" in str(exc)
        assert "remote.example" not in str(exc)
    else:
        raise AssertionError("remote database was accepted")
    monkeypatch.setenv("KAFKA_BOOTSTRAP", "remote.example:9092")  # type: ignore[attr-defined]
    assert kafka_status() == "blocked"


def test_private_key_scanner_catches_a_marker(tmp_path: object) -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(str(tmp_path))
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    (root / "sample.pem").write_text(marker + "\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "scripts" / "reject_private_keys.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    clean = subprocess.run(
        [sys.executable, str(script), str(Path(__file__).resolve().parents[2] / "src")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert clean.returncode == 0
