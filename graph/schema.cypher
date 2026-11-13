CREATE CONSTRAINT factory_id_unique IF NOT EXISTS
FOR (n:Factory) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT line_id_unique IF NOT EXISTS
FOR (n:ProductionLine) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT machine_id_unique IF NOT EXISTS
FOR (m:Machine) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT supplier_id_unique IF NOT EXISTS
FOR (n:Supplier) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT material_id_unique IF NOT EXISTS
FOR (n:Material) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT warehouse_id_unique IF NOT EXISTS
FOR (n:Warehouse) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT lot_id_unique IF NOT EXISTS
FOR (n:InventoryLot) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT product_id_unique IF NOT EXISTS
FOR (n:Product) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT production_order_id_unique IF NOT EXISTS
FOR (n:ProductionOrder) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT customer_order_id_unique IF NOT EXISTS
FOR (n:CustomerOrder) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT route_id_unique IF NOT EXISTS
FOR (n:TransportRoute) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT maintenance_id_unique IF NOT EXISTS
FOR (n:MaintenanceEvent) REQUIRE n.id IS UNIQUE;
