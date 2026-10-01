from btrades_executive_os import (
    IncidentRemediationEngine,
    KPIDriftDetector,
    LedgerRouter,
    PMOEvidenceWriter,
    ProjectResourceOptimizer,
    RevenueAttributionEngine,
    SupplierSLAScorer,
    UnitEconomicsEngine,
)


def test_revenue_attribution_aggregates_and_marks_unknown():
    engine = RevenueAttributionEngine()
    rows = engine.attribute([
        {"id": "o1", "net_revenue": 100, "attribution": {"utm_source": "meta", "utm_medium": "paid_social"}},
        {"id": "o2", "net_revenue": 50},
    ])
    agg = engine.aggregate(rows)
    assert agg["total_revenue"] == 150
    assert agg["revenue_by_channel"]["meta"] == 100
    assert agg["unattributed_revenue"] == 50
    assert 0 < agg["weighted_confidence"] < 1


def test_unit_economics():
    result = UnitEconomicsEngine().compute({
        "ad_spend": 200,
        "new_customers": 10,
        "attributed_revenue": 800,
        "aov": 80,
        "purchase_frequency": 2,
        "gross_margin_pct": 50,
        "customer_lifetime_periods": 3,
    })
    assert result["cac"] == 20
    assert result["roas"] == 4
    assert result["ltv"] == 240
    assert result["ltv_cac_ratio"] == 12


def test_supplier_score_gates():
    scorer = SupplierSLAScorer()
    good = scorer.score({
        "id": "s1", "on_time_delivery_pct": 96, "defect_rate_pct": 2,
        "dispute_rate_pct": 1, "quality_score": 94, "response_score": 90,
        "backup_supplier_ready": True,
    })
    bad = scorer.score({
        "id": "s2", "on_time_delivery_pct": 40, "defect_rate_pct": 25,
        "dispute_rate_pct": 20, "quality_score": 40, "response_score": 30,
        "backup_supplier_ready": False,
    })
    assert good["gate"] == "PASS"
    assert bad["gate"] == "BLOCK"


def test_ledger_router_is_non_assertive():
    queues = LedgerRouter().route([
        {"id": "1", "type": "sale", "amount": 100, "correlation_id": "c1"},
        {"id": "2", "type": "tax", "amount": 21, "correlation_id": "c1"},
        {"id": "3", "type": "unknown", "amount": 5},
    ])
    assert "revenue_pending_reconciliation" in queues
    assert "tax_review_required" in queues
    assert "manual_accounting_review" in queues


def test_kpi_drift_and_incident_remediation():
    anomalies = KPIDriftDetector().detect(
        {"conversion": 2.0, "refund_rate": 8.0},
        {"conversion": 3.0, "refund_rate": 4.0},
        {"conversion": 20, "refund_rate": 50},
    )
    assert {a["metric"] for a in anomalies} == {"conversion", "refund_rate"}
    tasks = IncidentRemediationEngine().plan(
        anomalies=anomalies,
        supplier_gates=[{"supplier_id": "s2", "gate": "BLOCK"}],
        payment_gate="BLOCK",
        fulfilment_gate="PASS",
    )
    assert tasks[0]["priority"] == 100
    assert any(t["action"] == "route_to_backup_supplier_or_hold_sku" for t in tasks)


def test_project_optimizer_ranks_best_first():
    ranked = ProjectResourceOptimizer().rank([
        {"id": "a", "expected_roi": 20, "urgency": .5, "confidence": .8, "readiness": .7, "risk": .2},
        {"id": "b", "expected_roi": 40, "urgency": .8, "confidence": .9, "readiness": .9, "risk": .1},
    ])
    assert ranked[0]["project_id"] == "b"


def test_pmo_evidence_writer_is_append_only():
    record = PMOEvidenceWriter().build_record(
        correlation_id="BTR-123", domain="revenue_ops", gate="PASS",
        metrics={"roas": 4.2}, actions=["monitor"],
    )
    assert record["write_mode"] == "append_only"
    assert record["requires_external_write_adapter"] is True
