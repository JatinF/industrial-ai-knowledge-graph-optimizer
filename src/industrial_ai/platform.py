"""Failure-to-plan workflow.

Observe the event, update the system of record and the graph projection,
build one snapshot, solve, and stop before any simulated write until an
operator who is not the requester approves.
"""

import json
from datetime import UTC
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from industrial_ai.catalog import EDGE_ATTR, build_catalog
from industrial_ai.domain.decisions import FlowError, decision_status_for
from industrial_ai.domain.entities import (
    FAILURE,
    IOT,
    LOT,
    MATERIAL,
    MES,
    ORDER,
    PRESS,
    PRODUCT_A,
    SUPPLIER,
)
from industrial_ai.domain.events import (
    MachineFailureDetected,
    ParsedEvent,
    SupplierDelayDetected,
    parse_event,
)
from industrial_ai.execution.approvals import Actor, require_role
from industrial_ai.execution.audit import records
from industrial_ai.execution.simulator import apply_simulated, produced_units
from industrial_ai.execution.validation import recheck
from industrial_ai.graph.impact_analysis import (
    affected_orders,
    material_shortage,
    supplier_impact,
    transport_disruption,
)
from industrial_ai.graph.projection import (
    alternate_available,
    build_snapshot,
    press_down,
)
from industrial_ai.graph.repository import OperationalGraph
from industrial_ai.graph.traversals import dependencies, production_dependencies
from industrial_ai.ingestion.entity_resolution import bind_alias, resolve
from industrial_ai.ml.anomaly_detection import advisory_anomaly
from industrial_ai.ml.forecasting import advisory_forecast
from industrial_ai.optimization.allocation_solver import solve_allocation
from industrial_ai.optimization.feasibility import constraint_violations
from industrial_ai.optimization.greedy import plan_greedy
from industrial_ai.optimization.model_builder import AllocationSnapshot
from industrial_ai.optimization.scheduling_solver import solve_schedule
from industrial_ai.scenarios import ScenarioSpec, load_scenario
from industrial_ai.storage.outbox import unpublished
from industrial_ai.storage.relational import OperationalStore
from industrial_ai.streaming.consumer import take_new
from industrial_ai.streaming.handlers import classify, dead_letter_body
from industrial_ai.streaming.idempotency import already_stored
from industrial_ai.streaming.producer import InProcessBus
from industrial_ai.streaming.topics import REPLANNING, topic_for_event_type
from industrial_ai.telemetry.metrics import Metrics
from industrial_ai.telemetry.tracing import new_trace_id


class ProjectionError(RuntimeError):
    pass


def utc_now() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_stale(
    current_sequence: int,
    current_at: str,
    incoming_sequence: int | None,
    incoming_at: str,
) -> bool:
    if incoming_sequence is not None:
        return incoming_sequence <= current_sequence
    return bool(current_at) and incoming_at <= current_at


def _snapshot_document(snapshot: AllocationSnapshot) -> dict[str, Any]:
    return {
        "revision": snapshot.revision,
        "product_id": snapshot.product_id,
        "demand": snapshot.demand,
        "materials": snapshot.materials,
        "plants": [
            {
                "plant_id": plant.plant_id,
                "capacity": plant.capacity,
                "cost_per_unit": plant.cost_per_unit,
            }
            for plant in snapshot.plants
        ],
        "route_capacity": snapshot.route_capacity,
        "transport_cost_per_unit": snapshot.transport_cost_per_unit,
        "allow_late": snapshot.allow_late,
        "forbid_shortfall": snapshot.forbid_shortfall,
        "down_machines": list(snapshot.down_machines),
        "candidate_orders": list(snapshot.candidate_orders),
    }


def _explain(
    snapshot: AllocationSnapshot,
    *,
    status: str,
    objective: int,
    unmet: int,
    late: int,
    on_time: int,
    production_cost: int,
    transport_cost: int,
    baseline_objective: int,
    requirement_met: bool,
    violations: list[str],
) -> str:
    down = ", ".join(snapshot.down_machines) if snapshot.down_machines else "none"
    orders = ", ".join(snapshot.candidate_orders) if snapshot.candidate_orders else "none"
    requirement = (
        "Operational requirement is met: unmet demand is 0 and lateness is 0."
        if requirement_met
        else "Operational requirement is not met. Solver status is not customer fulfillment."
    )
    checked = (
        "Constraint violations: 0."
        if not violations
        else "Constraint violations: " + "; ".join(violations) + "."
    )
    return " ".join(
        [
            f"Snapshot revision {snapshot.revision} for {snapshot.product_id}.",
            f"Down machines: {down}.",
            f"Candidate orders: {orders}.",
            f"Solver status {status}. Objective {objective}.",
            f"Unmet {unmet}, late {late}, on time {on_time}.",
            f"Production cost {production_cost}, transport cost {transport_cost}.",
            f"Name-order baseline objective {baseline_objective}.",
            requirement,
            checked,
            "No operational write happens before an operator approval.",
        ]
    )


