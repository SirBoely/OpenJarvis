# EXEC-OS-005 Privacy / DPIA Control Template

> Engineering/privacy assessment template; final legal determination should be reviewed for the actual deployment and jurisdictions.

## Processing description
Document each commerce processing activity: purpose, systems, categories of data, data subjects, recipients/processors, storage locations, retention, legal basis assessment and international transfers where applicable.

## High-risk triggers
Escalate for DPIA/legal review when processing includes material automated customer decisions, extensive tracking/profiling, sensitive data, large-scale fraud scoring, novel biometric/identity processing, systematic monitoring or new high-impact data combinations.

## Threat/control checklist
- Excessive data collection -> field allowlists + minimization review.
- Unauthorized access -> least privilege, MFA, secret isolation, audit logging.
- Dashboard leakage -> no direct identifiers in labels; aggregate telemetry.
- Cross-purpose reuse -> explicit purpose tags and connector allowlists.
- Incorrect automated decisions -> confidence/evidence thresholds and human appeal path.
- Retention drift -> configurable retention jobs and legal-hold flags.
- Data subject rights failure -> specialist queue, identity verification and evidence SLA.
- Processor/subprocessor risk -> maintain approved processor inventory and contract evidence.
- Breach detection failure -> incident classification, logging, kill switch and escalation evidence.

## Required evidence fields
`assessment_id`, `version`, `owner`, `systems`, `purposes`, `data_categories`, `legal_basis_review`, `retention_policy`, `processors`, `transfer_review`, `risks`, `controls`, `residual_risk`, `approval`, `review_date`.

## Runtime gate
Privacy gate must BLOCK affected production promotion when a required assessment is missing, expired, materially inconsistent with configured processing, or when unresolved critical privacy risk exists.
