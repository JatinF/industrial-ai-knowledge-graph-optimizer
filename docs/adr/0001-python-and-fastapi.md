# ADR 0001 — Python and FastAPI

## Status

Accepted for the measured path.

## Decision

The implementation language is Python 3.12. HTTP contracts are FastAPI and Pydantic. The same process holds the graph, the solver, and the store on the workstation path.

## Why

OR-Tools, the Neo4j driver, and FastAPI are all usable from one language. One process is enough to show a failure becoming a plan without a network.

## Consequences

The service is a single process. It is not a set of deployed microservices. OpenAPI is generated from the app and checked into `api/openapi.json`.
