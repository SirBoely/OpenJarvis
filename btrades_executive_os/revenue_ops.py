from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class AttributionResult:
    order_id: str
    revenue: float
    channel: str
    campaign: str | None
    source: str | None
    medium: str | None
    confidence: float


class RevenueAttributionEngine:
    """Deterministic order/revenue attribution with explicit confidence and no fabricated touchpoints."""

    CHANNEL_KEYS = ("channel", "utm_source", "referrer", "source")

    def attribute(self, orders: Iterable[Mapping[str, Any]]) -> List[AttributionResult]:
        results: List[AttributionResult] = []
        for order in orders:
            attrs = order.get("attribution", {}) or {}
            channel = str(attrs.get("channel") or attrs.get("utm_source") or order.get("channel") or "unknown")
            source = attrs.get("utm_source") or attrs.get("source")
            medium = attrs.get("utm_medium") or attrs.get("medium")
            campaign = attrs.get("utm_campaign") or attrs.get("campaign")
            explicit = sum(bool(attrs.get(k)) for k in ("channel", "utm_source", "utm_medium", "utm_campaign"))
            confidence = 1.0 if explicit >= 2 else (0.8 if explicit == 1 else 0.5)
            results.append(
                AttributionResult(
                    order_id=str(order.get("id", "unknown")),
                    revenue=float(order.get("net_revenue", order.get("revenue", 0.0)) or 0.0),
                    channel=channel,
                    campaign=str(campaign) if campaign is not None else None,
                    source=str(source) if source is not None else None,
                    medium=str(medium) if medium is not None else None,
                    confidence=confidence,
                )
            )
        return results

    def aggregate(self, rows: Sequence[AttributionResult]) -> Dict[str, Any]:
        channels: Dict[str, float] = {}
        unattributed = 0.0
        weighted_confidence = 0.0
        total_revenue = 0.0
        for row in rows:
            total_revenue += row.revenue
            weighted_confidence += row.revenue * row.confidence
            channels[row.channel] = channels.get(row.channel, 0.0) + row.revenue
            if row.channel == "unknown":
                unattributed += row.revenue
        return {
            "total_revenue": round(total_revenue, 2),
            "revenue_by_channel": {k: round(v, 2) for k, v in sorted(channels.items())},
            "unattributed_revenue": round(unattributed, 2),
            "weighted_confidence": round(weighted_confidence / total_revenue, 4) if total_revenue else 0.0,
        }


class UnitEconomicsEngine:
    """Computes CAC, ROAS and LTV from supplied evidence only."""

    def compute(self, data: Mapping[str, float]) -> Dict[str, float]:
        ad_spend = float(data.get("ad_spend", 0.0) or 0.0)
        new_customers = float(data.get("new_customers", 0.0) or 0.0)
        attributed_revenue = float(data.get("attributed_revenue", 0.0) or 0.0)
        aov = float(data.get("aov", 0.0) or 0.0)
        purchase_frequency = float(data.get("purchase_frequency", 0.0) or 0.0)
        gross_margin_pct = float(data.get("gross_margin_pct", 0.0) or 0.0)
        customer_lifetime_periods = float(data.get("customer_lifetime_periods", 0.0) or 0.0)
        cac = ad_spend / new_customers if new_customers > 0 else 0.0
        roas = attributed_revenue / ad_spend if ad_spend > 0 else 0.0
        ltv = aov * purchase_frequency * customer_lifetime_periods * max(gross_margin_pct, 0.0) / 100.0
        return {
            "cac": round(cac, 2),
            "roas": round(roas, 4),
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv / cac, 4) if cac > 0 else 0.0,
        }


class SupplierSLAScorer:
    """Scores suppliers using quality, delivery, defects, disputes and backup readiness."""

    def score(self, supplier: Mapping[str, Any]) -> Dict[str, Any]:
        on_time = max(0.0, min(float(supplier.get("on_time_delivery_pct", 0.0)), 100.0))
        defect = max(0.0, min(float(supplier.get("defect_rate_pct", 100.0)), 100.0))
        dispute = max(0.0, min(float(supplier.get("dispute_rate_pct", 100.0)), 100.0))
        quality = max(0.0, min(float(supplier.get("quality_score", 0.0)), 100.0))
        response = max(0.0, min(float(supplier.get("response_score", 0.0)), 100.0))
        backup = 100.0 if supplier.get("backup_supplier_ready") else 0.0
        score = (
            on_time * 0.30
            + (100.0 - defect) * 0.25
            + quality * 0.20
            + (100.0 - dispute) * 0.10
            + response * 0.10
            + backup * 0.05
        )
        gate = "PASS" if score >= 85 else ("REVIEW" if score >= 70 else "BLOCK")
        return {"supplier_id": supplier.get("id"), "score": round(score, 2), "gate": gate}


