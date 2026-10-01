# EXEC-OS-005 Commerce Data Contract

## Event envelope
Every ingested commerce event should provide:
- `event_id`: globally unique/idempotency key.
- `type`: supported event type.
- `order_id`: commerce order identifier when applicable.
- `occurred_at`: source timestamp.
- `correlation_id`: cross-system trace identifier.
- `source`: connector/system of origin.
- `schema_version`: event schema version.
- `payload`: event-specific fields.

## Data classes
### Restricted customer data
Name, address, email, phone, support contents and order-linked identifiers. These may be processed only in approved operational stores and must not be emitted as Grafana metric labels.

### Financial evidence
Order amount, refund amount, fee, supplier cost and reconciliation references. Financial evidence is traceable but this contract does not create accounting recognition.

### Operational evidence
Fulfillment state, supplier SLA, inventory, delivery and incident state.

### Analytical evidence
Aggregated conversion, contribution margin, return rate, attribution and merchandising scores. Prefer aggregate/pseudonymous values for dashboards.

## Idempotency
No external side effect may occur without an idempotency key/correlation ID. Duplicate event IDs must not create duplicate fulfillments, refunds, catalog mutations or financial actions.

## Provenance
Derived records preserve source identifiers, observed time, transformation version and confidence where relevant. Unknown data remains unknown; zero is not a substitute for missing evidence unless explicitly defined by a metric contract.

## Retention hooks
Retention is policy-driven by record class. The runtime must support configurable retention/deletion/anonymization actions rather than hard-coded indefinite retention. Legal/accounting holds supersede routine deletion when lawfully required.

## Schema evolution
Breaking changes require a new `schema_version`, compatibility tests and migration evidence. Consumers must reject unsupported critical schema versions rather than partially processing them.
