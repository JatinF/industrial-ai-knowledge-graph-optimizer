# Graph store unavailable

SQLite is the system of record on the measured path. The graph is a projection.

## Projection failure

The store commits first. The graph update runs after. If that update raises, the platform surfaces the projection error and does not pretend the graph is current.

`reconcile()` copies each entity's stored state and the inventory lot onto the graph. The test forces one projection failure, then reconciles, and expects the press to match the store.

## Divergent graph

If something sets the in-memory press to UP while the store still says DOWN, `reconcile()` puts DOWN back on the node. The store is not edited to match the graph.

## Neo4j

When `NEO4J_URI` is unset, the Neo4j driver is not constructed and there is nothing to reconnect. When the URI is a non-local host and the remote switch is unset, the call is blocked and the URL is not echoed.

A Neo4j outage on a live server was not injected on this workstation. The integration job is the place that contacts Neo4j, and only after that job is green.
