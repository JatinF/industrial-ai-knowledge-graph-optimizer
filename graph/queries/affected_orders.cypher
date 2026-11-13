MATCH (m:Machine {id: $machine_id})
      -[:PRODUCES]->(product:Product)
      <-[:REQUESTS]-(order:CustomerOrder)
RETURN
  m.id AS failed_machine,
  product.id AS affected_product,
  collect(DISTINCT order.id) AS candidate_orders
