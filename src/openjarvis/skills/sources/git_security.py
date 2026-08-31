"""Security helpers for external Git-backed skill sources.

External skill repositories are untrusted input. This module provides a
single fail-closed boundary for repository URL validation, immutable revision
pinning, clean staging checkouts and checkout attestation.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

_FULL_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_GITHUB_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

_GIT_ENV_KEYS_TO_REMOVE = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_ASKPASS",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_EXEC_PATH",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_TEMPLATE_DIR",
    "GIT_WORK_TREE",
}


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


def _git_environment() -> dict[str, str]:
    """Build a non-interactive Git environment without inherited Git overrides."""
    env = os.environ.copy()
    for key in tuple(env):
        if key in _GIT_ENV_KEYS_TO_REMOVE or key.startswith("GIT_CONFIG_"):
            env.pop(key, None)

    # External skill sources are public HTTPS repositories. Ignore user/system
    # Git config so repository-controlled attributes cannot activate a locally
    # configured smudge/filter command during checkout.
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    return env


def _run_git(
    cache_root: Path,
    *args: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run Git without replacement objects, hooks, fsmonitor or inherited overrides."""
    with tempfile.TemporaryDirectory(prefix="openjarvis-empty-hooks-") as hooks_dir:
        return subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-c",
                f"core.hooksPath={hooks_dir}",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(cache_root),
                *args,
            ],
            check=True,
            text=True,
            capture_output=capture_output,
            env=_git_environment(),
        )


def _assert_git_directory(cache_root: Path) -> None:
    if cache_root.is_symlink():
        raise SkillSourceSecurityError("skill cache root must not be a symlink")
    git_dir = cache_root / ".git"
    if git_dir.is_symlink() or not git_dir.is_dir():
        raise SkillSourceSecurityError(
            "skill cache must contain a regular non-symlink .git directory"
        )


def _assert_no_object_rewrites(cache_root: Path) -> None:
    """Reject replacement refs and legacy grafts before trusting object identity."""
    replacements = _run_git(
        cache_root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace",
        capture_output=True,
    ).stdout.strip()
    if replacements:
        raise SkillSourceSecurityError(
            "skill cache contains Git replacement refs that can rewrite object identity"
        )

    grafts = cache_root / ".git" / "info" / "grafts"
    if grafts.exists() or grafts.is_symlink():
        raise SkillSourceSecurityError(
            "skill cache contains a legacy Git graft file"
        )


def _assert_no_hidden_index_paths(cache_root: Path) -> None:
    """Reject index flags that can hide modified tracked files from status output."""
    listed = _run_git(
        cache_root,
        "ls-files",
        "-v",
        capture_output=True,
    ).stdout.splitlines()
    for entry in listed:
        if not entry:
            continue
        marker = entry[0]
        # `git ls-files -v` lowercases the tag for assume-unchanged paths;
        # skip-worktree paths are tagged `S`. Either can suppress worktree
        # modifications from the ordinary porcelain status boundary.
        if marker.islower() or marker == "S":
            raise SkillSourceSecurityError(
                "skill cache index contains hidden assume-unchanged or skip-worktree paths"
            )


def assert_trusted_checkout(
    cache_root: Path,
    repo_url: str,
    revision: str,
) -> None:
    """Attest origin, immutable object identity, index state and worktree cleanliness."""
    expected_url = normalize_github_https_url(repo_url)
    expected_revision = validate_full_commit_sha(revision)
    _assert_git_directory(cache_root)

    try:
        _assert_no_object_rewrites(cache_root)
        _assert_no_hidden_index_paths(cache_root)

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
        raise SkillSourceSecurityError(
            "failed to attest skill source checkout"
        ) from exc


def sync_pinned_checkout(cache_root: Path, repo_url: str, revision: str) -> None:
    """Build one approved immutable checkout in a fresh staging directory.

    Existing caches are never used as Git execution roots during synchronization.
    A fresh staging repository is initialized with inherited Git configuration,
    hooks, fsmonitor, interactive prompts and Git-LFS smudging disabled. Only
    after exact-HEAD and clean-worktree attestation is the disposable old cache
    replaced with the staged checkout.
    """
    normalized_url = normalize_github_https_url(repo_url)
    normalized_revision = validate_full_commit_sha(revision)
    cache_root = Path(cache_root)

    if cache_root.is_symlink():
        raise SkillSourceSecurityError("skill cache root must not be a symlink")
    if cache_root.exists() and not cache_root.is_dir():
        raise SkillSourceSecurityError("skill cache root must be a directory")

    cache_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{cache_root.name}.staging-",
            dir=str(cache_root.parent),
        )
    )

    promoted = False
    try:
        _run_git(staging, "init", "--template=")
        _run_git(staging, "remote", "add", "origin", normalized_url)
        _run_git(
            staging,
            "fetch",
            "--depth=1",
            "--no-tags",
            "origin",
            normalized_revision,
        )
        _run_git(staging, "checkout", "--detach", "--force", normalized_revision)
        _run_git(staging, "reset", "--hard", normalized_revision)
        _run_git(staging, "clean", "-ffdx")
        assert_trusted_checkout(staging, normalized_url, normalized_revision)

        if cache_root.exists():
            shutil.rmtree(cache_root)
        staging.replace(cache_root)
        promoted = True

        # Re-attest from the final location before returning it to a resolver.
        assert_trusted_checkout(cache_root, normalized_url, normalized_revision)
    except subprocess.CalledProcessError as exc:
        raise SkillSourceSecurityError(
            "unable to stage approved immutable skill revision"
        ) from exc
    finally:
        if not promoted and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


__all__ = [
    "SkillSourceSecurityError",
    "assert_trusted_checkout",
    "normalize_github_https_url",
    "sync_pinned_checkout",
    "validate_full_commit_sha",
]
