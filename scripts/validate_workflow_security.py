from __future__ import annotations

from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
UNTRUSTED_TRIGGERS = (
    "issue_comment:",
    "issues:",
    "pull_request_review_comment:",
    "pull_request_review:",
)
FORBIDDEN_WITH_UNTRUSTED_INPUT = (
    "contents: write",
    "id-token: write",
    "secrets.",
    "claude-code-action@",
)

errors: list[str] = []

for path in sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml"))):
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()

    if "pull_request_target:" in lowered:
        errors.append(f"{path}: pull_request_target is forbidden in the public repo")

    if "persist-credentials: true" in lowered:
        errors.append(f"{path}: persisted checkout credentials are forbidden")

    has_untrusted_trigger = any(trigger in lowered for trigger in UNTRUSTED_TRIGGERS)
    if has_untrusted_trigger:
        for forbidden in FORBIDDEN_WITH_UNTRUSTED_INPUT:
            if forbidden in lowered:
                errors.append(
                    f"{path}: untrusted public trigger cannot be combined with {forbidden}"
                )

if errors:
    print("PUBLIC_WORKFLOW_TRUST_BOUNDARY=FAIL")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("PUBLIC_WORKFLOW_TRUST_BOUNDARY=PASS")
print("PULL_REQUEST_TARGET=DENY")
print("UNTRUSTED_TRIGGER_SECRETS=DENY")
print("UNTRUSTED_TRIGGER_CONTENT_WRITE=DENY")
print("PERSISTED_CHECKOUT_CREDENTIALS=DENY")
