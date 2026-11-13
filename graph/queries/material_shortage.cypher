MATCH (m:Material {id: $material_id})<-[:REQUIRES]-(p:Product)
      <-[:REQUESTS]-(o:CustomerOrder)
RETURN
  m.id AS material_id,
  p.id AS product_id,
  collect(DISTINCT o.id) AS candidate_orders
