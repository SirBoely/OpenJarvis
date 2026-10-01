from btrades_executive_os import (
    AutonomousCommerceCommandFabric,
    BundleUpsellOptimizer,
    CatalogSyncEngine,
    CustomerServiceTriageAgent,
    ExecutiveTelemetryBuilder,
    FulfillmentStateMachine,
    MarginProtectionEngine,
    MerchandisingOptimizer,
    OrderEventIngestionEngine,
    ProductLaunchCanaryEngine,
    ReturnsRefundsIntelligence,
)


def test_catalog_sync_is_proposal_only():
    result = CatalogSyncEngine().diff(
        [{"sku": "A", "price": 30}, {"sku": "B", "price": 40}],
        [{"sku": "A", "price": 25}, {"sku": "C", "price": 20}],
    )
    assert len(result["creates"]) == 1
    assert len(result["updates"]) == 1
    assert len(result["archives"]) == 1
    assert result["external_write_allowed"] is False


def test_order_event_ingestion_deduplicates_and_rejects_unknown():
    result = OrderEventIngestionEngine().ingest([
        {"event_id": "e1", "type": "order_created", "order_id": "o1"},
        {"event_id": "e1", "type": "order_paid", "order_id": "o1"},
        {"event_id": "e2", "type": "unknown", "order_id": "o1"},
    ])
    assert len(result["accepted"]) == 1
    assert len(result["rejected"]) == 2


def test_fulfillment_state_machine_blocks_illegal_transition():
    machine = FulfillmentStateMachine()
    assert machine.transition("PAID", "ALLOCATED")["gate"] == "PASS"
    blocked = machine.transition("PAID", "DELIVERED")
    assert blocked["gate"] == "BLOCK"
    assert blocked["to"] == "PAID"


def test_customer_service_prioritizes_sensitive_cases():
    rows = CustomerServiceTriageAgent().triage([
        {"id": "1", "kind": "general"},
        {"id": "2", "kind": "privacy_request"},
    ])
    assert rows[0]["ticket_id"] == "2"
    assert rows[0]["requires_human_approval"] is True


def test_returns_refunds_is_intelligence_only():
    result = ReturnsRefundsIntelligence().analyze([
        {"sku": "A", "reason": "size", "value": 40},
        {"sku": "A", "reason": "size", "value": 40},
        {"sku": "B", "reason": "damaged", "value": 50},
    ])
    assert result["top_reason"] == "size"
    assert result["return_value"] == 130
    assert result["refund_external_write_allowed"] is False


def test_product_launch_canary_fails_closed():
    engine = ProductLaunchCanaryEngine()
    result = engine.evaluate(
        {"conversion_pct": 3, "margin_pct": 30, "refund_rate_pct": 5, "critical_incidents": 0},
        {"min_conversion_pct": 2, "min_margin_pct": 20, "max_refund_rate_pct": 8, "max_critical_incidents": 0},
    )
    assert result["gate"] == "PASS"
    blocked = engine.evaluate(
        {"conversion_pct": 3, "margin_pct": 10, "refund_rate_pct": 5, "critical_incidents": 0},
        {"min_conversion_pct": 2, "min_margin_pct": 20, "max_refund_rate_pct": 8, "max_critical_incidents": 0},
    )
    assert blocked["gate"] == "BLOCK"


def test_margin_protection_blocks_floor_breach():
    result = MarginProtectionEngine().protect(current_margin_pct=32, projected_margin_pct=18, floor_margin_pct=20)
    assert result["gate"] == "BLOCK"


def test_merchandising_and_bundle_are_ranked_not_written():
    products = MerchandisingOptimizer().rank([
        {"sku": "A", "contribution_margin_pct": 30, "conversion_pct": 3, "stock_readiness": .9, "return_rate_pct": 4},
        {"sku": "B", "contribution_margin_pct": 15, "conversion_pct": 2, "stock_readiness": .5, "return_rate_pct": 8},
    ])
    assert products[0]["sku"] == "A"
    bundles = BundleUpsellOptimizer().recommend([
        {"id": "x", "attach_rate_pct": 15, "incremental_contribution": 12, "return_rate_delta_pct": 1, "confidence": .9},
        {"id": "y", "attach_rate_pct": 20, "incremental_contribution": -2, "return_rate_delta_pct": 4, "confidence": .9},
    ])
    assert bundles[0]["bundle_id"] == "x"
    assert bundles[0]["gate"] == "PASS"


def test_telemetry_is_append_only_and_pii_safe_contract():
    record = ExecutiveTelemetryBuilder().build(
        correlation_id="BTR-5", metrics={"margin_pct": 30}, gates={"legal": "PASS"}
    )
    assert record["write_mode"] == "append_only"
    assert record["requires_external_write_adapter"] is True


def test_commerce_fabric_requires_all_gates_and_rolls_back_regression():
    fabric = AutonomousCommerceCommandFabric()
    ready = fabric.decide(
        evidence_gate="PASS", executive_gate="PASS", ci_gate="PASS", margin_gate="PASS",
        supplier_gate="PASS", legal_gate="PASS", canary_gate="PASS",
    )
    assert ready.gate == "PASS"
    assert ready.human_approval_required is True
    regression = fabric.decide(
        evidence_gate="PASS", executive_gate="PASS", ci_gate="PASS", margin_gate="PASS",
        supplier_gate="PASS", legal_gate="PASS", canary_gate="PASS", regression=True,
    )
    assert regression.gate == "BLOCK"
    assert "rollback_candidate" in regression.actions
