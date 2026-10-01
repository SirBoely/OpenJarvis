# EXEC-OS-005 Consumer Commerce Compliance Matrix

| Domain | Required evidence | Runtime gate | Automated action allowed | Human/legal review |
|---|---|---|---|---|
| Seller identity | Legal entity/contact/seller disclosure | BLOCK if missing | Read/verify | Required before launch |
| Product information | SKU, material/composition, size, price, delivery info | BLOCK for material gaps | Compare/detect gaps | Required for disputed claims |
| Pricing | Current price, discount basis, margin evidence | BLOCK on invalid/missing critical data | Recommend only | Required for external price writes |
| Shipping | Method, expected delivery, supplier/fulfillment route | BLOCK if no viable route | Score/route candidate | Required for material policy changes |
| Returns/refunds | Published policy + statutory-rights review | BLOCK if absent | Triage/recommend | Refund execution/exception approval |
| Privacy | Notice, processing inventory, retention/access controls | BLOCK on critical missing evidence | Audit/route requests | DPIA/legal review when triggered |
| Marketing consent | Consent/preference evidence where required | BLOCK affected marketing flow | Suppress/segment based on approved signals | Policy/legal review for new tracking |
| Product claims | Claim provenance/substantiation | BLOCK unsubstantiated material claim | Flag/hold copy | Legal/compliance approval for regulated claims |
| Supplier traceability | Supplier ID, specs, safety/compliance docs | BLOCK affected SKU if critical missing | Score/hold/failover candidate | Approval for supplier/purchase changes |
| Payments | Provider health/config evidence | BLOCK checkout/canary if critical fail | Monitor/triage | External payment config changes |
| Tax/accounting | Invoice/tax/reconciliation evidence | REVIEW/BLOCK by policy | Route/reconcile candidate | Accountant/tax validation |
| Telemetry | Correlation/provenance, PII-safe dimensions | BLOCK promotion if mandatory evidence unavailable | Append local evidence | External sink/config changes |

## Gate precedence
Safety/privacy/payment/consumer-rights critical BLOCK takes precedence over growth, merchandising, experiment or revenue optimization PASS signals.

## Review cadence
Evidence validity periods should be configured per domain. Supplier/product safety and privacy-processing changes require event-driven reassessment in addition to periodic review.
