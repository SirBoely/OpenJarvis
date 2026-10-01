from __future__ import annotations

from dataclasses import dataclass
from math import exp
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence


class SKUProfitabilityEngine:
    """Computes contribution economics per SKU from supplied evidence only."""

    def analyze(self, skus: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for sku in skus:
            units = float(sku.get("units_sold", 0.0) or 0.0)
            revenue = float(sku.get("revenue", 0.0) or 0.0)
            cogs = float(sku.get("cogs", 0.0) or 0.0)
            fulfilment = float(sku.get("fulfilment_cost", 0.0) or 0.0)
            fees = float(sku.get("fees", 0.0) or 0.0)
            refunds = float(sku.get("refunds", 0.0) or 0.0)
            ad_cost = float(sku.get("attributed_ad_cost", 0.0) or 0.0)
            contribution = revenue - cogs - fulfilment - fees - refunds - ad_cost
            margin_pct = contribution / revenue * 100.0 if revenue > 0 else 0.0
            rows.append({
                "sku": str(sku.get("sku", "unknown")),
                "units_sold": units,
                "revenue": round(revenue, 2),
                "contribution_profit": round(contribution, 2),
                "contribution_margin_pct": round(margin_pct, 2),
                "profit_per_unit": round(contribution / units, 2) if units > 0 else 0.0,
                "gate": "PASS" if contribution > 0 and margin_pct >= 20 else ("REVIEW" if contribution >= 0 else "BLOCK"),
            })
        return rows


class DynamicPricingEngine:
    """Generates bounded price recommendations; it never writes prices externally."""

    def recommend(self, *, current_price: float, unit_cost: float, demand_index: float = 1.0,
                  inventory_pressure: float = 0.0, min_margin_pct: float = 25.0,
                  max_change_pct: float = 10.0) -> Dict[str, Any]:
        current_price = max(float(current_price), 0.01)
        unit_cost = max(float(unit_cost), 0.0)
        demand_index = max(0.25, min(float(demand_index), 2.0))
        inventory_pressure = max(-1.0, min(float(inventory_pressure), 1.0))
        max_change_pct = max(0.0, min(float(max_change_pct), 25.0))
        floor = unit_cost / max(1.0 - min_margin_pct / 100.0, 0.01)
        signal = (demand_index - 1.0) * 0.5 - inventory_pressure * 0.25
        raw = current_price * (1.0 + signal)
        lower = current_price * (1.0 - max_change_pct / 100.0)
        upper = current_price * (1.0 + max_change_pct / 100.0)
        recommended = min(max(raw, lower, floor), upper)
        delta_pct = (recommended - current_price) / current_price * 100.0
        return {
            "current_price": round(current_price, 2),
            "recommended_price": round(recommended, 2),
            "delta_pct": round(delta_pct, 2),
            "margin_floor_price": round(floor, 2),
            "requires_human_approval": abs(delta_pct) > 5.0,
            "external_write_allowed": False,
        }


class InventoryReorderEngine:
    """Creates reorder signals using demand, lead time and safety stock."""

    def plan(self, *, on_hand: float, daily_demand: float, lead_time_days: float,
             safety_days: float = 7.0, target_cover_days: float = 30.0) -> Dict[str, Any]:
        on_hand = max(float(on_hand), 0.0)
        daily_demand = max(float(daily_demand), 0.0)
        lead_time_days = max(float(lead_time_days), 0.0)
        safety_days = max(float(safety_days), 0.0)
        target_cover_days = max(float(target_cover_days), lead_time_days + safety_days)
        reorder_point = daily_demand * (lead_time_days + safety_days)
        target_stock = daily_demand * target_cover_days
        reorder_qty = max(0.0, target_stock - on_hand) if on_hand <= reorder_point else 0.0
        days_cover = on_hand / daily_demand if daily_demand > 0 else float("inf")
        return {
            "reorder_point": round(reorder_point, 2),
            "recommended_reorder_qty": round(reorder_qty, 2),
            "days_cover": round(days_cover, 2) if days_cover != float("inf") else None,
            "stockout_risk": daily_demand > 0 and on_hand < daily_demand * lead_time_days,
            "requires_purchase_approval": reorder_qty > 0,
        }


class CampaignBudgetAllocator:
    """Allocates a bounded budget by risk-adjusted growth score while preserving reserve."""

    def allocate(self, campaigns: Iterable[Mapping[str, Any]], *, total_budget: float,
                 reserve_ratio: float = 0.20, max_campaign_share: float = 0.40) -> Dict[str, Any]:
        total_budget = max(float(total_budget), 0.0)
        reserve_ratio = max(0.0, min(float(reserve_ratio), 0.95))
        max_campaign_share = max(0.05, min(float(max_campaign_share), 1.0))
        deployable = total_budget * (1.0 - reserve_ratio)
        rows = []
        for c in campaigns:
            roas = max(float(c.get("roas", 0.0) or 0.0), 0.0)
            confidence = max(0.0, min(float(c.get("confidence", 0.0) or 0.0), 1.0))
            risk = max(0.0, min(float(c.get("risk", 0.0) or 0.0), 1.0))
            saturation = max(0.0, min(float(c.get("saturation", 0.0) or 0.0), 1.0))
            score = roas * confidence * (1.0 - risk) * (1.0 - 0.5 * saturation)
            rows.append((str(c.get("id", "unknown")), score))
        score_sum = sum(score for _, score in rows)
        cap = deployable * max_campaign_share
        allocations: Dict[str, float] = {}
        if score_sum > 0:
            for campaign_id, score in rows:
                allocations[campaign_id] = round(min(deployable * score / score_sum, cap), 2)
        spent = sum(allocations.values())
        return {
            "allocations": allocations,
            "deployable_budget": round(deployable, 2),
            "reserve": round(total_budget - spent, 2),
            "requires_external_write_approval": True,
        }


class CohortLTVForecaster:
    """Simple cohort retention/LTV forecast from observed values; no synthetic customer data."""

    def forecast(self, cohort: Mapping[str, Any], periods: int = 6) -> Dict[str, Any]:
        periods = max(1, min(int(periods), 24))
        aov = max(float(cohort.get("aov", 0.0) or 0.0), 0.0)
        gross_margin_pct = max(0.0, min(float(cohort.get("gross_margin_pct", 0.0) or 0.0), 100.0))
        initial_customers = max(float(cohort.get("customers", 0.0) or 0.0), 0.0)
        retention = max(0.0, min(float(cohort.get("period_retention", 0.0) or 0.0), 1.0))
        purchase_frequency = max(float(cohort.get("purchase_frequency", 1.0) or 0.0), 0.0)
        period_values = []
        customers = initial_customers
        cumulative_margin = 0.0
        for p in range(1, periods + 1):
            gross_margin = customers * aov * purchase_frequency * gross_margin_pct / 100.0
            cumulative_margin += gross_margin
            period_values.append({"period": p, "active_customers": round(customers, 2), "gross_margin": round(gross_margin, 2)})
            customers *= retention
        per_customer_ltv = cumulative_margin / initial_customers if initial_customers > 0 else 0.0
        return {"periods": period_values, "forecast_ltv_per_customer": round(per_customer_ltv, 2)}


class ExperimentationEngine:
    """Evaluates experiment candidates against explicit baseline and guardrails."""

    def evaluate(self, *, baseline: Mapping[str, float], variant: Mapping[str, float],
                 min_uplift_pct: float = 3.0) -> Dict[str, Any]:
        baseline_conv = float(baseline.get("conversion_rate", 0.0) or 0.0)
        variant_conv = float(variant.get("conversion_rate", 0.0) or 0.0)
        baseline_margin = float(baseline.get("margin_pct", 0.0) or 0.0)
        variant_margin = float(variant.get("margin_pct", 0.0) or 0.0)
        baseline_return = float(baseline.get("return_rate_pct", 0.0) or 0.0)
        variant_return = float(variant.get("return_rate_pct", 0.0) or 0.0)
        uplift = ((variant_conv - baseline_conv) / baseline_conv * 100.0) if baseline_conv > 0 else 0.0
        promote = uplift >= min_uplift_pct and variant_margin >= baseline_margin and variant_return <= baseline_return
        return {
            "uplift_pct": round(uplift, 2),
            "decision": "PROMOTE_CANDIDATE" if promote else "KEEP_BASELINE",
            "requires_human_promotion_approval": promote,
        }


class CustomerSegmentationEngine:
    """Rules-based customer segmentation for deterministic and auditable targeting."""

    def segment(self, customers: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for c in customers:
            orders = int(c.get("orders", 0) or 0)
            spend = float(c.get("lifetime_spend", 0.0) or 0.0)
            days = int(c.get("days_since_last_order", 9999) or 9999)
            returns = float(c.get("return_rate_pct", 0.0) or 0.0)
            if orders >= 3 and spend >= 250 and days <= 90 and returns <= 20:
                segment = "VIP"
            elif orders >= 2 and days <= 120:
                segment = "LOYAL"
            elif orders == 1 and days <= 60:
                segment = "NEW"
            elif days > 180:
                segment = "WINBACK"
            else:
                segment = "ACTIVE"
            result.append({"customer_id": c.get("id"), "segment": segment})
        return result


class SupplierFailoverOrchestrator:
    """Selects an eligible backup supplier without issuing purchase orders."""

    def route(self, suppliers: Sequence[Mapping[str, Any]], *, primary_id: str) -> Dict[str, Any]:
        primary = next((s for s in suppliers if str(s.get("id")) == str(primary_id)), None)
        if primary and primary.get("gate") == "PASS":
            return {"route": "PRIMARY", "supplier_id": primary_id, "requires_approval": False}
        eligible = [s for s in suppliers if str(s.get("id")) != str(primary_id) and s.get("gate") == "PASS" and s.get("sku_compatible", True)]
        eligible.sort(key=lambda s: float(s.get("score", 0.0) or 0.0), reverse=True)
        if not eligible:
            return {"route": "HOLD", "supplier_id": None, "requires_approval": True}
        return {"route": "FAILOVER_CANDIDATE", "supplier_id": eligible[0].get("id"), "requires_approval": True}


@dataclass(frozen=True)
class ProfitOptimizationDecision:
    gate: str
    actions: tuple[str, ...]
    reason: str
    autonomous_internal_actions_allowed: bool
    external_write_approval_required: bool = True


class ClosedLoopProfitOptimizer:
    """Coordinates profit actions under evidence, risk and spend guardrails."""

    def decide(self, *, evidence_gate: str, executive_gate: str, ci_gate: str,
               regression: bool, profit_delta_pct: float, anomaly_count: int,
               supplier_gate: str, spend_change_pct: float = 0.0) -> ProfitOptimizationDecision:
        if regression:
            return ProfitOptimizationDecision("BLOCK", ("rollback_candidate_changes",), "regression_detected", True)
        if evidence_gate != "PASS" or executive_gate != "PASS" or ci_gate != "PASS":
            return ProfitOptimizationDecision("BLOCK", ("refresh_evidence_and_close_gates",), "prerequisite_gate_not_green", True)
        if supplier_gate == "BLOCK":
            return ProfitOptimizationDecision("BLOCK", ("hold_affected_skus", "prepare_supplier_failover"), "supplier_blocked", True)
        actions: List[str] = []
        if anomaly_count > 0:
            actions.append("run_bounded_anomaly_remediation")
        if profit_delta_pct < 0:
            actions.extend(("pause_negative_margin_scaling", "recalculate_price_budget_inventory"))
        else:
            actions.append("prepare_growth_canary")
        if abs(float(spend_change_pct)) > 10.0:
            actions.append("require_budget_owner_approval")
        return ProfitOptimizationDecision(
            "PASS" if profit_delta_pct >= 0 and anomaly_count == 0 else "REVIEW",
            tuple(dict.fromkeys(actions)),
            "guardrails_satisfied" if profit_delta_pct >= 0 else "profit_regression_requires_optimization",
            True,
            True,
        )
