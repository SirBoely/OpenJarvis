from btrades_executive_os.core import (
    AnalyticsAgent,
    ExecutiveTriage,
    FeedbackRetrainingLoop,
    Goal,
    GoalTrackingAgent,
    OperationsAgent,
    ResourceManagementSystem,
)


def test_analytics_agent_metrics():
    result = AnalyticsAgent().analyze({"revenue": 1000, "cost": 600, "orders": 20, "sessions": 400, "returns": 1})
    assert result["gross_profit"] == 400
    assert result["margin_pct"] == 40
    assert result["aov"] == 50
    assert result["conversion_pct"] == 5
    assert result["return_rate_pct"] == 5


def test_goal_tracking_flags_underperformance():
    result = GoalTrackingAgent().score([Goal("revenue", 100, 90), Goal("evidence", 100, 70)])
    assert result["status"] == "AT_RISK"
    assert "evidence" in result["at_risk"]


def test_resource_manager_preserves_reserve():
    result = ResourceManagementSystem().allocate(1000, {"ads": 600, "rd": 600}, reserve_ratio=0.25)
    assert round(result["ads"] + result["rd"], 2) == 750
    assert result["reserve"] == 250


def test_bookkeeping_gap_detection():
    tasks = ResourceManagementSystem().bookkeeping_tasks([
        {"id": "t1", "receipt_id": None, "category": None, "reconcile": False}
    ])
    assert {t["type"] for t in tasks} == {"missing_receipt", "uncategorized_transaction", "reconciliation_required"}


def test_operations_green_path_runs_canary():
    state = {"payment_gate": "PASS", "supplier_gate": "PASS", "fulfilment_gate": "PASS", "legal_gate": "PASS"}
    assert OperationsAgent().triage(state) == ["run_sales_canary"]


def test_operations_blocks_on_legal_gap():
    state = {"payment_gate": "PASS", "supplier_gate": "PASS", "fulfilment_gate": "PASS", "legal_gate": "FAIL"}
    assert "hold_launch_for_compliance_review" in OperationsAgent().triage(state)


def test_feedback_loop_requires_human_promotion():
    result = FeedbackRetrainingLoop().evaluate(
        {"quality": 0.80, "roi": 1.0, "risk": 0.10},
        {"quality": 0.85, "roi": 1.1, "risk": 0.08},
    )
    assert result["proposal"] == "PROMOTE"
    assert result["requires_human_approval"] is True


def test_executive_triage_all_green():
    context = {
        "capital": {"margin_pct": 35, "cash_buffer_months": 4},
        "engineering": {"data_quality": 0.96, "ci_pass_rate": 0.99},
        "trust": {"compliance_coverage": 0.99, "critical_risks": 0},
    }
    result = ExecutiveTriage().run(context)
    assert result["overall_gate"] == "PASS"
    assert result["autonomous_execution_allowed"] is True


def test_executive_triage_fail_closed():
    context = {
        "capital": {"margin_pct": 35, "cash_buffer_months": 4},
        "engineering": {"data_quality": 0.96, "ci_pass_rate": 0.99},
        "trust": {"compliance_coverage": 0.80, "critical_risks": 1},
    }
    result = ExecutiveTriage().run(context)
    assert result["overall_gate"] == "BLOCK"
    assert result["autonomous_execution_allowed"] is False
