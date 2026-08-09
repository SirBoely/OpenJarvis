# Security Policy

## Supported security posture

OpenJarvis treats external repositories, skills, prompts, model output, retrieved content, learning traces, and imported artifacts as **untrusted input** unless an operator explicitly establishes trust.

Security-sensitive deployments should apply least privilege and keep credentials outside the repository. Never commit API keys, tokens, wallet seed phrases, private keys, signing material, production database credentials, or customer data.

## External skill safety

- Skill scripts are not imported unless the operator explicitly opts in.
- Imported skill filesystem content must consist only of regular files and directories; symlinks and special filesystem entries are rejected.
- A recorded source commit is provenance, not proof of trust. Production operators should approve and pin the exact upstream revision they intend to use.
- Treat `SKILL.md`, references, templates, assets, few-shot examples, learning overlays, and retrieved text as potentially adversarial instructions or data.
- Do not grant an imported skill credentials or write-capable tools solely because it parses successfully.

## Agent and tool safety

For deployments that can affect source code, infrastructure, financial systems, wallets, or production data:

1. Default to read-only capabilities.
2. Separate planning from execution.
3. Require explicit authorization for write-capable tools.
4. Use narrowly scoped and short-lived credentials.
5. Require independent validation before promotion or deployment.
6. Keep signing keys and recovery phrases outside the agent runtime.
7. Log provenance and tool decisions without logging secret values.

## Reporting a vulnerability

Please do not disclose exploitable vulnerabilities, credentials, or sensitive deployment information in a public issue.

Use GitHub's private vulnerability reporting / security advisory mechanism for this repository when available. Include affected revision, impact, reproduction steps, and a minimal remediation suggestion. Avoid attaching real secrets or production data.

## Dependency and CI security

Dependency update monitoring is configured for GitHub Actions, Python/uv, and Rust/Cargo. Security-sensitive deployments should additionally pin third-party GitHub Actions and external skill sources to reviewed immutable revisions and revalidate them before promotion.
