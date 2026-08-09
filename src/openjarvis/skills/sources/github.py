"""GitHubResolver — generic resolver for GitHub repositories containing skills.

Performs a recursive walk for SKILL.md (or skill.md) files anywhere under the
cache directory. External repositories are pinned to immutable commits by
default; mutable branch tracking requires an explicit low-trust override.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import List

import yaml

from openjarvis.skills.sources.base import ResolvedSkill, SourceResolver
from openjarvis.skills.sources.git_security import (
    SkillSourceSecurityError,
    assert_trusted_checkout,
    normalize_github_https_url,
    sync_pinned_checkout,
    validate_full_commit_sha,
)

LOGGER = logging.getLogger(__name__)


def _env_allows_mutable_sources() -> bool:
    return os.environ.get("OPENJARVIS_ALLOW_MUTABLE_SKILL_SOURCES", "").lower() in {
        "1",
        "true",
        "yes",
    }


class GitHubResolver(SourceResolver):
    """Generic resolver for an approved GitHub repo containing SKILL.md files."""

    name = "github"

    def __init__(
        self,
        cache_root: Path,
        repo_url: str,
        *,
        revision: str | None = None,
        allow_mutable: bool | None = None,
    ) -> None:
        self._cache_root = Path(cache_root)
        # Store the requested URL verbatim so local list-only/test use remains
        # possible. Any network synchronization or pinned attestation validates
        # it through normalize_github_https_url before Git receives it.
        self._repo_url = repo_url.strip()
        env_revision = os.environ.get("OPENJARVIS_GITHUB_REVISION", "").strip()
        self._revision = revision.strip() if revision else env_revision
        if self._revision:
            self._revision = validate_full_commit_sha(self._revision)
        self._allow_mutable = (
            _env_allows_mutable_sources()
            if allow_mutable is None
            else bool(allow_mutable)
        )

    def cache_dir(self) -> Path:
        return self._cache_root

    def sync(self) -> None:
        if self._revision:
            sync_pinned_checkout(self._cache_root, self._repo_url, self._revision)
            return
        if not self._allow_mutable:
            raise SkillSourceSecurityError(
                "GitHub skill sync requires a full immutable revision. Set "
                "OPENJARVIS_GITHUB_REVISION or pass revision=. Mutable sync is "
                "low-trust and requires explicit OPENJARVIS_ALLOW_MUTABLE_SKILL_SOURCES."
            )
        self._sync_mutable()

    def _sync_mutable(self) -> None:
        expected_url = normalize_github_https_url(self._repo_url)
        if self._cache_root.exists() and (self._cache_root / ".git").exists():
            origin = subprocess.run(
                ["git", "-C", str(self._cache_root), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if normalize_github_https_url(origin) != expected_url:
                raise SkillSourceSecurityError(
                    "GitHub skill cache origin does not match policy"
                )
            subprocess.run(
                ["git", "-C", str(self._cache_root), "pull", "--ff-only"],
                check=True,
            )
        elif self._cache_root.exists():
            raise SkillSourceSecurityError(
                "GitHub skill cache path exists but is not a Git checkout"
            )
        else:
            self._cache_root.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", expected_url, str(self._cache_root)],
                check=True,
            )

    def list_skills(self) -> List[ResolvedSkill]:
        if self._revision and (self._cache_root / ".git").exists():
            assert_trusted_checkout(
                self._cache_root,
                self._repo_url,
                self._revision,
            )
        if not self._cache_root.exists():
            return []

        results: List[ResolvedSkill] = []
        commit = self._read_commit()
        seen_dirs: set[Path] = set()

        for pattern in ("SKILL.md", "skill.md"):
            for skill_md in sorted(self._cache_root.rglob(pattern)):
                if ".git" in skill_md.parts:
                    continue
                skill_dir = skill_md.parent
                if skill_dir in seen_dirs:
                    continue
                seen_dirs.add(skill_dir)

                name, description = self._read_preview(
                    skill_md, default_name=skill_dir.name
                )
                try:
                    category = skill_dir.parent.relative_to(self._cache_root).as_posix()
                except ValueError:
                    category = ""

                results.append(
                    ResolvedSkill(
                        name=name,
                        source=self.name,
                        path=skill_dir,
                        category=category,
                        description=description,
                        commit=commit,
                    )
                )

        return results

    def _read_preview(self, skill_md: Path, default_name: str) -> tuple[str, str]:
        try:
            raw = skill_md.read_text(encoding="utf-8")
        except Exception:
            return default_name, ""
        if not raw.startswith("---"):
            return default_name, ""
        rest = raw[3:].lstrip("\n")
        end = rest.find("\n---")
        if end == -1:
            return default_name, ""
        try:
            fm = yaml.safe_load(rest[:end])
        except yaml.YAMLError:
            return default_name, ""
        if not isinstance(fm, dict):
            return default_name, ""
        return str(fm.get("name", default_name)), str(fm.get("description", ""))

    def _read_commit(self) -> str:
        if not (self._cache_root / ".git").exists():
            return ""
        try:
            result = subprocess.run(
                ["git", "-C", str(self._cache_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""


__all__ = ["GitHubResolver"]
