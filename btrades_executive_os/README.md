# B-Trades Executive Agentic OS

This extension adds a fail-closed executive triage layer to OpenJarvis.

## Top 3 Leader Agents

1. **Business Intelligence & Capital Leader** — BI, unit economics, capital allocation, cash reserves, finance evidence and bookkeeping gaps.
2. **Data Science / DevOps / RevOps / R&D Leader** — analytics, data quality, experiments, CI/CD, revenue attribution, model evaluation and release engineering.
3. **Governance / Legal / Compliance / Operations Leader** — operational readiness, controls, legal/compliance gates, evidence freshness, incidents and safe execution.

## Specialist Agents

- AnalyticsAgent
- OperationsAgent
- GoalTrackingAgent
- ResourceManagementSystem
- FeedbackRetrainingLoop

## Triage Contract

All three leaders participate in the executive decision. Governance is fail-closed: a BLOCK from the Trust/Governance leader blocks autonomous execution. REVIEW allows preparation and remediation, but not unrestricted production writes. PASS allows only actions already permitted by the approval policy.

## Autonomous vs approval-required

Autonomous:
- read-only analytics
- KPI and goal scoring
- internal remediation/task generation
- bookkeeping gap detection
- experiment analysis
- evidence refresh proposals

Human approval required:
- payments, transfers or external financial writes
- contracts or legal assertions
- production deployments when the repository requires approval
- model promotion/retraining activation
- destructive changes

## Feedback and retraining cycle

1. Collect outcome metrics and traces.
2. Compare baseline versus candidate.
3. Require quality improvement, non-negative ROI delta and non-increasing risk.
4. Generate a PROMOTE/REJECT proposal.
5. Require human approval before promotion.
6. Store the result for the next calibration cycle.

## Resource and bookkeeping loop

The resource manager protects a reserve before allocating deployable cash. It also creates tasks for missing receipts, uncategorized transactions and unreconciled events, enabling downstream accounting workflows without silently inventing ledger entries.

## Example

```python
from btrades_executive_os import ExecutiveTriage

context = {
    "capital": {"margin_pct": 35, "cash_buffer_months": 4},
    "engineering": {"data_quality": 0.96, "ci_pass_rate": 0.99},
    "trust": {"compliance_coverage": 0.99, "critical_risks": 0},
}

result = ExecutiveTriage().run(context)
assert result["overall_gate"] == "PASS"
```

## Production gates

- package compiles on Python 3.10-3.13
- focused pytest suite passes
- import smoke test passes
- governance BLOCK semantics tested
- resource reserve invariant tested
- retraining promotion remains approval-gated

The GitHub Actions workflow `.github/workflows/btrades-executive-os.yml` enforces these focused gates on pull requests touching this extension.
