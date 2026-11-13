# Solver timeout

The platform calls the allocation solver with `max_time_seconds=5.0`. That value is passed to CP-SAT as `max_time_in_seconds`.

## What a stop looks like

If the returned status is not OPTIMAL or FEASIBLE, the decision status is SOLVER_STOPPED, or INFEASIBLE when the status is exactly INFEASIBLE. Neither status can be approved. Execute is refused. The lot does not change.

UNKNOWN is handled by the same branch as a stop. The test replaces `solve_allocation` with a function that returns UNKNOWN. That is a policy test. It does not measure a solver that ran out of time.

## What the bench showed

On 40 hand-scenario solves the longest wall time was 0.019853 seconds. The 5 second limit did not stop those solves. Do not report a timeout as something this bench observed.

## What to do

Leave the plan unapproved. Read `solver_status` and `decision_status` on the plan. A later solve after the inputs change is a new plan id. Do not execute the stopped plan.