class LedgerRouter:
    """Routes bookkeeping events into deterministic queues without creating accounting assertions."""

    RULES = {
        "sale": "revenue_pending_reconciliation",
        "refund": "refunds_pending_reconciliation",
        "supplier_invoice": "cost_of_goods_pending_reconciliation",
        "ad_spend": "marketing_expense_pending_reconciliation",
        "fee": "platform_fees_pending_reconciliation",
        "tax": "tax_review_required",
    }

    def route(self, events: Iterable[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        queues: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            event_type = str(event.get("type", "unknown"))
            queue = self.RULES.get(event_type, "manual_accounting_review")
            queues.setdefault(queue, []).append({
                "event_id": event.get("id"),
                "type": event_type,
                "amount": float(event.get("amount", 0.0) or 0.0),
                "currency": event.get("currency", "EUR"),
                "correlation_id": event.get("correlation_id"),
            })
        return queues


class KPIDriftDetector:
    """Flags material KPI drift against explicit baselines and thresholds."""

    def detect(self, current: Mapping[str, float], baseline: Mapping[str, float], thresholds_pct: Mapping[str, float] | None = None) -> List[Dict[str, Any]]:
        thresholds_pct = dict(thresholds_pct or {})
        anomalies: List[Dict[str, Any]] = []
        for key, current_value in current.items():
            if key not in baseline:
                continue
            base = float(baseline[key])
            cur = float(current_value)
            if base == 0:
                continue
            delta_pct = (cur - base) / abs(base) * 100.0
            threshold = float(thresholds_pct.get(key, 20.0))
            if abs(delta_pct) >= threshold:
                anomalies.append({
                    "metric": key,
                    "baseline": base,
                    "current": cur,
                    "delta_pct": round(delta_pct, 2),
                    "threshold_pct": threshold,
                    "direction": "up" if delta_pct > 0 else "down",
                })
        return anomalies


class IncidentRemediationEngine:
    """Maps anomalies and operational failures to bounded remediation tasks."""

    def plan(self, *, anomalies: Iterable[Mapping[str, Any]], supplier_gates: Iterable[Mapping[str, Any]], payment_gate: str, fulfilment_gate: str) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        if payment_gate != "PASS":
            tasks.append({"priority": 100, "action": "hold_sales_canary_and_repair_payment_gate", "approval_required": True})
        if fulfilment_gate != "PASS":
            tasks.append({"priority": 95, "action": "pause_auto_fulfilment_and_repair_routing", "approval_required": True})
        for supplier in supplier_gates:
            if supplier.get("gate") == "BLOCK":
                tasks.append({"priority": 90, "action": "route_to_backup_supplier_or_hold_sku", "supplier_id": supplier.get("supplier_id"), "approval_required": True})
            elif supplier.get("gate") == "REVIEW":
                tasks.append({"priority": 70, "action": "supplier_sla_review", "supplier_id": supplier.get("supplier_id"), "approval_required": False})
        for anomaly in anomalies:
            tasks.append({"priority": 60, "action": "investigate_kpi_drift", "metric": anomaly.get("metric"), "approval_required": False})
        return sorted(tasks, key=lambda x: int(x.get("priority", 0)), reverse=True)


class ProjectResourceOptimizer:
    """Ranks project requests using value, urgency, confidence and execution readiness."""

    def rank(self, projects: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []
        for project in projects:
            roi = float(project.get("expected_roi", 0.0) or 0.0)
            urgency = max(0.0, min(float(project.get("urgency", 0.0) or 0.0), 1.0))
            confidence = max(0.0, min(float(project.get("confidence", 0.0) or 0.0), 1.0))
            readiness = max(0.0, min(float(project.get("readiness", 0.0) or 0.0), 1.0))
            risk = max(0.0, min(float(project.get("risk", 0.0) or 0.0), 1.0))
            score = roi * 0.45 + urgency * 25 + confidence * 15 + readiness * 15 - risk * 20
            ranked.append({"project_id": project.get("id"), "score": round(score, 3)})
        return sorted(ranked, key=lambda x: x["score"], reverse=True)


class PMOEvidenceWriter:
    """Creates immutable PMO evidence payloads for downstream write adapters."""

    def build_record(self, *, correlation_id: str, domain: str, gate: str, metrics: Mapping[str, Any], actions: Sequence[Mapping[str, Any]] | Sequence[str]) -> Dict[str, Any]:
        return {
            "correlation_id": correlation_id,
            "domain": domain,
            "gate": gate,
            "metrics": dict(metrics),
            "actions": list(actions),
            "write_mode": "append_only",
            "requires_external_write_adapter": True,
        }
