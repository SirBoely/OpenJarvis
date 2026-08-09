from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping


class Gate(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Decision:
    owner: str
    priority: int
    gate: Gate
    reasons: tuple[str, ...]
    actions: tuple[str, ...]
    metrics: Mapping[str, float] = field(default_factory=dict)


@dataclass
class Goal:
    goal_id: str
    target: float
    actual: float = 0.0
    weight: float = 1.0

    @property
    def attainment(self) -> float:
        if self.target <= 0:
            return 0.0
        return max(0.0, min(self.actual / self.target, 2.0))


class GoalTrackingAgent:
    """Tracks weighted goal attainment and creates escalation signals."""

    def score(self, goals: Iterable[Goal]) -> Dict[str, Any]:
        goals = list(goals)
        if not goals:
            return {"weighted_attainment": 0.0, "at_risk": [], "status": "NO_GOALS"}
        weight = sum(max(g.weight, 0.0) for g in goals) or 1.0
        weighted = sum(g.attainment * max(g.weight, 0.0) for g in goals) / weight
        at_risk = [g.goal_id for g in goals if g.attainment < 0.8]
        return {
            "weighted_attainment": round(weighted, 4),
            "at_risk": at_risk,
            "status": "ON_TRACK" if not at_risk else "AT_RISK",
        }


class AnalyticsAgent:
    """Computes compact business-health metrics without external dependencies."""

    def analyze(self, data: Mapping[str, float]) -> Dict[str, float]:
        revenue = float(data.get("revenue", 0.0))
        cost = float(data.get("cost", 0.0))
        orders = float(data.get("orders", 0.0))
        sessions = float(data.get("sessions", 0.0))
        returns = float(data.get("returns", 0.0))
        gross_profit = revenue - cost
        return {
            "gross_profit": round(gross_profit, 2),
            "margin_pct": round((gross_profit / revenue * 100.0) if revenue else 0.0, 2),
            "aov": round((revenue / orders) if orders else 0.0, 2),
            "conversion_pct": round((orders / sessions * 100.0) if sessions else 0.0, 2),
            "return_rate_pct": round((returns / orders * 100.0) if orders else 0.0, 2),
        }


class OperationsAgent:
    """Converts operational state into deterministic action queues."""

    def triage(self, state: Mapping[str, Any]) -> List[str]:
        actions: List[str] = []
        if state.get("payment_gate") != "PASS":
            actions.append("repair_payment_gate")
        if state.get("supplier_gate") != "PASS":
            actions.append("validate_supplier_and_backup")
        if state.get("fulfilment_gate") != "PASS":
            actions.append("repair_fulfilment_routing")
        if state.get("legal_gate") != "PASS":
            actions.append("hold_launch_for_compliance_review")
        if not actions:
            actions.append("run_sales_canary")
        return actions


class ResourceManagementSystem:
    """Allocates capital and workload while preserving a configurable reserve."""

    def allocate(self, cash: float, requests: Mapping[str, float], reserve_ratio: float = 0.25) -> Dict[str, float]:
        reserve_ratio = max(0.0, min(reserve_ratio, 0.95))
        deployable = max(0.0, cash) * (1.0 - reserve_ratio)
        positive = {k: max(0.0, float(v)) for k, v in requests.items()}
        total = sum(positive.values())
        if total <= deployable:
            allocations = positive
        elif total == 0:
            allocations = {k: 0.0 for k in positive}
        else:
            allocations = {k: round(deployable * v / total, 2) for k, v in positive.items()}
        allocations["reserve"] = round(max(0.0, cash) - sum(v for k, v in allocations.items() if k != "reserve"), 2)
        return allocations

    def bookkeeping_tasks(self, events: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for event in events:
            if not event.get("receipt_id"):
                tasks.append({"type": "missing_receipt", "event_id": event.get("id")})
            if not event.get("category"):
                tasks.append({"type": "uncategorized_transaction", "event_id": event.get("id")})
            if event.get("reconcile") is False:
                tasks.append({"type": "reconciliation_required", "event_id": event.get("id")})
        return tasks


class FeedbackRetrainingLoop:
    """Produces safe retraining proposals; it never silently promotes a model."""

    def evaluate(self, baseline: Mapping[str, float], candidate: Mapping[str, float]) -> Dict[str, Any]:
        quality_delta = float(candidate.get("quality", 0.0)) - float(baseline.get("quality", 0.0))
        roi_delta = float(candidate.get("roi", 0.0)) - float(baseline.get("roi", 0.0))
        risk_delta = float(candidate.get("risk", 0.0)) - float(baseline.get("risk", 0.0))
        promote = quality_delta > 0 and roi_delta >= 0 and risk_delta <= 0
        return {
            "proposal": "PROMOTE" if promote else "REJECT",
            "requires_human_approval": True,
            "quality_delta": round(quality_delta, 4),
            "roi_delta": round(roi_delta, 4),
            "risk_delta": round(risk_delta, 4),
        }


class BusinessIntelligenceCapitalLeader:
    name = "business_intelligence_capital_leader"

    def decide(self, metrics: Mapping[str, float]) -> Decision:
        margin = float(metrics.get("margin_pct", 0.0))
        cash_buffer = float(metrics.get("cash_buffer_months", 0.0))
        gate = Gate.PASS if margin >= 20 and cash_buffer >= 2 else Gate.REVIEW
        return Decision(
            owner=self.name,
            priority=90,
            gate=gate,
            reasons=(f"margin_pct={margin}", f"cash_buffer_months={cash_buffer}"),
            actions=("optimize_unit_economics", "allocate_capital_by_risk_adjusted_roi", "reconcile_finance_evidence"),
            metrics=dict(metrics),
        )


class GrowthEngineeringLeader:
    name = "data_science_devops_revops_rd_leader"

    def decide(self, metrics: Mapping[str, float]) -> Decision:
        data_quality = float(metrics.get("data_quality", 0.0))
        ci_pass = float(metrics.get("ci_pass_rate", 0.0))
        gate = Gate.PASS if data_quality >= 0.9 and ci_pass >= 0.95 else Gate.REVIEW
        return Decision(
            owner=self.name,
            priority=85,
            gate=gate,
            reasons=(f"data_quality={data_quality}", f"ci_pass_rate={ci_pass}"),
            actions=("run_experiment_backlog", "improve_data_contracts", "optimize_release_and_revenue_cycle"),
            metrics=dict(metrics),
        )


class TrustGovernanceOperationsLeader:
    name = "governance_legal_compliance_operations_leader"

    def decide(self, metrics: Mapping[str, float]) -> Decision:
        compliance = float(metrics.get("compliance_coverage", 0.0))
        critical_risks = int(metrics.get("critical_risks", 0.0))
        gate = Gate.PASS if compliance >= 0.95 and critical_risks == 0 else Gate.BLOCK
        return Decision(
            owner=self.name,
            priority=100,
            gate=gate,
            reasons=(f"compliance_coverage={compliance}", f"critical_risks={critical_risks}"),
            actions=("close_control_gaps", "refresh_evidence", "validate_operational_readiness"),
            metrics=dict(metrics),
        )


class ExecutiveTriage:
    """Top-three consensus layer with fail-closed governance semantics."""

    def __init__(self) -> None:
        self.leaders = (
            BusinessIntelligenceCapitalLeader(),
            GrowthEngineeringLeader(),
            TrustGovernanceOperationsLeader(),
        )

    def run(self, context: Mapping[str, Mapping[str, float]]) -> Dict[str, Any]:
        decisions = [
            self.leaders[0].decide(context.get("capital", {})),
            self.leaders[1].decide(context.get("engineering", {})),
            self.leaders[2].decide(context.get("trust", {})),
        ]
        if any(d.gate == Gate.BLOCK for d in decisions):
            overall = Gate.BLOCK
        elif any(d.gate == Gate.REVIEW for d in decisions):
            overall = Gate.REVIEW
        else:
            overall = Gate.PASS
        actions = sorted({a for d in decisions for a in d.actions})
        return {
            "overall_gate": overall.value,
            "leaders": [d.owner for d in decisions],
            "decisions": decisions,
            "actions": actions,
            "autonomous_execution_allowed": overall == Gate.PASS,
        }
