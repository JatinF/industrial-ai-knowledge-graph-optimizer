# Broker disconnect

The workstation path has no broker. This runbook is the in-process stand-in that the tests cover, and the behavior the Kafka gateway is written to keep.

## What you see

An accepted event is in SQLite. The replanning outbox row is still unpublished. Machine state has already changed once. A second apply would be a fault.

## What the code does

Ingest commits the event and the outbox row in one transaction. Publication is after that commit. If the replanning topic is in `fail_topics`, publication throws, the row stays unpublished, and the machine state is left as the commit wrote it.

`recover()` publishes unpublished outbox rows and does not call ingest again. A second `recover()` finds nothing new to publish.

Replanning notices are not fed back into the event handler.

## What was not exercised

A real Kafka disconnect, a consumer group rebalance, and a broker restart were not run. `confluent-kafka` was not installed. Do not treat a green unit test as a broker drill.
