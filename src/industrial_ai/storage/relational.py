"""Orders, inventory, decisions, and audit rows.

SQLite is the default. The same statements run on PostgreSQL when a local
server is contacted. The threading lock is in-process only. It is not a
distributed lock. Inventory and the execution row commit in one transaction,
so a failed insert does not leave a half-applied lot.
"""

import json
import threading
from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import StaticPool

from industrial_ai.domain.decisions import FlowError

metadata = MetaData()

events = Table(
    "events",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("event_type", String, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("occurred_at", String, nullable=False),
    Column("ingested_at", String, nullable=False),
    Column("source_system", String, nullable=False),
    Column("accepted", Integer, nullable=False),
    Column("payload", Text, nullable=False),
    Column("trace_id", String, nullable=False),
)

entity_state = Table(
    "entity_state",
    metadata,
    Column("entity_id", String, primary_key=True),
    Column("kind", String, nullable=False),
    Column("status", String, nullable=False),
    Column("source_sequence", Integer, nullable=False),
    Column("occurred_at", String, nullable=False),
    Column("quantity", Integer),
    Column("reason", String, nullable=False),
)

inventory_lots = Table(
    "inventory_lots",
    metadata,
    Column("lot_id", String, primary_key=True),
    Column("material_id", String, nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("location", String, nullable=False),
)

finished_goods = Table(
    "finished_goods",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("quantity", Integer, nullable=False),
)

plans = Table(
    "plans",
    metadata,
    Column("plan_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("requester_id", String, nullable=False),
    Column("document", Text, nullable=False),
    Column("trace_id", String, nullable=False),
)

approvals = Table(
    "approvals",
    metadata,
    Column("approval_id", String, primary_key=True),
    Column("plan_id", String, nullable=False),
    Column("actor_id", String, nullable=False),
    Column("action", String, nullable=False),
    Column("acted_at", String, nullable=False),
)

executions = Table(
    "executions",
    metadata,
    Column("plan_id", String, primary_key=True),
    Column("effect", Text, nullable=False),
    Column("applied_at", String, nullable=False),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("audit_id", String, primary_key=True),
    Column("acted_at", String, nullable=False),
    Column("actor_id", String, nullable=False),
    Column("action", String, nullable=False),
    Column("detail", Text, nullable=False),
)

outbox = Table(
    "outbox",
    metadata,
    Column("outbox_id", String, primary_key=True),
    Column("topic", String, nullable=False),
    Column("payload", Text, nullable=False),
    Column("published", Integer, nullable=False),
)

meta = Table(
    "meta",
    metadata,
    Column("meta_id", Integer, primary_key=True),
    Column("revision", Integer, nullable=False),
)


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, pool_pre_ping=True)


class OperationalStore:
    def __init__(self, url: str = "sqlite://") -> None:
        self.url = url
        self.kind = "sqlite" if url.startswith("sqlite") else "postgres"
        self.engine = make_engine(url)
        self._lock = threading.Lock()
        metadata.create_all(self.engine)
        with self.engine.begin() as conn:
            found = conn.execute(select(meta.c.revision).where(meta.c.meta_id == 1)).first()
            if found is None:
                conn.execute(insert(meta).values(meta_id=1, revision=1))

    def revision(self) -> int:
        with self.engine.connect() as conn:
            row = conn.execute(select(meta.c.revision).where(meta.c.meta_id == 1)).one()
        return int(row.revision)

    def clear(self, *, lot_id: str, material_id: str, lot_qty: int, location: str) -> None:
        with self._lock, self.engine.begin() as conn:
            for table in reversed(metadata.sorted_tables):
                conn.execute(delete(table))
            conn.execute(insert(meta).values(meta_id=1, revision=1))
            conn.execute(
                insert(inventory_lots).values(
                    lot_id=lot_id,
                    material_id=material_id,
                    quantity=lot_qty,
                    location=location,
                )
            )

    def lot_quantity(self, lot_id: str) -> int:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(inventory_lots.c.quantity).where(inventory_lots.c.lot_id == lot_id)
            ).one()
        return int(row.quantity)

    def finished_quantity(self, product_id: str) -> int:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(finished_goods.c.quantity).where(finished_goods.c.product_id == product_id)
            ).first()
        if row is None:
            return 0
        return int(row.quantity)

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(events).where(events.c.event_id == event_id)).first()
        if row is None:
            return None
        return dict(row._mapping)

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(entity_state).where(entity_state.c.entity_id == entity_id)
            ).first()
        if row is None:
            return None
        return dict(row._mapping)

    def commit_event(
        self,
        *,
        event_id: str,
        event_type: str,
        schema_version: int,
        occurred_at: str,
        ingested_at: str,
        source_system: str,
        accepted: bool,
        payload: dict[str, Any],
        trace_id: str,
        entity_id: str | None,
        entity_kind: str | None,
        entity_status: str | None,
        source_sequence: int | None,
        quantity: int | None,
        reason: str,
        outbox_id: str | None,
        outbox_topic: str | None,
        bump: bool,
        audit_id: str,
        actor_id: str,
        audit_action: str,
    ) -> int:
        with self._lock, self.engine.begin() as conn:
            conn.execute(
                insert(events).values(
                    event_id=event_id,
                    event_type=event_type,
                    schema_version=schema_version,
                    occurred_at=occurred_at,
                    ingested_at=ingested_at,
                    source_system=source_system,
                    accepted=1 if accepted else 0,
                    payload=json.dumps(payload),
                    trace_id=trace_id,
                )
            )
            if (
                accepted
                and entity_id is not None
                and entity_kind is not None
                and entity_status is not None
            ):
                existing = conn.execute(
                    select(entity_state.c.entity_id).where(entity_state.c.entity_id == entity_id)
                ).first()
                values = {
                    "kind": entity_kind,
                    "status": entity_status,
                    "source_sequence": source_sequence if source_sequence is not None else 0,
                    "occurred_at": occurred_at,
                    "quantity": quantity,
                    "reason": reason,
                }
                if existing is None:
                    conn.execute(insert(entity_state).values(entity_id=entity_id, **values))
                else:
                    conn.execute(
                        update(entity_state)
                        .where(entity_state.c.entity_id == entity_id)
                        .values(**values)
                    )
            if outbox_id is not None and outbox_topic is not None:
                conn.execute(
                    insert(outbox).values(
                        outbox_id=outbox_id,
                        topic=outbox_topic,
                        payload=json.dumps(payload),
                        published=0,
                    )
                )
            revision = self._revision_in(conn)
            if bump:
                revision += 1
                conn.execute(update(meta).where(meta.c.meta_id == 1).values(revision=revision))
            conn.execute(
                insert(audit_log).values(
                    audit_id=audit_id,
                    acted_at=ingested_at,
                    actor_id=actor_id,
                    action=audit_action,
                    detail=json.dumps({"event_id": event_id, "accepted": accepted}),
                )
            )
            return revision

    def _revision_in(self, conn: Connection) -> int:
        row = conn.execute(select(meta.c.revision).where(meta.c.meta_id == 1)).one()
        return int(row.revision)

    def reject_event(
        self,
        *,
        event_id: str,
        event_type: str,
        schema_version: int,
        occurred_at: str,
        ingested_at: str,
        source_system: str,
        payload: dict[str, Any],
        trace_id: str,
        audit_id: str,
        reason: str,
    ) -> None:
        with self._lock, self.engine.begin() as conn:
            conn.execute(
                insert(events).values(
                    event_id=event_id,
                    event_type=event_type,
                    schema_version=schema_version,
                    occurred_at=occurred_at,
                    ingested_at=ingested_at,
                    source_system=source_system,
                    accepted=0,
                    payload=json.dumps(payload),
                    trace_id=trace_id,
                )
            )
            conn.execute(
                insert(audit_log).values(
                    audit_id=audit_id,
                    acted_at=ingested_at,
                    actor_id="system",
                    action=reason,
                    detail=json.dumps({"event_id": event_id}),
                )
            )

    def save_plan(self, plan_id: str, document: dict[str, Any]) -> None:
        with self._lock, self.engine.begin() as conn:
            conn.execute(
                insert(plans).values(
                    plan_id=plan_id,
                    status=str(document["status"]),
                    revision=int(document["snapshot_revision"]),
                    requester_id=str(document["requester_id"]),
                    document=json.dumps(document),
                    trace_id=str(document["trace_id"]),
                )
            )
            conn.execute(
                insert(audit_log).values(
                    audit_id=f"audit-{plan_id}-save",
                    acted_at=str(document["created_at"]),
                    actor_id=str(document["requester_id"]),
                    action="plan_proposed",
                    detail=json.dumps({"plan_id": plan_id}),
                )
            )

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(plans.c.document).where(plans.c.plan_id == plan_id)).first()
        if row is None:
            return None
        loaded = json.loads(str(row.document))
        if not isinstance(loaded, dict):
            raise FlowError("plan_corrupt", "stored plan is not an object", 500)
        return loaded

    def set_plan_status(
        self,
        plan_id: str,
        status: str,
        *,
        actor_id: str,
        action: str,
        acted_at: str,
        approval_id: str,
    ) -> dict[str, Any]:
        with self._lock, self.engine.begin() as conn:
            row = conn.execute(select(plans.c.document).where(plans.c.plan_id == plan_id)).one()
            document = json.loads(str(row.document))
            if not isinstance(document, dict):
                raise FlowError("plan_corrupt", "stored plan is not an object", 500)
            document["status"] = status
            if status in {"APPROVED", "REJECTED", "EXECUTED"}:
                document["decision_status"] = status
            else:
                document["decision_status"] = document["decision_status"]
            conn.execute(
                update(plans)
                .where(plans.c.plan_id == plan_id)
                .values(status=status, document=json.dumps(document))
            )
            conn.execute(
                insert(approvals).values(
                    approval_id=approval_id,
                    plan_id=plan_id,
                    actor_id=actor_id,
                    action=action,
                    acted_at=acted_at,
                )
            )
            conn.execute(
                insert(audit_log).values(
                    audit_id=f"audit-{approval_id}",
                    acted_at=acted_at,
                    actor_id=actor_id,
                    action=action,
                    detail=json.dumps({"plan_id": plan_id, "status": status}),
                )
            )
            return document

    def execution(self, plan_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(executions).where(executions.c.plan_id == plan_id)).first()
        if row is None:
            return None
        effect = json.loads(str(row.effect))
        if not isinstance(effect, dict):
            raise FlowError("execution_corrupt", "stored execution is not an object", 500)
        return effect

    def apply_execution(
        self,
        *,
        plan_id: str,
        expected_revision: int,
        lot_id: str,
        consume: int,
        product_id: str,
        produce: int,
        actor_id: str,
        applied_at: str,
        audit_id: str,
    ) -> dict[str, Any]:
        with self._lock, self.engine.begin() as conn:
            existing = conn.execute(
                select(executions.c.effect).where(executions.c.plan_id == plan_id)
            ).first()
            if existing is not None:
                effect = json.loads(str(existing.effect))
                if not isinstance(effect, dict):
                    raise FlowError("execution_corrupt", "stored execution is not an object", 500)
                effect["idempotent"] = True
                return effect
            revision = self._revision_in(conn)
            if revision != expected_revision:
                raise FlowError("stale_snapshot", "operational revision changed", 409)
            lot = conn.execute(
                select(inventory_lots.c.quantity).where(inventory_lots.c.lot_id == lot_id)
            ).one()
            available = int(lot.quantity)
            if consume > available:
                raise FlowError("inventory_short", "lot quantity is below the plan", 409)
            remaining = available - consume
            conn.execute(
                update(inventory_lots)
                .where(inventory_lots.c.lot_id == lot_id)
                .values(quantity=remaining)
            )
            finished = conn.execute(
                select(finished_goods.c.quantity).where(finished_goods.c.product_id == product_id)
            ).first()
            if finished is None:
                made = produce
                conn.execute(insert(finished_goods).values(product_id=product_id, quantity=made))
            else:
                made = int(finished.quantity) + produce
                conn.execute(
                    update(finished_goods)
                    .where(finished_goods.c.product_id == product_id)
                    .values(quantity=made)
                )
            effect = {
                "plan_id": plan_id,
                "lot_id": lot_id,
                "lot_quantity": remaining,
                "product_id": product_id,
                "finished_quantity": made,
                "consumed": consume,
                "idempotent": False,
                "simulated": True,
                "controller_calls": 0,
            }
            conn.execute(
                insert(executions).values(
                    plan_id=plan_id,
                    effect=json.dumps(effect),
                    applied_at=applied_at,
                )
            )
            conn.execute(update(meta).where(meta.c.meta_id == 1).values(revision=revision + 1))
            plan_row = conn.execute(
                select(plans.c.document).where(plans.c.plan_id == plan_id)
            ).one()
            document = json.loads(str(plan_row.document))
            if isinstance(document, dict):
                document["status"] = "EXECUTED"
                document["decision_status"] = "EXECUTED"
                conn.execute(
                    update(plans)
                    .where(plans.c.plan_id == plan_id)
                    .values(status="EXECUTED", document=json.dumps(document))
                )
            conn.execute(
                insert(audit_log).values(
                    audit_id=audit_id,
                    acted_at=applied_at,
                    actor_id=actor_id,
                    action="plan_executed",
                    detail=json.dumps(effect),
                )
            )
            return effect

    def pending_outbox(self) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(select(outbox).where(outbox.c.published == 0)).all()
        return [dict(row._mapping) for row in rows]

    def mark_outbox(self, outbox_id: str) -> None:
        with self._lock, self.engine.begin() as conn:
            conn.execute(update(outbox).where(outbox.c.outbox_id == outbox_id).values(published=1))

    def list_audit(self) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(audit_log).order_by(audit_log.c.acted_at, audit_log.c.audit_id)
            ).all()
        return [dict(row._mapping) for row in rows]

    def force_lot(self, lot_id: str, quantity: int) -> None:
        """Test hook. Does not bump the revision."""

        with self._lock, self.engine.begin() as conn:
            conn.execute(
                update(inventory_lots)
                .where(inventory_lots.c.lot_id == lot_id)
                .values(quantity=quantity)
            )
