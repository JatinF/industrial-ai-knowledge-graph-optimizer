# ADR 0007 — Synthetic bearer identities

## Status

Accepted.

## Decision

SYN-USER-PLANNER uses token `lab-planner`. SYN-USER-OPERATOR uses token `lab-operator`. Matching checks length, then `secrets.compare_digest`. These tokens are not issued by an external identity provider.

## Why

The approval tests need two stable identities. A client-supplied `approved` flag would collapse that check.

## Consequences

The tokens are fixtures in source. They authorize nothing outside this process. Replacing them with a real issuer is future work and is not claimed here.
