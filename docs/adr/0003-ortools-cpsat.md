# ADR 0003 — OR-Tools CP-SAT

## Status

Accepted.

## Decision

Allocation and scheduling are separate CP-SAT models. Shortfall is a variable. The application reports operational requirement separately from OPTIMAL or FEASIBLE.

## Why

Integer capacities, material totals, route caps, machine non-overlap, and downtime are constraint-programming problems. A graph walk does not produce a feasible quantity plan.

## Consequences

Coefficients are the integer units in `optimization/objectives.py`. The starter model keeps unmet weight 100. The two-period model uses 1000. Tests lock both. A cheaper objective that fails `constraint_violations` is not approvable.
