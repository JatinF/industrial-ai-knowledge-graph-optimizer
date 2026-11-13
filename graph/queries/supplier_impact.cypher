MATCH (s:Supplier {id: $supplier_id})-[:SUPPLIES]->(m:Material)
      <-[:REQUIRES]-(p:Product)
      <-[:REQUESTS]-(o:CustomerOrder)
RETURN
  s.id AS supplier_id,
  m.id AS material_id,
  p.id AS product_id,
  collect(DISTINCT o.id) AS candidate_orders
