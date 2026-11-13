MATCH (asset {id: $asset_id})-[rel]-(other)
RETURN
  asset.id AS asset_id,
  type(rel) AS relationship,
  other.id AS other_id,
  labels(other) AS other_labels
