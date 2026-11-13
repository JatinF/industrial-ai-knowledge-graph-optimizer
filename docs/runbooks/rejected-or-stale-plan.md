# Rejected or stale plan

## Rejected

The operator calls reject. The plan status becomes rejected. Execute returns an error and does not change LOT-1001. Approve after reject does not turn the plan into an execution.

## Stale snapshot

Execute compares the plan's snapshot revision with the store revision. They must match. A newer accepted event, with a new event id, bumps the revision. Execute then returns `stale_snapshot`, rolls back, and leaves the lot at 14.

Approval alone does not consume the lot. The demo never approves, so the lot stays 14 through the printed transcript.

## Second apply

After a successful execute the lot is 4 and finished PRODUCT-A is 10. The execution row is keyed by plan id. The next execute returns that row with `idempotent` true and does not decrement again.

## Who may call

SYN-USER-OPERATOR, and only if that person did not request the plan. SYN-USER-PLANNER receives 403 on approve and execute. An infeasible plan and a stopped plan are refused before any inventory update.
