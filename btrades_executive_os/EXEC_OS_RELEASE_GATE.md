# EXEC-OS V1-V5 Consolidated Release Gate

This file records the consolidated release contract for the B-Trades Executive Agentic OS lineage.

Release prerequisites:
- PR targets `main`.
- Python 3.10, 3.11, 3.12 and 3.13 validation jobs pass.
- Package compile passes.
- Focused V1-V5 tests pass.
- Import smoke test passes.
- Governance remains fail-closed.
- External financial, pricing, refund, purchase-order, fulfillment-reroute and production-promotion writes remain approval-gated.
- Legal/privacy/consumer-rights controls remain blocking prerequisites where applicable.
- Runtime evidence must retain provenance and correlation IDs.

A release is considered eligible for merge only when GitHub CI evidence and mergeability are both green against the current `main` base.
