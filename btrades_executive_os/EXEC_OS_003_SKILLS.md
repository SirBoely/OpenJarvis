# EXEC-OS-003 — Revenue & Autonomous Operations Fabric

## Revenue Attribution Skill
Inputs: Shopify orders, net revenue, UTM/source/channel metadata.
Outputs: order-level attribution, revenue by channel, unattributed revenue, confidence.
Rule: never invent missing touchpoints; unknown remains unknown.

## Unit Economics Skill
KPIs: CAC, ROAS, LTV, LTV/CAC.
Rule: compute only from supplied evidence; zero denominators yield explicit zero rather than fabricated estimates.

## Supplier SLA Skill
Signals: on-time delivery, defect rate, disputes, quality, response quality, backup readiness.
Gates: PASS >= 85, REVIEW >= 70, otherwise BLOCK.
BLOCK requires SKU hold or backup-supplier route before autonomous fulfilment.

## Ledger Routing Skill
Queues sales, refunds, supplier invoices, ad spend, fees and tax events into reconciliation workflows.
Rule: routing is not accounting recognition. Tax remains review-gated and unknown events require manual accounting review.

## KPI Drift / Anomaly Skill
Compares current KPIs against explicit baselines and per-metric thresholds.
Outputs deterministic anomaly evidence for downstream incident triage.

## Incident Remediation Skill
Priority: payment > fulfilment > blocked supplier > supplier review > KPI drift.
External/destructive actions remain approval-gated; analysis and internal remediation tasks may run autonomously.

## Project Resource Optimizer Skill
Ranks projects by expected ROI, urgency, confidence, readiness and risk.
Ranking produces a recommendation only; capital deployment remains controlled by the Executive Resource Management layer.

## PMO Evidence Write-Back Skill
Builds append-only evidence payloads with correlation_id, gate, metrics and actions.
Direct external writes require an approved adapter and must retain correlation IDs and provenance.

## Control Loop
1. Ingest commerce + finance + operational evidence.
2. Attribute revenue and calculate unit economics.
3. Score suppliers and detect KPI drift.
4. Route ledger events and generate bookkeeping queues.
5. Rank project-resource opportunities.
6. Generate bounded incident-remediation tasks.
7. Produce append-only PMO evidence record.
8. Feed outcome evidence back into EXEC-OS-002 ExecutiveControlPlane.
9. Promote only after evidence, CI, governance and canary gates are green.
