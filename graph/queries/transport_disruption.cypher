MATCH (r:TransportRoute {id: $route_id})-[:CONNECTS_TO]->(w:Warehouse)
      <-[:DESTINED_TO]-(o:CustomerOrder)
RETURN
  r.id AS route_id,
  w.id AS warehouse_id,
  collect(DISTINCT o.id) AS candidate_orders
