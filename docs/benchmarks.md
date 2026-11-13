# Benchmarks

Source file: `benchmarks/latest.json`. Price: none.

## Hardware and software

| Item | Recorded value |
| --- | --- |
| Processor | 11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz |
| Cores | 4 |
| Logical processors | 8 |
| System | Windows |
| Python | 3.12.10 |
| OR-Tools | 9.15.6755 |
| Store | sqlite |
| Graph | in-memory |
| Neo4j | not-run |
| Kafka | not-run |
| PostgreSQL | sqlite-default |

## Method

`scripts/benchmark.py` resets the hand scenario, then times ingest plus solve. The catalog rebuild is outside the timer. Repeats: 40. Each sample uses a new event id and sequence. The loop asserts objective 72 and no constraint violations. The solver time limit passed by the platform is 5.0 seconds.

Nearest-rank p95 uses `math.ceil`. After the loop, one plan is approved and executed, then executed again. `invalid_executed_plans` is 1 if the lot is not 4 or the second call is not idempotent. This run recorded 0.

The graph-query timer is 100 in-memory impact walks for PRESS-220 on the seeded catalog. It is not a Neo4j round trip.

The scale build is a separate in-memory graph: 5,000 products, 2,000 machines, 50 PRODUCES edges each, and 10,000 orders. It is not loaded into Neo4j and it is not the event-to-plan timer.

## Results

| Metric | Value | How to read it |
| --- | --- | --- |
| Event-to-plan p95 | 0.032483 seconds | Ingest plus solve, hand scenario, 40 repeats. Bar of 2 seconds met for this scenario only. |
| Solver wall min / p50 / max | 0.006555 / 0.009827 / 0.019853 seconds | The 5 second limit did not fire. |
| Graph impact p95 | 1.1 microseconds | In-memory walk. Full value `1.1000010999850929e-06` seconds. |
| Invalid executed plans | 0 | One approve, one execute, one replay. |
| Scale entities / relationships | 17,000 / 110,000 | In-memory. Build 0.178426 seconds. One impact 0.000071 seconds. Neo4j not-run. |
| Seeded catalog | 190 entities, 1,027 relationships | Seed 7. Not the scale graph. |

Exact JSON numbers override the rounded phrases above.

## What this file is not

It is not a network service latency. It is not a Neo4j or Kafka result. It is not evidence that 10,000 customer orders were optimized. It is not a price or a capacity claim for a plant. The 2 second bar and the zero invalid executions are acceptance checks for the small scenario that was actually run.
