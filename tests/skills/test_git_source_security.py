"""Security regression tests for Git-backed external skill sources."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from openjarvis.skills.sources.git_security import (
    SkillSourceSecurityError,
    _git_environment,
    assert_trusted_checkout,
    normalize_github_https_url,
    validate_full_commit_sha,
)
from openjarvis.skills.sources.github import GitHubResolver
from openjarvis.skills.sources.hermes import HermesResolver
from openjarvis.skills.sources.openclaw import OpenClawResolver


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_attested_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "security-tests@example.invalid")
    _git(repo, "config", "user.name", "OpenJarvis Security Tests")
    (repo / "README.md").write_text("trusted\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    _git(
        repo,
        "remote",
        "add",
        "origin",
        "https://github.com/example/skills.git",
    )
    return repo, _git(repo, "rev-parse", "HEAD")


def test_full_commit_sha_required() -> None:
    revision = "A" * 40
    assert validate_full_commit_sha(revision) == "a" * 40

    mutable_or_ambiguous = ("main", "v1.0.0", "abc1234", "g" * 40, "")
    for value in mutable_or_ambiguous:
        with pytest.raises(SkillSourceSecurityError):
            validate_full_commit_sha(value)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/skills",
        "ssh://git@github.com/example/skills.git",
        "https://evil.example/example/skills.git",
        "https://user:token@github.com/example/skills.git",
        "https://github.com/example/skills.git?ref=main",
        "https://github.com/example/skills.git#main",
        "https://github.com/../skills.git",
    ],
)
def test_untrusted_repository_urls_are_rejected(url: str) -> None:
    with pytest.raises(SkillSourceSecurityError):
        normalize_github_https_url(url)


def test_github_https_url_is_normalized() -> None:
    assert (
        normalize_github_https_url("https://github.com/example/skills")
        == "https://github.com/example/skills.git"
    )
    assert (
        normalize_github_https_url("https://github.com/example/skills.git")
        == "https://github.com/example/skills.git"
    )


def test_git_environment_strips_inherited_execution_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/tmp/attacker-git-dir")
    monkeypatch.setenv("GIT_WORK_TREE", "/tmp/attacker-work-tree")
    monkeypatch.setenv("GIT_TEMPLATE_DIR", "/tmp/attacker-template")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "/tmp/attacker-command")

    env = _git_environment()

    assert "GIT_DIR" not in env
    assert "GIT_WORK_TREE" not in env
    assert "GIT_TEMPLATE_DIR" not in env
    assert "GIT_CONFIG_COUNT" not in env
    assert "GIT_CONFIG_KEY_0" not in env
    assert "GIT_CONFIG_VALUE_0" not in env
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_LFS_SKIP_SMUDGE"] == "1"


@pytest.mark.parametrize(
    "resolver_factory",
    [
        lambda root: HermesResolver(cache_root=root),
        lambda root: OpenClawResolver(cache_root=root),
        lambda root: GitHubResolver(
            cache_root=root,
            repo_url="https://github.com/example/skills.git",
        ),
    ],
)
def test_external_sync_fails_closed_without_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resolver_factory,
) -> None:
    monkeypatch.delenv("OPENJARVIS_HERMES_REVISION", raising=False)
    monkeypatch.delenv("OPENJARVIS_OPENCLAW_REVISION", raising=False)
    monkeypatch.delenv("OPENJARVIS_GITHUB_REVISION", raising=False)
    monkeypatch.delenv("OPENJARVIS_ALLOW_MUTABLE_SKILL_SOURCES", raising=False)

    resolver = resolver_factory(tmp_path / "cache")
    with pytest.raises(SkillSourceSecurityError, match="immutable revision"):
        resolver.sync()


def test_mutable_generic_sync_still_rejects_non_github_url(
    tmp_path: Path,
) -> None:
    resolver = GitHubResolver(
        cache_root=tmp_path / "cache",
        repo_url="file:///tmp/attacker-controlled-repo",
        allow_mutable=True,
    )
    with pytest.raises(SkillSourceSecurityError):
        resolver.sync()


def test_clean_checkout_attestation_passes(tmp_path: Path) -> None:
    repo, revision = _make_attested_repo(tmp_path)
    assert_trusted_checkout(
        repo,
        "https://github.com/example/skills.git",
        revision,
    )


def test_checkout_attestation_rejects_wrong_origin(tmp_path: Path) -> None:
    repo, revision = _make_attested_repo(tmp_path)
    with pytest.raises(SkillSourceSecurityError, match="origin"):
        assert_trusted_checkout(
            repo,
            "https://github.com/other/skills.git",
            revision,
        )


def test_checkout_attestation_rejects_wrong_head(tmp_path: Path) -> None:
    repo, _revision = _make_attested_repo(tmp_path)
    wrong_revision = "0" * 40
    with pytest.raises(SkillSourceSecurityError, match="HEAD"):
        assert_trusted_checkout(
            repo,
            "https://github.com/example/skills.git",
            wrong_revision,
        )


def test_checkout_attestation_rejects_untracked_content(
    tmp_path: Path,
) -> None:
    repo, revision = _make_attested_repo(tmp_path)
    (repo / "payload.txt").write_text("poisoned\n", encoding="utf-8")
    with pytest.raises(
        SkillSourceSecurityError,
        match="modified, untracked or ignored",
    ):
        assert_trusted_checkout(
            repo,
            "https://github.com/example/skills.git",
            revision,
        )


def test_checkout_attestation_rejects_ignored_content(tmp_path: Path) -> None:
    repo, _revision = _make_attested_repo(tmp_path)
    (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "add ignore rule")
    revision = _git(repo, "rev-parse", "HEAD")
    (repo / "ignored.txt").write_text("hidden payload\n", encoding="utf-8")

    with pytest.raises(
        SkillSourceSecurityError,
        match="modified, untracked or ignored",
    ):
        assert_trusted_checkout(
            repo,
            "https://github.com/example/skills.git",
            revision,
        )


def test_checkout_attestation_rejects_symlinked_git_marker(
    tmp_path: Path,
) -> None:
    repo, revision = _make_attested_repo(tmp_path)
    real_git = repo / ".git-real"
    (repo / ".git").rename(real_git)
    try:
        (repo / ".git").symlink_to(real_git, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this platform")

    with pytest.raises(SkillSourceSecurityError, match="non-symlink .git"):
        assert_trusted_checkout(
            repo,
            "https://github.com/example/skills.git",
            revision,
        )
