# Threat model

This process simulates a planning desk. The assets worth protecting are the plan record, the simulated inventory lot, and the audit trail. There is no plant network, no customer tenant, and no external identity provider.

## Trust boundary

Inside the process: FastAPI, the in-memory graph, SQLite, OR-Tools, and the in-process bus.

Outside, and not contacted on the workstation that produced the evidence: Neo4j, Kafka, PostgreSQL, Docker, Grafana, and any industrial controller. Health reads the gate result. It does not open those sockets.

A URL whose host is not `localhost`, `127.0.0.1`, or `::1` is blocked. The exception text does not include the URL. `INDUSTRIAL_AI_ALLOW_REMOTE=1` is the compose-file switch for service DNS. The workstation demo leaves it unset.

The flow test replaces socket creation and expects the failure scenario to make no connection.

## Identities

| Identity | Token | May do |
| --- | --- | --- |
| SYN-USER-PLANNER | `lab-planner` | Reset, run a scenario, ingest, solve |
| SYN-USER-OPERATOR | `lab-operator` | Approve, reject, execute |

Tokens are fixture strings. `secrets.compare_digest` runs only after the lengths match. A missing or unknown bearer is 401. A known bearer in the wrong role is 403.

The approver's user id must differ from the requester's user id. The planner cannot approve a plan they requested, and cannot execute.

Reads of health, assets, graph, a stored plan, audit, and metrics do not require a bearer.

## What is refused

| Action | Result |
| --- | --- |
| Body field `approved: true` without the operator call | Not an approval. The route does not read that field as authority. |
| Approve an INFEASIBLE, BLOCKED, or SOLVER_STOPPED plan | Refused. Inventory unchanged. |
| Execute a rejected plan | Refused. |
| Execute when the store revision moved | `stale_snapshot`. Transaction rolled back. |
| Execute when the lot cannot cover consumption | `inventory_short`. Transaction rolled back. |
| Execute the same plan again | Returns the first effect. Lot and finished goods stay put. |
| Replay the same `event_id` | No second state change. |
| Older sequence after a newer one | Press state stays at the newer value. |
| Unsupported schema version | Dead letter. No state change. |
| Remote adapter URL | No driver, engine, or producer is constructed. |

## Integrity of the simulated write

The execution row's primary key is the plan id. The decrement, the finished-goods increase, the execution insert, the revision bump, and the audit row are one transaction. A second call sees the execution row and returns before another decrement.

Graph projection is not the source of truth for that write. If the projection fails, reconcile restores the graph from the store. A manually corrupted graph state is corrected the same way.

## Secrets in the repository

`.env.example` ships empty values. The CI workflow contains the lab passwords `lab` and `lab-password` for the throwaway Postgres and Neo4j service containers. Those values authorize nothing outside that job. The private-key scanner fails the security workflow if a PEM private-key marker is committed. The scanner source splits the marker so it does not match itself.

## Out of scope

This model does not claim resistance to a person who can edit the SQLite file, the source, or the fixture tokens. It does not authenticate operators against a company directory. It does not encrypt the in-process bus. It does not rate-limit the open read routes.
