from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence


class CatalogSyncEngine:
    """Diffs catalog state without mutating Shopify directly."""

    IMMUTABLE_KEYS = {"id", "created_at"}

    def diff(self, source: Iterable[Mapping[str, Any]], target: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        src = {str(x.get("sku")): dict(x) for x in source if x.get("sku")}
        dst = {str(x.get("sku")): dict(x) for x in target if x.get("sku")}
        creates = [src[k] for k in sorted(src.keys() - dst.keys())]
        archives = [dst[k] for k in sorted(dst.keys() - src.keys())]
        updates: List[Dict[str, Any]] = []
        for sku in sorted(src.keys() & dst.keys()):
            changes = {}
            for key, value in src[sku].items():
                if key in self.IMMUTABLE_KEYS or key == "sku":
                    continue
                if dst[sku].get(key) != value:
                    changes[key] = {"from": dst[sku].get(key), "to": value}
            if changes:
                updates.append({"sku": sku, "changes": changes})
        return {
            "creates": creates,
            "updates": updates,
            "archives": archives,
            "external_write_allowed": False,
            "requires_approval": bool(creates or updates or archives),
        }


class OrderEventIngestionEngine:
    """Normalizes commerce events and deduplicates by event id."""

    ALLOWED_TYPES = {
        "order_created", "order_paid", "order_cancelled", "fulfillment_created",
        "fulfillment_delivered", "refund_created", "return_requested", "chargeback_opened",
    }

    def ingest(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        seen: set[str] = set()
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        for raw in events:
            event_id = str(raw.get("event_id") or raw.get("id") or "")
            event_type = str(raw.get("type") or "")
            if not event_id or event_id in seen:
                rejected.append({"event_id": event_id or None, "reason": "missing_or_duplicate_event_id"})
                continue
            seen.add(event_id)
            if event_type not in self.ALLOWED_TYPES:
                rejected.append({"event_id": event_id, "reason": "unsupported_event_type"})
                continue
            accepted.append({
                "event_id": event_id,
                "type": event_type,
                "order_id": str(raw.get("order_id") or ""),
                "occurred_at": raw.get("occurred_at"),
                "amount": float(raw.get("amount", 0.0) or 0.0),
                "currency": str(raw.get("currency") or "EUR"),
                "correlation_id": raw.get("correlation_id") or event_id,
                "payload": dict(raw.get("payload") or {}),
            })
        return {"accepted": accepted, "rejected": rejected}


class FulfillmentStateMachine:
    """Deterministic fulfillment lifecycle with explicit illegal-transition blocking."""

    TRANSITIONS = {
        "PENDING_PAYMENT": {"PAID", "CANCELLED"},
        "PAID": {"ALLOCATED", "CANCELLED", "REFUND_PENDING"},
        "ALLOCATED": {"FULFILLING", "HOLD"},
        "FULFILLING": {"SHIPPED", "HOLD"},
        "SHIPPED": {"DELIVERED", "LOST", "RETURN_REQUESTED"},
        "DELIVERED": {"RETURN_REQUESTED", "CLOSED"},
        "RETURN_REQUESTED": {"RETURN_IN_TRANSIT", "RETURN_REJECTED"},
        "RETURN_IN_TRANSIT": {"RETURN_RECEIVED", "LOST"},
        "RETURN_RECEIVED": {"REFUND_PENDING", "CLOSED"},
        "REFUND_PENDING": {"REFUNDED", "HOLD"},
        "REFUNDED": {"CLOSED"},
        "HOLD": {"ALLOCATED", "FULFILLING", "CANCELLED", "REFUND_PENDING"},
    }

    def transition(self, current: str, requested: str) -> Dict[str, Any]:
        current = str(current)
        requested = str(requested)
        allowed = requested in self.TRANSITIONS.get(current, set())
        return {
            "from": current,
            "to": requested if allowed else current,
            "requested": requested,
            "gate": "PASS" if allowed else "BLOCK",
            "reason": "transition_allowed" if allowed else "illegal_state_transition",
        }


class CustomerServiceTriageAgent:
    """Routes service cases by risk and urgency without making legal/payment commitments."""

    def triage(self, tickets: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for t in tickets:
            kind = str(t.get("kind") or "general")
            age_h = float(t.get("age_hours", 0.0) or 0.0)
            value = float(t.get("order_value", 0.0) or 0.0)
            if kind in {"chargeback", "privacy_request", "legal_complaint", "fraud"}:
                priority, queue, approval = 100, "specialist_review", True
            elif kind in {"refund", "missing_delivery", "damaged_item"}:
                priority, queue, approval = 80, "resolution_queue", True
            elif kind in {"size_exchange", "return_status"}:
                priority, queue, approval = 60, "returns_queue", False
            else:
                priority, queue, approval = 40, "customer_care", False
            if age_h >= 24:
                priority += 10
            if value >= 250:
                priority += 5
            rows.append({
                "ticket_id": t.get("id"), "kind": kind, "priority": min(priority, 100),
                "queue": queue, "requires_human_approval": approval,
            })
        return sorted(rows, key=lambda x: (-x["priority"], str(x.get("ticket_id"))))


class ReturnsRefundsIntelligence:
    """Analyzes return causes and creates refund recommendations, never direct payment writes."""

    def analyze(self, returns: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        rows = list(returns)
        reasons: Dict[str, int] = {}
        sku_counts: Dict[str, int] = {}
        total_value = 0.0
        for row in rows:
            reason = str(row.get("reason") or "unknown")
            sku = str(row.get("sku") or "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
            sku_counts[sku] = sku_counts.get(sku, 0) + 1
            total_value += float(row.get("value", 0.0) or 0.0)
        count = len(rows)
        top_reason = max(reasons, key=reasons.get) if reasons else None
        return {
            "return_count": count,
            "return_value": round(total_value, 2),
            "reasons": dict(sorted(reasons.items())),
            "sku_counts": dict(sorted(sku_counts.items())),
            "top_reason": top_reason,
            "refund_external_write_allowed": False,
        }


class ProductLaunchCanaryEngine:
    """Evaluates small-launch canaries against explicit guardrails."""

    def evaluate(self, metrics: Mapping[str, float], thresholds: Mapping[str, float]) -> Dict[str, Any]:
        checks = {
            "conversion": float(metrics.get("conversion_pct", 0.0)) >= float(thresholds.get("min_conversion_pct", 0.0)),
            "margin": float(metrics.get("margin_pct", 0.0)) >= float(thresholds.get("min_margin_pct", 20.0)),
            "refunds": float(metrics.get("refund_rate_pct", 100.0)) <= float(thresholds.get("max_refund_rate_pct", 10.0)),
            "incidents": float(metrics.get("critical_incidents", 999.0)) <= float(thresholds.get("max_critical_incidents", 0.0)),
        }
        gate = "PASS" if all(checks.values()) else "BLOCK"
        return {"gate": gate, "checks": checks, "promotion_candidate": gate == "PASS", "requires_approval": True}


class MarginProtectionEngine:
    """Stops growth proposals that breach SKU or portfolio margin floors."""

    def protect(self, *, current_margin_pct: float, projected_margin_pct: float,
                floor_margin_pct: float = 20.0, max_drop_pct_points: float = 5.0) -> Dict[str, Any]:
        current = float(current_margin_pct)
        projected = float(projected_margin_pct)
        floor = float(floor_margin_pct)
        max_drop = max(float(max_drop_pct_points), 0.0)
        drop = current - projected
        blocked = projected < floor or drop > max_drop
        return {
            "gate": "BLOCK" if blocked else "PASS",
            "current_margin_pct": current,
            "projected_margin_pct": projected,
            "margin_floor_pct": floor,
            "drop_pct_points": round(drop, 2),
            "action": "hold_growth_change" if blocked else "eligible_for_canary",
        }


class MerchandisingOptimizer:
    """Ranks products using profit, conversion, inventory and return evidence."""

    def rank(self, products: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for p in products:
            margin = float(p.get("contribution_margin_pct", 0.0) or 0.0)
            conversion = float(p.get("conversion_pct", 0.0) or 0.0)
            stock = float(p.get("stock_readiness", 0.0) or 0.0)
            return_rate = float(p.get("return_rate_pct", 0.0) or 0.0)
            confidence = max(0.0, min(float(p.get("confidence", 1.0) or 1.0), 1.0))
            score = (margin * 0.40 + conversion * 5.0 * 0.30 + stock * 100.0 * 0.20 - return_rate * 0.10) * confidence
            scored.append({"sku": str(p.get("sku") or "unknown"), "score": round(score, 4)})
        return sorted(scored, key=lambda x: (-x["score"], x["sku"]))


class BundleUpsellOptimizer:
    """Scores bundle candidates by attach rate and incremental contribution."""

    def recommend(self, candidates: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for c in candidates:
            attach = max(0.0, float(c.get("attach_rate_pct", 0.0) or 0.0))
            contribution = float(c.get("incremental_contribution", 0.0) or 0.0)
            return_delta = float(c.get("return_rate_delta_pct", 0.0) or 0.0)
            confidence = max(0.0, min(float(c.get("confidence", 0.0) or 0.0), 1.0))
            score = (attach * 0.4 + contribution * 0.6 - max(return_delta, 0.0) * 2.0) * confidence
            gate = "PASS" if contribution > 0 and return_delta <= 2 else "REVIEW"
            rows.append({"bundle_id": c.get("id"), "score": round(score, 4), "gate": gate})
        return sorted(rows, key=lambda x: (-x["score"], str(x.get("bundle_id"))))


class ExecutiveTelemetryBuilder:
    """Builds PMO/Grafana-safe telemetry payloads with correlation and provenance."""

    def build(self, *, correlation_id: str, metrics: Mapping[str, Any], gates: Mapping[str, str],
              source: str = "exec-os-005") -> Dict[str, Any]:
        return {
            "correlation_id": correlation_id,
            "source": source,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "metrics": dict(metrics),
            "gates": dict(gates),
            "write_mode": "append_only",
            "grafana_labels": {"system": "btrades", "layer": "exec-os-005"},
            "requires_external_write_adapter": True,
        }


@dataclass(frozen=True)
class CommerceCommandDecision:
    gate: str
    actions: tuple[str, ...]
    human_approval_required: bool
    reason: str


class AutonomousCommerceCommandFabric:
    """Closed-loop commerce command layer with fail-closed controls."""

    def decide(self, *, evidence_gate: str, executive_gate: str, ci_gate: str,
               margin_gate: str, supplier_gate: str, legal_gate: str,
               canary_gate: str, regression: bool = False) -> CommerceCommandDecision:
        if regression:
            return CommerceCommandDecision("BLOCK", ("rollback_candidate", "freeze_external_writes"), True, "regression_detected")
        prerequisites = {
            "evidence": evidence_gate, "executive": executive_gate, "ci": ci_gate,
            "margin": margin_gate, "supplier": supplier_gate, "legal": legal_gate,
        }
        failed = [k for k, v in prerequisites.items() if v != "PASS"]
        if failed:
            return CommerceCommandDecision("BLOCK", tuple(f"repair_{x}_gate" for x in failed), True, "prerequisite_not_green")
        if canary_gate != "PASS":
            return CommerceCommandDecision("REVIEW", ("prepare_or_repeat_canary",), True, "canary_not_green")
        return CommerceCommandDecision(
            "PASS",
            ("refresh_analytics", "prepare_merchandising_changes", "prepare_bundle_candidates", "write_pmo_evidence"),
            True,
            "commerce_change_candidate_ready",
        )
