# EXEC-OS-005 Production Runbook

## Preflight gates
1. Shopify connector health PASS.
2. Catalog source-of-truth freshness PASS.
3. Payment provider health PASS.
4. Primary/backup supplier evidence PASS.
5. Fulfillment routing PASS.
6. Legal/compliance evidence PASS.
7. Margin floor configured per SKU/category.
8. Returns/refund workflow configured.
9. PMO/Grafana telemetry sink configured.
10. Kill switch tested.

## Event flow
Shopify/webhook event -> signature validation at connector boundary -> idempotency/deduplication -> normalized order event -> state-machine transition -> finance/fulfillment/customer-care fanout -> PMO evidence append.

## Canary launch
- Restrict initial exposure by explicit canary configuration.
- Monitor conversion, contribution margin, payment errors, fulfillment errors, returns/refunds, supplier SLA and critical incidents.
- Do not expand when any hard gate is BLOCK.
- Regression creates rollback candidate and freezes related external writes.

## Kill switch
Kill switch disables external catalog, pricing, marketing-spend, refund, purchase-order and fulfillment-reroute writes. Read-only evidence ingestion, analytics, customer-service triage and PMO evidence generation remain available unless the incident requires full isolation.

## Recovery sequence
1. Freeze impacted external writes.
2. Capture correlation IDs and latest evidence snapshot.
3. Identify last known-good configuration/version.
4. Remediate root cause in staging/canary.
5. Run focused CI/preflight.
6. Require legal/governance review when customer rights, privacy, payments, tax or safety are affected.
7. Re-run canary.
8. Promote only after all gates are PASS.

## Failure routing
- Payment issue -> payment incident queue + sales canary hold.
- Supplier BLOCK -> SKU HOLD or approved backup candidate.
- Fulfillment transition violation -> state-machine BLOCK + manual resolution queue.
- Margin breach -> growth/promotion HOLD.
- Privacy/legal complaint -> specialist review; no autonomous response commitment.
- Product safety issue -> immediate SKU HOLD and P0/P1 escalation.
- Telemetry failure -> commerce may continue only when required evidence remains locally durable; production promotion is blocked until evidence write-back recovers.

## Operational SLO candidates
- Event ingestion accepted/rejected visibility: 100%.
- Duplicate event external side effects: 0.
- Illegal state transitions executed: 0.
- Customer-impacting external writes without correlation ID: 0.
- Catalog changes without rollback evidence: 0.
- P0/P1 incident affected-flow write freeze: mandatory.
