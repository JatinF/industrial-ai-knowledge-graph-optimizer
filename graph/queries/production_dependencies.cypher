MATCH (po:ProductionOrder)-[:PRODUCES]->(p:Product {id: $product_id})
      <-[:PRODUCES]-(m:Machine)
RETURN
  po.id AS production_order,
  p.id AS product_id,
  collect(DISTINCT m.id) AS machines
