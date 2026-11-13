# ADR 0006 — A person approves before a simulated write

## Status

Accepted.

## Decision

A clean solver result is stored as a proposal. Inventory changes only on execute, after a different person has approved, and only if the snapshot revision still matches. Rejection writes nothing. A second execute does not apply again.

## Why

OPTIMAL can still leave demand late or unmet. The planning identity that requested the solve must not be the identity that authorizes the write.

## Consequences

The demo stops before approval and leaves LOT-1001 at 14. There is no policy engine such as OPA in this repository. Authorization is the two fixture roles in `execution/approvals.py`.
