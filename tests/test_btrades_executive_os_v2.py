from datetime import datetime, timedelta, timezone

from btrades_executive_os import EvidenceRecord, EvidenceRegistry, ExecutiveControlPlane, PromotionController


def _registry(now):
    r = EvidenceRegistry()
    fresh = now - timedelta(minutes=1)
    payloads = {
        "github": {"ci_pass_rate": 1.0},
        "supabase": {"data_quality": 0.98},
        "shopify": {"revenue": 1000, "cost": 600, "orders": 20, "sessions": 500, "returns": 1, "margin_pct": 40},
        "pmo": {"data_quality": 0.97},
        "finance": {"margin_pct": 40, "cash_buffer_months": 4},
        "compliance": {"coverage": 1.0, "critical_risks": 0},
    }
    for domain, payload in payloads.items():
        r.put(EvidenceRecord(domain, domain, fresh, payload, 1.0))
    return r


def test_missing_evidence_blocks():
    r = EvidenceRegistry()
    out = ExecutiveControlPlane().run(r, {})
    assert out["overall_gate"] == "BLOCK"
    assert out["stage"] == "evidence"


def test_stale_evidence_blocks():
    now = datetime.now(timezone.utc)
    r = _registry(now)
    r.put(EvidenceRecord("shopify", "shopify", now - timedelta(hours=2), {}, 1.0))
    assert r.readiness(ExecutiveControlPlane.REQUIRED_EVIDENCE, now)["gate"] == "BLOCK"


def test_green_control_plane_requires_human_promotion():
    now = datetime.now(timezone.utc)
    runtime = {
        "ci_gate": "PASS",
        "canary_ok": True,
        "cash": 10000,
        "resource_requests": {"growth": 3000, "ops": 2000},
        "operations": {"payment_gate": "PASS", "supplier_gate": "PASS", "fulfilment_gate": "PASS", "legal_gate": "PASS"},
        "goals": [{"goal_id": "revenue", "target": 1000, "actual": 1000}],
    }
    out = ExecutiveControlPlane().run(_registry(now), runtime)
    assert out["overall_gate"] == "PASS"
    assert out["human_approval_required"] is True
    assert out["autonomous_execution_allowed"] is False
    assert out["operations_actions"] == ["run_sales_canary"]


def test_regression_forces_rollback():
    d = PromotionController().evaluate(preflight_gate="PASS", ci_gate="PASS", executive_gate="PASS", canary_ok=True, regression=True)
    assert d.gate == "BLOCK"
    assert d.rollback_required is True


def test_ci_failure_blocks_promotion():
    d = PromotionController().evaluate(preflight_gate="PASS", ci_gate="BLOCK", executive_gate="PASS", canary_ok=True, regression=False)
    assert d.gate == "BLOCK"
    assert d.reason == "ci_not_green"
