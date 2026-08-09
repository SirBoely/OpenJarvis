"""Security helpers for external Git-backed skill sources.

External skill repositories are untrusted input. This module provides a
single fail-closed boundary for repository URL validation, immutable revision
pinning, origin attestation and clean-worktree checks.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

_FULL_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_GITHUB_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class SkillSourceSecurityError(ValueError):
    """Raised when an external skill source violates the trust policy."""


def validate_full_commit_sha(revision: str) -> str:
    """Return a normalized full Git commit SHA or fail closed.

    Short SHAs, branches, tags and other mutable refs are intentionally not
    accepted in immutable mode.
    """
    value = revision.strip()
    if not _FULL_COMMIT_RE.fullmatch(value):
        raise SkillSourceSecurityError(
            "immutable skill sources require a full 40-character commit SHA"
        )
    return value.lower()


def normalize_github_https_url(repo_url: str) -> str:
    """Validate and normalize a public GitHub HTTPS repository URL.

    Credentials, query strings, fragments, SSH/file protocols and arbitrary
    hosts are rejected so Git cannot be redirected to local files or an
    attacker-controlled credential endpoint.
    """
    parsed = urlparse(repo_url.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise SkillSourceSecurityError(
            "external skill repositories must use https://github.com/<owner>/<repo>"
        )
    if parsed.username or parsed.password or parsed.port:
        raise SkillSourceSecurityError("repository URLs must not embed credentials")
    if parsed.query or parsed.fragment or parsed.params:
        raise SkillSourceSecurityError(
            "repository URLs must not contain query parameters or fragments"
        )

    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/") if path else []
    if (
        len(parts) != 2
        or any(part in {".", ".."} for part in parts)
        or not all(_GITHUB_COMPONENT_RE.fullmatch(part) for part in parts)
    ):
        raise SkillSourceSecurityError(
            "repository URL must identify exactly one GitHub owner/repository"
        )

    owner, repo = parts
    return f"https://github.com/{owner}/{repo}.git"


def _run_git(
    cache_root: Path,
    *args: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cache_root), *args],
        check=True,
        text=True,
        capture_output=capture_output,
    )


def _assert_git_directory(cache_root: Path) -> None:
    git_dir = cache_root / ".git"
    if git_dir.is_symlink() or not git_dir.is_dir():
        raise SkillSourceSecurityError(
            "skill cache must contain a regular non-symlink .git directory"
        )


def assert_trusted_checkout(
    cache_root: Path,
    repo_url: str,
    revision: str,
) -> None:
    """Attest origin, HEAD and worktree cleanliness for a pinned checkout."""
    expected_url = normalize_github_https_url(repo_url)
    expected_revision = validate_full_commit_sha(revision)
    _assert_git_directory(cache_root)

    try:
        origin = _run_git(
            cache_root,
            "remote",
            "get-url",
            "origin",
            capture_output=True,
        ).stdout.strip()
        normalized_origin = normalize_github_https_url(origin)
        if normalized_origin != expected_url:
            raise SkillSourceSecurityError("skill cache origin does not match policy")

        head = _run_git(
            cache_root,
            "rev-parse",
            "HEAD",
            capture_output=True,
        ).stdout.strip().lower()
        if head != expected_revision:
            raise SkillSourceSecurityError(
                "skill cache HEAD does not match the approved immutable revision"
            )

        status = _run_git(
            cache_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignored=matching",
            capture_output=True,
        ).stdout.strip()
        if status:
            raise SkillSourceSecurityError(
                "skill cache contains modified, untracked or ignored content"
            )
    except subprocess.CalledProcessError as exc:
        raise SkillSourceSecurityError("failed to attest skill source checkout") from exc


def sync_pinned_checkout(cache_root: Path, repo_url: str, revision: str) -> None:
    """Synchronize a cache to one approved immutable commit and attest it.

    The cache is disposable. Existing tracked, untracked and ignored data are
    reset before attestation so stale local content cannot silently survive.
    """
    normalized_url = normalize_github_https_url(repo_url)
    normalized_revision = validate_full_commit_sha(revision)
    cache_root = Path(cache_root)

    if cache_root.exists() and not (cache_root / ".git").exists():
        raise SkillSourceSecurityError(
            "skill cache path exists but is not an attested Git checkout"
        )

    if not cache_root.exists():
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--no-checkout", normalized_url, str(cache_root)],
            check=True,
            text=True,
        )

    _assert_git_directory(cache_root)

    # Refuse a poisoned cache before fetching from it.
    try:
        origin = _run_git(
            cache_root,
            "remote",
            "get-url",
            "origin",
            capture_output=True,
        ).stdout.strip()
        if normalize_github_https_url(origin) != normalized_url:
            raise SkillSourceSecurityError("skill cache origin does not match policy")

        _run_git(cache_root, "fetch", "--no-tags", "--prune", "origin", normalized_revision)
        _run_git(cache_root, "checkout", "--detach", "--force", normalized_revision)
        _run_git(cache_root, "reset", "--hard", normalized_revision)
        _run_git(cache_root, "clean", "-ffdx")
    except subprocess.CalledProcessError as exc:
        raise SkillSourceSecurityError(
            "unable to synchronize approved immutable skill revision"
        ) from exc

    assert_trusted_checkout(cache_root, normalized_url, normalized_revision)


__all__ = [
    "SkillSourceSecurityError",
    "assert_trusted_checkout",
    "normalize_github_https_url",
    "sync_pinned_checkout",
    "validate_full_commit_sha",
]
