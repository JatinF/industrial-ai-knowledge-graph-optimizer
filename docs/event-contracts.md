# Event contracts

The measured path uses an in-process bus. Topic names match the design. A Kafka broker was not started, and the `confluent-kafka` package was not installed in the workstation environment. The producer class is constructed only after the host gate allows the URL and the import succeeds.

## Topics

| Topic | Use |
| --- | --- |
| `industrial.telemetry.v1` | `MachineFailureDetected` |
| `industrial.inventory.v1` | Reserved name. Inventory changes in this version go through the store. |
| `industrial.supplier.v1` | `SupplierDelayDetected` |
| `industrial.orders.v1` | `DemandChanged` |
| `industrial.replanning.v1` | Outbox notice after an accepted event. Not ingested as a new event. |
| `industrial.decisions.v1` | Reserved name for plan lifecycle notices. |
| `industrial.dead-letter.v1` | Rejected schema or an unknown event type. |

`topic_for_event_type` sends anything else, including the internal dead-letter marker, to `industrial.dead-letter.v1`.

## Machine failure

The scenario file `datasets/scenarios/machine_failure.json` carries:

```json
{
  "schema_version": 1,
  "event_id": "evt-1001",
  "event_type": "MachineFailureDetected",
  "occurred_at": "2026-11-13T10:00:00Z",
  "source_system": "synthetic-mes",
  "factory_id": "PLANT-A",
  "machine_id": "PRESS-220",
  "new_status": "DOWN",
  "reason": "hydraulic_pressure_fault",
  "source_sequence": 2
}
```

The same body without `source_sequence` is accepted once. That is the event-time policy for a first unsequenced event.

## Rules the tests lock

- `event_id` is the idempotency key. A second delivery returns `duplicate` and does not bump the revision.
- `occurred_at` is the source time. `ingested_at` is the process clock. The failure-flow tests pin that clock at `2026-11-12T15:00:00Z`.
- `schema_version` must be 1. Version 2 is rejected, dead-lettered, and leaves the press DOWN.
- A sequenced event is stale when its sequence is less than or equal to the stored sequence. With no stored row the floor is -1, so sequence 2 applies.
- An unsequenced event is stale when `occurred_at` is less than or equal to the stored `occurred_at`.
- A later unsequenced event must not reset a stored sequence down to 0. The store keeps `max(current, 0)`.
- A factory that does not match the machine, or an id that does not resolve, is rejected.
- `synthetic-iot` / `SYN-SENSOR-220` resolves to PRESS-220 and keeps both source identifiers.
- If the replanning topic is marked failed, the event still commits, the outbox stays unpublished, and `recover()` publishes once without applying the state again.

## Processing order

1. Validate the body and the schema version.
2. Drop a duplicate id.
3. Drop a stale sequence or a stale event time.
4. Commit the event, the entity clock, and the outbox row.
5. Project the machine state onto the graph, or reconcile later from the store.
6. Build a snapshot at the new revision and solve.
7. Leave the plan at REQUIRES_APPROVAL when the point is clean.

The solver does not run on a snapshot whose revision has already moved on by the time execute is called.
