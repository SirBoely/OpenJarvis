from btrades_executive_os import (
    CampaignBudgetAllocator,
    ClosedLoopProfitOptimizer,
    CohortLTVForecaster,
    CustomerSegmentationEngine,
    DynamicPricingEngine,
    ExperimentationEngine,
    InventoryReorderEngine,
    SKUProfitabilityEngine,
    SupplierFailoverOrchestrator,
)


def test_sku_profitability_flags_negative_sku():
    rows = SKUProfitabilityEngine().analyze([
        {"sku": "A", "units_sold": 10, "revenue": 1000, "cogs": 300, "fulfilment_cost": 100, "fees": 50, "refunds": 50, "attributed_ad_cost": 100},
        {"sku": "B", "units_sold": 5, "revenue": 200, "cogs": 150, "fulfilment_cost": 40, "fees": 20, "refunds": 30, "attributed_ad_cost": 50},
    ])
    assert rows[0]["gate"] == "PASS"
    assert rows[1]["gate"] == "BLOCK"


def test_dynamic_pricing_respects_bounds_and_margin_floor():
    out = DynamicPricingEngine().recommend(current_price=50, unit_cost=30, demand_index=1.5, min_margin_pct=25, max_change_pct=10)
    assert 45 <= out["recommended_price"] <= 55
    assert out["recommended_price"] >= out["margin_floor_price"]
    assert out["external_write_allowed"] is False


def test_inventory_reorder_requires_purchase_approval():
    out = InventoryReorderEngine().plan(on_hand=20, daily_demand=5, lead_time_days=5, safety_days=3, target_cover_days=20)
    assert out["recommended_reorder_qty"] > 0
    assert out["requires_purchase_approval"] is True


def test_campaign_allocator_preserves_reserve_and_caps_share():
    out = CampaignBudgetAllocator().allocate([
        {"id": "meta", "roas": 4, "confidence": .9, "risk": .1, "saturation": .2},
        {"id": "google", "roas": 2, "confidence": .8, "risk": .2, "saturation": .1},
    ], total_budget=1000, reserve_ratio=.2, max_campaign_share=.5)
    assert out["deployable_budget"] == 800
    assert out["reserve"] >= 200
    assert max(out["allocations"].values()) <= 400


def test_cohort_ltv_forecast_decreases_active_customers():
    out = CohortLTVForecaster().forecast({"customers": 100, "aov": 50, "gross_margin_pct": 50, "period_retention": .8, "purchase_frequency": 1}, periods=3)
    assert out["periods"][1]["active_customers"] < out["periods"][0]["active_customers"]
    assert out["forecast_ltv_per_customer"] > 0


def test_experiment_requires_guardrails_for_promotion():
    good = ExperimentationEngine().evaluate(
        baseline={"conversion_rate": 2, "margin_pct": 30, "return_rate_pct": 5},
        variant={"conversion_rate": 2.2, "margin_pct": 31, "return_rate_pct": 4},
    )
    bad = ExperimentationEngine().evaluate(
        baseline={"conversion_rate": 2, "margin_pct": 30, "return_rate_pct": 5},
        variant={"conversion_rate": 2.3, "margin_pct": 20, "return_rate_pct": 7},
    )
    assert good["decision"] == "PROMOTE_CANDIDATE"
    assert bad["decision"] == "KEEP_BASELINE"


def test_customer_segmentation_and_supplier_failover():
    segs = CustomerSegmentationEngine().segment([
        {"id": "c1", "orders": 4, "lifetime_spend": 500, "days_since_last_order": 20, "return_rate_pct": 2},
        {"id": "c2", "orders": 1, "lifetime_spend": 50, "days_since_last_order": 250, "return_rate_pct": 0},
    ])
    assert segs[0]["segment"] == "VIP"
    assert segs[1]["segment"] == "WINBACK"
    route = SupplierFailoverOrchestrator().route([
        {"id": "p", "gate": "BLOCK", "score": 50},
        {"id": "b", "gate": "PASS", "score": 92, "sku_compatible": True},
    ], primary_id="p")
    assert route["route"] == "FAILOVER_CANDIDATE"
    assert route["requires_approval"] is True


def test_closed_loop_optimizer_fails_closed_and_detects_regression():
    blocked = ClosedLoopProfitOptimizer().decide(
        evidence_gate="PASS", executive_gate="PASS", ci_gate="PASS", regression=True,
        profit_delta_pct=2, anomaly_count=0, supplier_gate="PASS",
    )
    assert blocked.gate == "BLOCK"
    assert "rollback_candidate_changes" in blocked.actions
    ready = ClosedLoopProfitOptimizer().decide(
        evidence_gate="PASS", executive_gate="PASS", ci_gate="PASS", regression=False,
        profit_delta_pct=5, anomaly_count=0, supplier_gate="PASS",
    )
    assert ready.gate == "PASS"
    assert ready.external_write_approval_required is True
