# EXEC-OS-005 — Autonomous Commerce Command Fabric

## Catalog Synchronization Skill
Diffs desired versus observed Shopify catalog state by SKU. Creates create/update/archive proposals only; no direct catalog mutation. Every external write requires an approved Shopify adapter, correlation ID, rollback plan and audit evidence.

## Order Event Ingestion Skill
Accepts supported order, payment, fulfillment, return, refund and chargeback events. Event IDs are mandatory and deduplicated. Unsupported events are rejected into an evidence queue rather than silently discarded.

## Fulfillment State Machine Skill
Enforces deterministic state transitions from payment through allocation, fulfillment, delivery, return and refund. Illegal transitions fail closed. HOLD is explicit and may only resume through a valid transition.

## Customer Service Triage Skill
Prioritizes chargebacks, privacy requests, legal complaints and fraud above routine customer-care tickets. The agent may classify and route cases autonomously; payment commitments, legal commitments, exceptions and sensitive-data disclosures require human approval.

## Returns / Refunds Intelligence Skill
Aggregates reasons, SKU concentration and financial exposure. It may recommend remediation, sizing/content changes and refund candidates but must never issue external refunds by itself.

## Product Launch Canary Skill
Launch promotion requires explicit minimum conversion and contribution-margin thresholds, maximum refund rate and zero/controlled critical incidents. PASS means candidate only; production rollout stays approval-gated.

## Real-Time Margin Protection Skill
Any proposed price, promotion, bundle, acquisition-spend or fulfillment change that breaches the configured contribution-margin floor or maximum allowed margin drop is blocked before execution.

## Automated Merchandising Skill
Ranks products from contribution margin, conversion, stock readiness, returns and evidence confidence. Rankings are recommendations and cannot bypass inventory, legal, supplier or margin gates.

## Bundle / Upsell Optimizer Skill
Scores bundles on attach rate, incremental contribution, returns impact and confidence. Negative contribution or material returns degradation cannot auto-promote.

## PMO / Grafana Executive Telemetry Skill
Generates append-only telemetry with correlation ID, provenance, metrics and gate states. External PMO/Grafana writes require configured adapters. Sensitive customer data must not be included in labels or metric dimensions.

## Commerce Command Consensus
Required gates before a commerce change becomes eligible for canary/promotion:
1. Evidence PASS.
2. Executive consensus PASS.
3. CI PASS.
4. Margin protection PASS.
5. Supplier readiness PASS.
6. Legal/compliance PASS.
7. Canary PASS.
8. No regression signal.

A PASS remains a promotion candidate; price writes, spend changes, refunds, purchase orders, fulfillment reroutes and production deployment remain controlled external writes.
