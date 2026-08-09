---
name: b-trades-openjarvis-role-skill-profile
description: Federated B-Trades AGENT venue contract for OpenJarvis role routing, capability verification, security, release control, and independent evaluation.
---

# OpenJarvis Role-Skill Contract

OpenJarvis is the AGENT venue in the federated B-Trades role-skill architecture.

## Required control chain
`SKILL-005 Pipeline Controller -> agent/tool/data skills -> SKILL-025 QA -> SKILL-035 Security -> SKILL-041 Git control -> SKILL-050 independent evaluation`

## Specialization
- orchestration/state: SKILL-005 + SKILL-012
- provider/tool adapters: SKILL-016
- memory/data/mock fixtures: SKILL-017 + SKILL-019
- privacy/secrets/security: SKILL-033 + SKILL-034 + SKILL-035
- telemetry/performance: SKILL-030 + SKILL-037
- prompt/context/resource optimization: SKILL-042 + SKILL-043 + SKILL-044
- conversational/realtime channels: SKILL-046 + SKILL-049
- CI/release: SKILL-025 + SKILL-041 + SKILL-045 + SKILL-050

## Capability rule
Optional extras, live channels, cloud providers, Docker/GPU paths and external credentials are capabilities that must be discovered and validated in the active environment. Their presence is never inferred from `pyproject.toml` alone.

This profile is additive and does not change OpenJarvis runtime/package behavior.
