CREATE TABLE events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  occurred_at TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  source_system TEXT NOT NULL,
  accepted INTEGER NOT NULL,
  payload TEXT NOT NULL,
  trace_id TEXT NOT NULL
);

CREATE TABLE entity_state (
  entity_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  source_sequence INTEGER NOT NULL,
  occurred_at TEXT NOT NULL,
  quantity INTEGER,
  reason TEXT NOT NULL
);

CREATE TABLE inventory_lots (
  lot_id TEXT PRIMARY KEY,
  material_id TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  location TEXT NOT NULL
);

CREATE TABLE finished_goods (
  product_id TEXT PRIMARY KEY,
  quantity INTEGER NOT NULL
);

CREATE TABLE plans (
  plan_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  revision INTEGER NOT NULL,
  requester_id TEXT NOT NULL,
  document TEXT NOT NULL,
  trace_id TEXT NOT NULL
);

CREATE TABLE approvals (
  approval_id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  action TEXT NOT NULL,
  acted_at TEXT NOT NULL
);

CREATE TABLE executions (
  plan_id TEXT PRIMARY KEY,
  effect TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE audit_log (
  audit_id TEXT PRIMARY KEY,
  acted_at TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  action TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE TABLE outbox (
  outbox_id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  payload TEXT NOT NULL,
  published INTEGER NOT NULL
);

CREATE TABLE meta (
  meta_id INTEGER PRIMARY KEY,
  revision INTEGER NOT NULL
);
