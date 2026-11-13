# ADR 0002 — Neo4j as the server shape, in-memory as the measured graph

## Status

Accepted.

## Decision

The running graph in tests and the demo is the in-memory repository. Neo4j is the server the Cypher files and `storage/neo4j.py` target. The driver connects only when `NEO4J_URI` passes the host gate.

## Why

This workstation has no Neo4j binary and no Docker. The decision demo still has to run. Cypher constraints and parameterized queries stay in the repository so a local bolt URL can load the same ontology.

## Consequences

Impact timings in `benchmarks/latest.json` are in-memory walks. They are not Neo4j latencies. A Gremlin adapter is not part of this version. Uniqueness is enforced in memory and declared in `graph/schema.cypher`.
