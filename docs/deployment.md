# Deployment

![What ran on this workstation](diagrams/deployment.svg)

## Workstation path

This is the path that produced the demo transcript and `benchmarks/latest.json`.

- OS: Windows. Processor: 11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz. 4 cores. 8 logical processors.
- Python 3.12.10 in the project virtual environment `.venv`.
- Install: `pip install -e ".[dev]"`.
- Store: SQLite through SQLAlchemy, `sqlite://` with `StaticPool` and `check_same_thread=False`. A `DATABASE_URL` in the environment does not redirect unit tests. Live tests opt in.
- Graph: in-memory. `NEO4J_URI` unset, so the adapter status is `not-run`.
- Bus: in-process. `KAFKA_BOOTSTRAP` and `KAFKA_BOOTSTRAP_SERVERS` unset. `confluent-kafka` was not installed.
- Commands: `scripts/run_demo.py`, `python -m pytest`, `ruff check src tests scripts`, `mypy`, `scripts/benchmark.py`.

Docker, kubectl, Neo4j, Kafka, psql, and Java were not available on this workstation. A local image build was not run.

## Compose sketch

`docker-compose.yml` describes postgres:16, neo4j:5, apache/kafka:3.9.1, and an API image built from the Dockerfile. The API service sets `INDUSTRIAL_AI_ALLOW_REMOTE=1` and points at the service hostnames. That file was not started here.

The Dockerfile uses `python:3.12-slim`, creates user id 10001, and starts `python -m industrial_ai serve`. `.dockerignore` leaves out `.venv`, caches, `.env`, benchmarks, and tests.

## GitHub Actions

`.github/workflows/ci.yml` defines three jobs on `ubuntu-24.04`:

| Job | What it runs |
| --- | --- |
| `test` | `pip install -e ".[dev]"`, ruff, mypy, pytest. Adapter URLs are not set. |
| `integration` | Neo4j 5 and Postgres 16 service containers. `pip install -e ".[dev,postgres]"`. Only `tests/integration/test_live_adapters.py`. |
| `docker-build` | `docker build` and `docker compose config`. The stack is not started. |

The integration job uses `bolt://localhost:7687` with user `neo4j` and password `lab-password`, and `postgresql+psycopg://lab:lab@127.0.0.1:5432/labdb`. Those are lab fixtures for that job.

`.github/workflows/security.yml` runs `scripts/reject_private_keys.py`. There is no Kafka service in CI.

Actions results belong in the README evidence section only after a run is green and the annotation API has been read. A local pytest pass is not that evidence.

## Gates

| Variable | Unset | Local host | Other host |
| --- | --- | --- | --- |
| `NEO4J_URI` | not-run | driver may connect | blocked |
| `DATABASE_URL` | SQLite default | engine may connect | blocked |
| `KAFKA_BOOTSTRAP` or `KAFKA_BOOTSTRAP_SERVERS` | not-run | client may connect if installed | blocked |

`INDUSTRIAL_AI_ALLOW_REMOTE=1` turns a non-local host into `remote`. Leave it unset outside the compose file.
