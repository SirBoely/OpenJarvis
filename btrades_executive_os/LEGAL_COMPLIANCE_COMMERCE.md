# B-Trades Commerce Legal & Compliance Control Pack

> Engineering control document, not a substitute for jurisdiction-specific legal advice.

## Scope
Applies to commerce automation, Shopify catalog/order/fulfillment events, marketing and personalization, returns/refunds, customer support, supplier routing and PMO/Grafana telemetry.

## Core control domains

### GDPR / AVG
- Data minimization: collect only fields required for order fulfillment, support, fraud prevention, accounting and explicitly approved analytics.
- Purpose limitation: customer/order data may not be silently repurposed for unrelated profiling.
- Access control: least privilege for customer, payment, address and support data.
- Retention: configure documented retention windows per record type; deletion/anonymization must preserve mandatory accounting/legal records where applicable.
- Data subject requests: access, rectification, deletion, restriction and portability requests route to specialist review with identity verification and evidence logging.
- Automated decisioning: material customer-impact decisions must expose review/escalation paths; protected/sensitive attributes are excluded from commercial segmentation logic.
- Telemetry: no direct personal identifiers in Grafana labels, metric names or high-cardinality dimensions.

### EU consumer commerce
- Product identity, material characteristics, sizing, total price, taxes/fees, delivery expectations and seller identity must be presented accurately before purchase.
- Returns/refund policies must be visible and consistent with applicable statutory consumer rights; internal automation may not reduce mandatory rights.
- Dark patterns, fabricated scarcity, fabricated reviews and misleading countdowns are prohibited.
- Refund automation remains approval-gated until policy, payment-provider and legal conditions are evidenced.

### Marketing / ePrivacy
- Consent-dependent tracking/marketing requires recorded consent evidence where applicable.
- Marketing preference and unsubscribe signals must propagate to downstream campaign systems.
- Customer segmentation must not use protected/sensitive traits and must remain explainable and auditable.

### Payments / fraud
- Do not store raw payment credentials in this package.
- Payment-provider tokens/secrets belong in approved secret stores only.
- Chargebacks, suspected fraud and unusual refund patterns route to specialist review.

### Product claims / advertising
- Claims about compression, health, body shaping, sustainability, delivery or performance require substantiation appropriate to the claim.
- Medical/therapeutic claims must not be generated from generic product metadata.
- Before/after imagery and testimonials require provenance/permission and may not materially misrepresent expected results.

### Supplier / product safety
- Supplier selection must retain evidence of identity, product specification, material/composition evidence, traceability and required safety/compliance documentation.
- BLOCK or missing critical supplier evidence prevents automated SKU launch/fulfillment failover.
- Product recalls or safety incidents trigger immediate HOLD and incident escalation.

### Accounting / tax
- Ledger routing is classification/reconciliation support only; it is not statutory accounting recognition.
- VAT/tax treatment, invoices, OSS/IOSS or other tax obligations require jurisdiction-appropriate accounting/tax validation.
- Transaction, refund, fee and supplier-invoice correlation IDs must remain traceable into finance evidence.

## Required launch evidence
A commerce production launch cannot be marked legally ready unless evidence exists for: seller/business identity, privacy notice, cookie/consent configuration where applicable, terms/checkout disclosures, returns/refund policy, shipping/delivery policy, product information, supplier traceability, customer-service contact path, payment-provider configuration, and retention/access controls.

## Incident classes
- P0: payment compromise, material privacy breach, product safety event, systemic unlawful checkout behavior.
- P1: widespread fulfillment failure, incorrect pricing/tax display, material returns/refunds defect.
- P2: isolated support/SLA failures, catalog inaccuracies without material consumer harm.
P0/P1 require external-write freeze for affected flow until owner/control approval.

## Evidence contract
Every control decision should preserve: correlation_id, source, observed_at, evidence version, gate, reason, action owner, approval requirement and rollback reference. Evidence is append-only; corrections supersede prior records rather than deleting history.
