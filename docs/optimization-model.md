# Optimization model

Two CP-SAT models share the process and do not share a decision vector.

Model A allocates PRODUCT-A across PLANT-A and PLANT-B for two periods. Model B schedules two jobs onto PRESS-220 and, when allowed, MILL-110. MILL-110 does not increase Model A capacity.

OR-Tools 9.15.6755 is the solver that produced the numbers below. Coefficients are integer cost-units for this model. They are not a universal plant policy.

## Objective

For the two-period model the solver minimizes:

```
1000 * unmet + 10 * late + transport_cost + production_cost
```

Transport cost is `quantity * 3` on the hand route. Production cost is `quantity * 3` at PLANT-A and `quantity * 2` at PLANT-B.

Unmet demand dominates one late unit. One late unit costs 10, which is more than shipping one unit (3) or making one unit at either plant (3 or 2). Tests lock that order. The code constants are `UNMET_PENALTY` and `LATE_PENALTY` in `optimization/objectives.py`.

The published starter uses a different unmet weight, 100, and a transport cost of 0. The solver selects that weight only when transport cost is 0, demand is 16, and late shipments are forbidden. The PRESS-220 scenario does not use it.

## Decision variables

For each plant and period 0 and 1:

- `produce[plant, period]` from 0 to that plant's larger period cap
- `ship[plant, period]` from 0 to the route capacity

Plus `on_time`, `late`, and `unmet`, each from 0 to demand.

`ship` is forced equal to `produce` for the same plant and period. There is one shared route, so the model does not choose among routes. `route_used` from a broader design is not a variable in this version.

## Constraints

- Produce at most the plant cap in that period. A down PRESS-220 sets PLANT-A's cap to 2.
- Sum of production across both periods is at most the material pool.
- Sum of shipments in one period is at most the route capacity.
- A shipment in period t arrives in period t+1. Period-0 arrivals count as on time. Period-1 arrivals count as late when `allow_late` is true.
- When `allow_late` is false, period-1 shipments and late units are 0.
- `on_time + late + unmet = demand`.
- When `forbid_shortfall` is true, unmet is 0. If the other constraints cannot reach demand, the status is INFEASIBLE.
- Maintenance removes capacity before the model is built. The solver does not treat a down machine as available.

Customer fulfillment cannot exceed demand because on-time, late, and unmet sum to demand and each is non-negative.

## Hand calculation, normal operations

Demand 10, materials 14, route capacity 20, both plants available in period 0 (caps 8 and 6).

The cheapest feasible on-time plan fills period 0 from PLANT-B first: 6 at cost 2, then 4 at PLANT-A at cost 3. Period 1 is unused.

- Production cost `3*4 + 2*6 = 24`
- Transport cost `10*3 = 30`
- Late and unmet penalties `0`
- Objective `54`
- On time 10, late 0, unmet 0
- Operational requirement met

## Hand calculation, PRESS-220 down

PLANT-A cap is 2. Period 0 can ship `2+6 = 8`. The remaining 2 ship in period 1 from the cheaper plant.

- Period 0: PLANT-A 2, PLANT-B 6
- Period 1: PLANT-B 2
- Production cost `3*2 + 2*6 + 2*2 = 22`
- Transport cost `30`
- Late penalty `2*10 = 20`
- Objective `72`
- On time 8, late 2, unmet 0
- Solver status OPTIMAL
- Operational requirement not met
- Decision status REQUIRES_APPROVAL

Name-order greedy fills PLANT-A before PLANT-B, so the period-1 pair is made at PLANT-A. Production cost becomes 24 and the objective becomes 74. Unmet demand is not better than the solver. The solver's cost and objective are strictly lower, and the feasibility checker accepts the solver point.

## Other locked points

| Case | Result |
| --- | --- |
| On time only, PLANT-A cap 2 | OPTIMAL, on time 8, unmet 2, objective 2042. Not the proposed plan. |
| Period 0 blocked | On time 0, late 10, unmet 0, objective 154. |
| Route capacity 5 | On time 5, late 5, unmet 0. The test locks the quantities. |
| Materials 4, late allowed | OPTIMAL, on time 4, unmet 6, objective 6020, all of it on PLANT-B. |
| Materials 4, late forbidden, shortfall forbidden | INFEASIBLE. |
| Demand 20, caps 8 and 6, materials 14 | On time 14, unmet 6, objective 6078. |

`6000 + 4*2 + 4*3 = 6020` is the material-shortage objective. `6000 + 8*3 + 6*2 + 14*3 = 6078` is the demand-surge objective.

## Starter model

`optimize()` is the small model from the design note. Caps 8 and 6, demand 16, materials 14, unmet weight 100, plant costs 3 and 2, no transport charge.

The optimum uses the cheaper plant to its cap and then plant A: plant A 8, plant B 6, unfulfilled 2, objective `100*2 + 3*8 + 2*6 = 236`.

`optimize(max_b=2)` is that starter's capacity cut. It is not PRESS-220. Plant A 8, plant B 2, unfulfilled 6, objective `100*6 + 3*8 + 2*2 = 628`.

## Schedule model

Horizon 20. JOB-2 starts at or after JOB-1 ends. Each job is assigned to exactly one machine. Optional interval variables and `add_no_overlap` keep a machine from running both jobs at once. If maintenance is on, a job present on PRESS-220 must start at time 5 or later.

| Case | Makespan | Machines |
| --- | --- | --- |
| No maintenance, alternate available | 7 | either machine can hold the chain |
| Maintenance, MILL-110 available | 7 | both jobs on MILL-110 |
| Maintenance, no alternate | 12 | both jobs on PRESS-220, JOB-1 start at least 5 |

## Feasibility versus the solver status

`constraint_violations` recomputes capacity, materials, route totals, lead time, the ship-equals-produce rule, and the objective identity. A violation blocks approval even if the status is OPTIMAL or FEASIBLE.

INFEASIBLE and any other status, including UNKNOWN, cannot be approved. UNKNOWN is the stand-in the timeout test uses. The bench maximum wall time was under 0.02 seconds, so the 5 second `max_time_in_seconds` limit was not what stopped a solve.

## Baseline

`plan_greedy` walks plants in id order, period 0 then period 1, and uses the unmet weight 1000. Its status string is GREEDY. It is the comparison in the quality tests. It is not applied to inventory.
