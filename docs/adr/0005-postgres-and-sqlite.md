# ADR 0005 — PostgreSQL shape, SQLite by default

## Status

Accepted.

## Decision

The default system of record is SQLite. `db/migrations/001_operational.sql` names the same tables SQLAlchemy creates. PostgreSQL is contacted only when `DATABASE_URL` passes the host gate and the caller opts into the live adapter.

## Why

The demo and the unit tests must run with no database server. The integration workflow is where Postgres 16 is started.

## Consequences

There is no claim of a PostgreSQL latency or a migrated production database. The in-process lock around the store is not a distributed lock. Unit tests keep their own SQLite even if the environment has a database URL.
