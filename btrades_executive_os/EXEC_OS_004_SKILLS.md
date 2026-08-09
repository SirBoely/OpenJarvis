# EXEC-OS-004 — Adaptive Growth & Profit Optimization Fabric

## SKU Profitability Skill
Computes contribution profit, contribution margin and profit per unit using supplied revenue/cost evidence. Negative contribution => BLOCK. No synthetic costs or revenue.

## Dynamic Pricing Skill
Produces bounded recommendations only. Guardrails: explicit margin floor, maximum price-change percentage, demand and inventory signals. External price writes are disabled by default; material changes require owner approval.

## Inventory / Reorder Skill
Computes reorder point, days of cover, stockout risk and reorder quantity from observed demand, lead time and safety-stock policy. Purchase orders remain approval-gated.

## Campaign Budget Allocator Skill
Ranks campaigns using ROAS, confidence, saturation and risk, preserves a cash/budget reserve and caps campaign concentration. It outputs an allocation proposal, never an autonomous external spend command.

## Cohort / LTV Forecast Skill
Projects active customers and gross-margin LTV from observed cohort AOV, margin, retention and purchase frequency. Forecasts must identify assumptions and may not generate synthetic customer records.

## Experimentation Skill
Candidate promotion requires conversion uplift plus non-degrading margin and return rate. Promotion is a candidate state only and remains approval/canary gated.

## Customer Segmentation Skill
Deterministic, auditable customer segmentation (VIP, LOYAL, NEW, ACTIVE, WINBACK). Sensitive/protected attributes are excluded from segmentation logic.

## Supplier Failover Skill
Primary PASS => keep primary. Primary unavailable/BLOCK => choose highest-scoring compatible PASS backup as a failover candidate. If no eligible supplier exists, HOLD the SKU. Failover purchasing remains approval-gated.

## Closed-Loop Profit Optimizer Skill
Prerequisites: evidence PASS + executive PASS + CI PASS + no regression + supplier not BLOCK. It may autonomously run read-only analytics, generate remediation tasks, create price/budget/reorder proposals and prepare canaries. External writes, spend changes, supplier purchases and production promotion require approval.

## Optimization Cycle
1. Read latest commerce, attribution, supplier, finance and PMO evidence.
2. Score profitability per SKU.
3. Generate bounded price and reorder candidates.
4. Allocate marketing budget subject to reserves and concentration caps.
5. Forecast cohort LTV and segment customers.
6. Evaluate experiments and supplier failover readiness.
7. Run closed-loop profit decision under executive + CI guardrails.
8. Canary eligible changes.
9. Compare realized profit, margin, returns, CAC/LTV and operational incidents against baseline.
10. Regression => rollback candidate and evidence record; improvement => promotion candidate with approval.