class Platform:
    def __init__(
        self,
        store: OperationalStore | None = None,
        clock: Any = None,
    ) -> None:
        self.store = store or OperationalStore()
        self.clock = clock or utc_now
        self.bus = InProcessBus()
        self.metrics = Metrics()
        self.controller_calls = 0
        self.fail_next_projection = False
        self.graph = OperationalGraph()
        self.spec: ScenarioSpec | None = None
        self.allow_late = True
        self.forbid_shortfall = False
        self.scenario_id = ""
        self._plan_seq = 0
        self.last_trace = ""
        self._audit_seq = 0
        self.reset("normal_operations")

    def now(self) -> str:
        value = self.clock()
        if not isinstance(value, str):
            raise FlowError("clock", "clock must return a string", 500)
        return value

    def reset(self, scenario_id: str) -> dict[str, Any]:
        spec = load_scenario(scenario_id)
        self.spec = spec
        self.scenario_id = spec.scenario_id
        self.allow_late = spec.allow_late
        self.forbid_shortfall = spec.forbid_shortfall
        self.graph = build_catalog()
        bind_alias(self.graph, source_system=MES, source_id=PRESS, canonical_id=PRESS)
        bind_alias(self.graph, source_system=IOT, source_id="SYN-SENSOR-220", canonical_id=PRESS)
        self.graph.update(LOT, quantity=spec.on_hand)
        self.graph.update(ORDER, quantity=spec.base_demand)
        for edge in self.graph.outgoing(SUPPLIER, "SUPPLIES"):
            if edge.dst == MATERIAL:
                edge.props["inbound_quantity"] = spec.inbound
        self.store.clear(
            lot_id=LOT, material_id=MATERIAL, lot_qty=spec.on_hand, location="WH-NORTH"
        )
        self.bus.messages.clear()
        self.bus.cursor = 0
        self._plan_seq = 0
        self.last_trace = ""
        return {
            "scenario_id": spec.scenario_id,
            "title": spec.title,
            "revision": self.store.revision(),
            "on_hand": spec.on_hand,
            "inbound": spec.inbound,
            "base_demand": spec.base_demand,
        }

    def reconcile(self) -> dict[str, int]:
        updated = 0
        for machine in self.graph.nodes("Machine"):
            row = self.store.get_entity(machine.id)
            if row is None:
                continue
            self.graph.update(
                machine.id,
                state=row["status"],
                source_sequence=row["source_sequence"],
                occurred_at=row["occurred_at"],
            )
            updated += 1
        for supplier in self.graph.nodes("Supplier"):
            row = self.store.get_entity(supplier.id)
            if row is None:
                continue
            self.graph.update(
                supplier.id,
                status=row["status"],
                source_sequence=row["source_sequence"],
                occurred_at=row["occurred_at"],
            )
            updated += 1
        for order in self.graph.nodes("CustomerOrder"):
            row = self.store.get_entity(order.id)
            if row is None or row["quantity"] is None:
                continue
            self.graph.update(
                order.id,
                quantity=int(row["quantity"]),
                source_sequence=row["source_sequence"],
                occurred_at=row["occurred_at"],
            )
            updated += 1
        if self.graph.has(LOT):
            self.graph.update(LOT, quantity=self.store.lot_quantity(LOT))
        return {"updated": updated, "revision": self.store.revision()}

    def _factory_of(self, machine_id: str) -> str | None:
        links = self.graph.incoming(machine_id, "HAS_MACHINE")
        if not links:
            return None
        plants = self.graph.incoming(links[0].src, "HAS_LINE")
        if not plants:
            return None
        return plants[0].src

    def _clock_for(self, entity_id: str) -> tuple[int, str]:
        row = self.store.get_entity(entity_id)
        if row is None:
            return -1, ""
        return int(row["source_sequence"]), str(row["occurred_at"])

    def _audit_id(self, name: str) -> str:
        self._audit_seq += 1
        return f"audit-{name}-{self._audit_seq}"

    def _reject(
        self,
        payload: dict[str, Any],
        *,
        trace_id: str,
        reason: str,
        event_type: str,
        occurred_at: str,
        source_system: str,
        schema_version: int,
    ) -> dict[str, Any]:
        event_id = payload.get("event_id")
        if isinstance(event_id, str) and event_id:
            if already_stored(self.store, event_id):
                self.metrics.inc("industrial_events_duplicate_total")
                stored = self.store.get_event(event_id)
                accepted = bool(stored and stored["accepted"])
                return {
                    "accepted": accepted,
                    "duplicate": True,
                    "state_changed": False,
                    "error": reason,
                    "revision": self.store.revision(),
                    "trace_id": str(stored["trace_id"]) if stored else trace_id,
                }
            self.store.reject_event(
                event_id=event_id,
                event_type=event_type,
                schema_version=schema_version,
                occurred_at=occurred_at,
                ingested_at=self.now(),
                source_system=source_system,
                payload=payload,
                trace_id=trace_id,
                audit_id=self._audit_id("reject"),
                reason=reason,
            )
        try:
            self.bus.publish(topic_for_event_type("dead"), dead_letter_body(reason, payload))
        except RuntimeError:
            pass
        self.metrics.inc("industrial_events_rejected_total")
        return {
            "accepted": False,
            "duplicate": False,
            "state_changed": False,
            "error": reason,
            "revision": self.store.revision(),
            "trace_id": trace_id,
        }

    def ingest(
        self, payload: object, *, actor_id: str, trace_id: str | None = None
    ) -> dict[str, Any]:
        trace = trace_id or new_trace_id()
        self.last_trace = trace
        if not isinstance(payload, dict):
            return self._reject(
                {},
                trace_id=trace,
                reason="schema_rejected",
                event_type="unknown",
                occurred_at="",
                source_system="unknown",
                schema_version=0,
            )
        try:
            event = parse_event(payload)
        except (ValueError, ValidationError):
            version = payload.get("schema_version")
            return self._reject(
                payload,
                trace_id=trace,
                reason="schema_rejected",
                event_type=str(payload.get("event_type") or "unknown"),
                occurred_at=str(payload.get("occurred_at") or ""),
                source_system=str(payload.get("source_system") or "unknown"),
                schema_version=version if type(version) is int else 0,
            )
        if already_stored(self.store, event.event_id):
            self.metrics.inc("industrial_events_duplicate_total")
            stored = self.store.get_event(event.event_id)
            return {
                "accepted": bool(stored and stored["accepted"]),
                "duplicate": True,
                "state_changed": False,
                "revision": self.store.revision(),
                "trace_id": str(stored["trace_id"]) if stored else trace,
                "event_id": event.event_id,
            }
        bound = self._bind(event)
        if bound is None:
            return self._reject(
                payload,
                trace_id=trace,
                reason="unresolved_entity",
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                source_system=event.source_system,
                schema_version=event.schema_version,
            )
        entity_id, kind, status, quantity = bound
        current_sequence, current_at = self._clock_for(entity_id)
        if _is_stale(current_sequence, current_at, event.source_sequence, event.occurred_at):
            return self._reject(
                payload,
                trace_id=trace,
                reason="stale_event",
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                source_system=event.source_system,
                schema_version=event.schema_version,
            )
        stored_sequence = (
            event.source_sequence if event.source_sequence is not None else max(current_sequence, 0)
        )
        revision = self.store.commit_event(
            event_id=event.event_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            occurred_at=event.occurred_at,
            ingested_at=self.now(),
            source_system=event.source_system,
            accepted=True,
            payload=payload,
            trace_id=trace,
            entity_id=entity_id,
            entity_kind=kind,
            entity_status=status,
            source_sequence=stored_sequence,
            quantity=quantity,
            reason=event.reason,
            outbox_id=f"out-{event.event_id}",
            outbox_topic=REPLANNING,
            bump=True,
            audit_id=self._audit_id("event"),
            actor_id=actor_id,
            audit_action="event_accepted",
        )
        reconciled = False
        try:
            self._project(event, entity_id, stored_sequence, quantity)
        except ProjectionError:
            self.reconcile()
            reconciled = True
        published = self._flush_outbox()
        self.metrics.inc("industrial_events_accepted_total")
        return {
            "accepted": True,
            "duplicate": False,
            "state_changed": True,
            "revision": revision,
            "trace_id": trace,
            "event_id": event.event_id,
            "entity_id": entity_id,
            "projection_reconciled": reconciled,
            "outbox_published": published,
            "occurred_at": event.occurred_at,
            "ingested_at": self._ingested_at(event.event_id),
        }

    def _ingested_at(self, event_id: str) -> str:
        stored = self.store.get_event(event_id)
        if stored is None:
            return ""
        return str(stored["ingested_at"])

    def _bind(self, event: ParsedEvent) -> tuple[str, str, str, int | None] | None:
        if isinstance(event, MachineFailureDetected):
            canonical = resolve(self.graph, event.source_system, event.machine_id)
            if canonical is None or not self.graph.has(canonical):
                return None
            if self.graph.get(canonical).label != "Machine":
                return None
            factory = self._factory_of(canonical)
            if factory != event.factory_id:
                return None
            return canonical, "machine", event.new_status, None
        if isinstance(event, SupplierDelayDetected):
            if not self.graph.has(event.supplier_id):
                return None
            if event.material_id != MATERIAL and not self.graph.has(event.material_id):
                return None
            return event.supplier_id, "supplier", event.new_status, None
        if not self.graph.has(event.order_id):
            return None
        order = self.graph.get(event.order_id)
        if order.label != "CustomerOrder" or order.props.get("product_id") != event.product_id:
            return None
        return event.order_id, "customer_order", "OPEN", event.quantity

    def _project(
        self,
        event: ParsedEvent,
        entity_id: str,
        stored_sequence: int,
        quantity: int | None,
    ) -> None:
        if self.fail_next_projection:
            self.fail_next_projection = False
            raise ProjectionError("projection failed")
        if isinstance(event, MachineFailureDetected):
            self.graph.update(
                entity_id,
                state=event.new_status,
                source_sequence=stored_sequence,
                occurred_at=event.occurred_at,
                reason=event.reason,
            )
            if event.new_status == "DOWN" and entity_id == PRESS and not self.graph.has(FAILURE):
                self.graph.add_node(
                    "MaintenanceEvent",
                    FAILURE,
                    machine_id=PRESS,
                    timestamp=event.occurred_at,
                    severity="high",
                    reason=event.reason,
                    source_system=event.source_system,
                )
                self.graph.add_edge(FAILURE, "AFFECTS", PRESS, **EDGE_ATTR)
            return
        if isinstance(event, SupplierDelayDetected):
            self.graph.update(
                entity_id,
                status=event.new_status,
                source_sequence=stored_sequence,
                occurred_at=event.occurred_at,
            )
            return
        self.graph.update(
            entity_id,
            quantity=quantity if quantity is not None else 0,
            source_sequence=stored_sequence,
            occurred_at=event.occurred_at,
        )

    def _flush_outbox(self) -> bool:
        try:
            for row in unpublished(self.store):
                self.bus.publish(str(row["topic"]), row["payload"])
                self.store.mark_outbox(str(row["outbox_id"]))
            return True
        except RuntimeError:
            return False

    def recover(self) -> dict[str, Any]:
        before = len(self.store.pending_outbox())
        published = self._flush_outbox()
        after = len(self.store.pending_outbox())
        return {"pending_before": before, "pending_after": after, "published": published}

    def submit_event(self, payload: object, actor: Actor) -> dict[str, Any]:
        require_role(actor, "planner", "operator")
        body = payload if isinstance(payload, dict) else {"invalid": True}
        event_type = body.get("event_type")
        try:
            self.bus.publish(topic_for_event_type(event_type), body)
        except RuntimeError as exc:
            raise FlowError("bus_unavailable", "event bus unavailable", 503) from exc
        return self._drain(actor)

    def _drain(self, actor: Actor) -> dict[str, Any]:
        last: dict[str, Any] = {"accepted": False, "error": "empty"}
        for topic, payload in take_new(self.bus):
            kind = classify(topic)
            if kind == "ingest":
                last = self.ingest(payload, actor_id=actor.user_id)
            elif kind == "notice":
                continue
            else:
                continue
        return last

    def solve(self, actor: Actor, trace_id: str | None = None) -> dict[str, Any]:
        require_role(actor, "planner", "operator")
        trace = trace_id or self.last_trace or new_trace_id()
        self.last_trace = trace
        snapshot = build_snapshot(
            self.graph,
            revision=self.store.revision(),
            allow_late=self.allow_late,
            forbid_shortfall=self.forbid_shortfall,
        )
        allocation = solve_allocation(snapshot, max_time_seconds=5.0)
        violations = constraint_violations(snapshot, allocation)
        decision = decision_status_for(allocation.status, violations)
        baseline = plan_greedy(snapshot)
        schedule = solve_schedule(
            maintenance=press_down(self.graph),
            alternate_available=alternate_available(self.graph),
        )
        self._plan_seq += 1
        plan_id = f"PLAN-{self._plan_seq:04d}"
        status = {
            "REQUIRES_APPROVAL": "proposed",
            "BLOCKED": "blocked",
            "INFEASIBLE": "infeasible",
            "SOLVER_STOPPED": "stopped",
        }[decision]
        document: dict[str, Any] = {
            "plan_id": plan_id,
            "status": status,
            "decision_status": decision,
            "snapshot_revision": snapshot.revision,
            "requester_id": actor.user_id,
            "created_at": self.now(),
            "trace_id": trace,
            "scenario_id": self.scenario_id,
            "solver_status": allocation.status,
            "objective": allocation.objective,
            "unmet_demand": allocation.unmet,
            "late": allocation.late,
            "on_time": allocation.on_time,
            "operational_requirement_met": allocation.operational_requirement_met,
            "production_cost": allocation.production_cost,
            "transport_cost": allocation.transport_cost,
            "baseline_objective": baseline.objective,
            "baseline_unmet": baseline.unmet,
            "baseline_production_cost": baseline.production_cost,
            "productions": allocation.as_dict()["productions"],
            "shipments": allocation.as_dict()["shipments"],
            "constraint_violations": violations,
            "candidate_orders": list(snapshot.candidate_orders),
            "down_machines": list(snapshot.down_machines),
            "schedule": schedule.as_dict(),
            "explanation": _explain(
                snapshot,
                status=allocation.status,
                objective=allocation.objective,
                unmet=allocation.unmet,
                late=allocation.late,
                on_time=allocation.on_time,
                production_cost=allocation.production_cost,
                transport_cost=allocation.transport_cost,
                baseline_objective=baseline.objective,
                requirement_met=allocation.operational_requirement_met,
                violations=violations,
            ),
            "signals": {
                "authoritative": False,
                "forecast_next": advisory_forecast(),
                "anomaly": advisory_anomaly(),
                "note": "Forecasts and anomaly flags do not decide feasibility.",
            },
            "snapshot": _snapshot_document(snapshot),
            "allocation": allocation.as_dict(),
            "simulated": True,
            "controller_calls": self.controller_calls,
        }
        self.store.save_plan(plan_id, document)
        self.metrics.inc("industrial_plans_solved_total")
        self.metrics.observe("industrial_solver_seconds", allocation.wall_seconds)
        return document

    def run_scenario(self, scenario_id: str, actor: Actor) -> dict[str, Any]:
        require_role(actor, "planner", "operator")
        self.reset(scenario_id)
        trace = new_trace_id()
        event_result = None
        if self.spec is not None and self.spec.event is not None:
            event_result = self.ingest(self.spec.event, actor_id=actor.user_id, trace_id=trace)
            if not event_result.get("accepted"):
                raise FlowError("scenario_event_rejected", "scenario event was not accepted", 409)
        plan = self.solve(actor, trace_id=trace)
        plan["event"] = event_result
        return plan

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self.store.get_plan(plan_id)
        if plan is None:
            raise FlowError("not_found", "unknown plan", 404)
        return plan

    def approve(self, plan_id: str, actor: Actor) -> dict[str, Any]:
        require_role(actor, "operator")
        plan = self.get_plan(plan_id)
        if plan["status"] == "APPROVED":
            replay = dict(plan)
            replay["idempotent"] = True
            return replay
        if plan["status"] != "proposed" or plan["decision_status"] != "REQUIRES_APPROVAL":
            raise FlowError("not_approvable", "plan cannot be approved", 409)
        if actor.user_id == plan["requester_id"]:
            raise FlowError("forbidden", "approver must be a different identity", 403)
        if recheck(plan):
            raise FlowError("blocked", "recheck found constraint violations", 409)
        updated = self.store.set_plan_status(
            plan_id,
            "APPROVED",
            actor_id=actor.user_id,
            action="plan_approved",
            acted_at=self.now(),
            approval_id=f"APR-{plan_id}-approve",
        )
        self.metrics.inc("industrial_plans_approved_total")
        updated["idempotent"] = False
        return updated

    def reject(self, plan_id: str, actor: Actor) -> dict[str, Any]:
        require_role(actor, "operator")
        plan = self.get_plan(plan_id)
        if plan["status"] == "REJECTED":
            replay = dict(plan)
            replay["idempotent"] = True
            return replay
        if plan["status"] != "proposed":
            raise FlowError("not_rejectable", "plan cannot be rejected", 409)
        updated = self.store.set_plan_status(
            plan_id,
            "REJECTED",
            actor_id=actor.user_id,
            action="plan_rejected",
            acted_at=self.now(),
            approval_id=f"APR-{plan_id}-reject",
        )
        self.metrics.inc("industrial_plans_rejected_total")
        updated["idempotent"] = False
        return updated

    def execute(self, plan_id: str, actor: Actor) -> dict[str, Any]:
        require_role(actor, "operator")
        if self.controller_calls != 0:
            raise FlowError("controller", "refusing live controller", 500)
        plan = self.get_plan(plan_id)
        existing = self.store.execution(plan_id)
        if existing is not None:
            existing["idempotent"] = True
            existing["controller_calls"] = self.controller_calls
            return existing
        if plan["status"] != "APPROVED":
            raise FlowError("not_approved", "only an approved plan can execute", 409)
        violations = recheck(plan)
        if violations:
            raise FlowError("blocked", "recheck found constraint violations", 409)
        units = produced_units(plan)
        effect = apply_simulated(
            self.store,
            plan_id=plan_id,
            expected_revision=int(plan["snapshot_revision"]),
            lot_id=LOT,
            product_id=PRODUCT_A,
            units=units,
            actor_id=actor.user_id,
            applied_at=self.now(),
            audit_id=self._audit_id("execute"),
        )
        self.graph.update(LOT, quantity=int(effect["lot_quantity"]))
        self.metrics.inc("industrial_plans_executed_total")
        effect["controller_calls"] = self.controller_calls
        return effect

    def assets(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for label in ("Factory", "ProductionLine", "Machine", "Supplier", "Warehouse", "Product"):
            for node in self.graph.nodes(label):
                status = node.props.get("status", node.props.get("state", ""))
                rows.append({"id": node.id, "label": label, "status": status})
        return rows

    def dependency_view(self, asset_id: str) -> dict[str, object]:
        if not self.graph.has(asset_id):
            raise FlowError("not_found", "unknown asset", 404)
        return {"asset_id": asset_id, "dependencies": dependencies(self.graph, asset_id)}

    def impact_view(self, asset_id: str) -> dict[str, object]:
        if not self.graph.has(asset_id):
            raise FlowError("not_found", "unknown asset", 404)
        label = self.graph.get(asset_id).label
        if label == "Machine":
            rows: object = affected_orders(self.graph, asset_id)
        elif label == "Supplier":
            rows = supplier_impact(self.graph, asset_id)
        elif label == "Material":
            rows = material_shortage(self.graph, asset_id)
        elif label == "TransportRoute":
            rows = transport_disruption(self.graph, asset_id)
        else:
            rows = production_dependencies(self.graph)
        return {"asset_id": asset_id, "label": label, "impact": rows}

    def audit(self) -> list[dict[str, Any]]:
        return records(self.store)


def plan_public(document: dict[str, Any]) -> dict[str, Any]:
    """Fields the API returns. The stored snapshot stays in the database."""

    keys = (
        "plan_id",
        "status",
        "decision_status",
        "snapshot_revision",
        "requester_id",
        "created_at",
        "trace_id",
        "scenario_id",
        "solver_status",
        "objective",
        "unmet_demand",
        "late",
        "on_time",
        "operational_requirement_met",
        "production_cost",
        "transport_cost",
        "baseline_objective",
        "baseline_unmet",
        "productions",
        "shipments",
        "constraint_violations",
        "candidate_orders",
        "down_machines",
        "schedule",
        "explanation",
        "signals",
        "simulated",
        "controller_calls",
        "event",
        "idempotent",
    )
    return {key: document[key] for key in keys if key in document}


def loads_payload(raw: str) -> dict[str, Any]:
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise FlowError("schema_rejected", "event payload must be an object", 422)
    return loaded


def new_id(prefix: str) -> str:
    return prefix + uuid4().hex[:12]
