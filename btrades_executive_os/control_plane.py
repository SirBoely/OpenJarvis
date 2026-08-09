from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .core import AnalyticsAgent, ExecutiveTriage, Goal, GoalTrackingAgent, OperationsAgent, ResourceManagementSystem
from .evidence import ContextPackBuilder, EvidenceRegistry


@dataclass(frozen=True)
class PromotionDecision:
    gate: str
    reason: str
    requires_human_approval: bool = True
    rollback_required: bool = False


class PromotionController:
    """Controls production promotion and rollback with fail-closed semantics."""

    def evaluate(self, *, preflight_gate: str, ci_gate: str, executive_gate: str, canary_ok: bool, regression: bool) -> PromotionDecision:
        if regression:
            return PromotionDecision("BLOCK", "regression_detected", True, True)
        if preflight_gate != "PASS":
            return PromotionDecision("BLOCK", "preflight_not_green")
        if ci_gate != "PASS":
            return PromotionDecision("BLOCK", "ci_not_green")
        if executive_gate != "PASS":
            return PromotionDecision("BLOCK", "executive_consensus_not_green")
        if not canary_ok:
            return PromotionDecision("REVIEW", "canary_not_confirmed")
        return PromotionDecision("PASS", "promotion_candidate_ready", True, False)


class ExecutiveControlPlane:
    """End-to-end executive loop: evidence -> triage -> goals/resources -> operations -> promotion."""

    REQUIRED_EVIDENCE = ("github", "supabase", "shopify", "pmo", "finance", "compliance")

    def __init__(self) -> None:
        self.context_builder = ContextPackBuilder()
        self.triage = ExecutiveTriage()
        self.analytics = AnalyticsAgent()
        self.goals = GoalTrackingAgent()
        self.operations = OperationsAgent()
        self.resources = ResourceManagementSystem()
        self.promotion = PromotionController()

    def run(self, registry: EvidenceRegistry, runtime: Mapping[str, Any]) -> Dict[str, Any]:
        evidence_gate = registry.readiness(self.REQUIRED_EVIDENCE)
        if evidence_gate["gate"] != "PASS":
            return {
                "overall_gate": "BLOCK",
                "stage": "evidence",
                "evidence": evidence_gate,
                "autonomous_execution_allowed": False,
            }

        context = self.context_builder.build(registry)
        executive = self.triage.run(context)

        commerce = context.get("commerce", {})
        analytics = self.analytics.analyze({
            "revenue": float(commerce.get("revenue", 0.0)),
            "cost": float(commerce.get("cost", 0.0)),
            "orders": float(commerce.get("orders", 0.0)),
            "sessions": float(commerce.get("sessions", 0.0)),
            "returns": float(commerce.get("returns", 0.0)),
        })

        goal_specs = runtime.get("goals", [])
        goals = [Goal(str(g["goal_id"]), float(g["target"]), float(g.get("actual", 0.0)), float(g.get("weight", 1.0))) for g in goal_specs]
        goal_score = self.goals.score(goals)

        allocations = self.resources.allocate(
            float(runtime.get("cash", 0.0)),
            runtime.get("resource_requests", {}),
            float(runtime.get("reserve_ratio", 0.25)),
        )
        bookkeeping = self.resources.bookkeeping_tasks(runtime.get("finance_events", []))
        ops_actions = self.operations.triage(runtime.get("operations", {}))

        promotion = self.promotion.evaluate(
            preflight_gate=evidence_gate["gate"],
            ci_gate=str(runtime.get("ci_gate", "BLOCK")),
            executive_gate=str(executive["overall_gate"]),
            canary_ok=bool(runtime.get("canary_ok", False)),
            regression=bool(runtime.get("regression", False)),
        )

        overall = promotion.gate
        return {
            "overall_gate": overall,
            "stage": "promotion" if overall != "BLOCK" else "control",
            "evidence": evidence_gate,
            "executive": executive,
            "analytics": analytics,
            "goals": goal_score,
            "resource_allocations": allocations,
            "bookkeeping_tasks": bookkeeping,
            "operations_actions": ops_actions,
            "promotion": promotion,
            "autonomous_execution_allowed": overall == "PASS" and not promotion.requires_human_approval,
            "human_approval_required": promotion.requires_human_approval,
        }
