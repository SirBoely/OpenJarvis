# B-Trades Executive Agentic OS — Role Skills

## Skill: BI-CAPITAL-LEADER
Purpose: convert finance, commerce and PMO evidence into capital allocation and unit-economics decisions.
Inputs: revenue, costs, cash buffer, margin, project ROI, bookkeeping gaps.
Outputs: PASS/REVIEW, allocation proposal, finance remediation queue.
Autonomous: read-only analysis, internal tasks, scenario scoring.
Approval required: payments, transfers, external commitments.

## Skill: DATA-GROWTH-LEADER
Purpose: coordinate Data Science, DevOps, RevOps and R&D around measurable business outcomes.
Inputs: data quality, CI pass rate, attribution, experiment results, model quality, latency/cost.
Outputs: experiment backlog, release recommendation, retraining candidate proposal.
Autonomous: benchmarking, A/B analysis, test generation, evidence refresh proposals.
Approval required: production deployment and model promotion where policy requires it.

## Skill: TRUST-OPS-LEADER
Purpose: fail-closed governance, legal/compliance and operational readiness.
Inputs: compliance coverage, critical risks, evidence freshness, incidents, payment/supplier/fulfilment/legal gates.
Outputs: PASS/BLOCK, control remediation, launch hold, evidence requests.
Autonomous: read-only control checks, issue creation, evidence classification.
Approval required: legal assertions, contracts, destructive production actions.

## Skill: ANALYTICS-AGENT
KPIs: gross profit, margin, AOV, conversion, return rate, CAC/ROAS when evidence exists.
Rule: never fabricate unavailable metrics; emit missing-evidence tasks.

## Skill: OPERATIONS-AGENT
Triage order: legal/compliance -> payment -> supplier -> fulfilment -> canary.
Rule: launch canary only when prerequisite gates are PASS.

## Skill: GOAL-TRACKING-AGENT
Tracks weighted goal attainment, identifies goals below 80% attainment, and emits escalation tasks.

## Skill: RESOURCE-MANAGEMENT-SYSTEM
Protects configurable cash reserve before allocating deployable capital. Generates bookkeeping tasks for missing receipts, uncategorized transactions and unreconciled events.

## Skill: FEEDBACK-RETRAINING-LOOP
Candidate promotion requires: quality delta > 0, ROI delta >= 0, risk delta <= 0. Promotion remains human-gated; regressions require rollback.

## Executive Triage Contract
1. Evidence readiness must PASS.
2. All three leaders evaluate the same normalized context pack.
3. Any Trust/Governance BLOCK => overall BLOCK.
4. Any other REVIEW => overall REVIEW.
5. PASS only makes a promotion candidate eligible; external writes remain subject to approval policy.
6. Canary evidence precedes full rollout.
7. Regression after canary => rollback_required=true.
8. Every cycle produces evidence usable by the next cycle.
