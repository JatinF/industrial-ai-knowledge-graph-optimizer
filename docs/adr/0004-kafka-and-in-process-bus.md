# ADR 0004 — Kafka topic names, in-process bus

## Status

Accepted for this version.

## Decision

The seven `industrial.*.v1` topic names are real constants. Delivery on the measured path is an in-process bus with a cursor, deduplication, and an outbox. `confluent-kafka` is an optional extra. The producer is constructed only after the host gate allows it and the import succeeds.

## Why

No broker is installed here, and CI does not start one. The failure workflow still needs idempotency, a dead letter, and a recoverable outbox.

## Consequences

Broker restart, consumer groups, and network delay are not measured. The runbook `docs/runbooks/broker-disconnect.md` describes the in-process failure the tests cover.
