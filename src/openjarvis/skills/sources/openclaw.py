"""OpenClawResolver — resolves skills from the OpenClaw skill index.

Layout:
    skills/<owner>/<skill-name>/SKILL.md
    skills/<owner>/<skill-name>/_meta.json  (optional sidecar registry data)
"""

from __future__ import annotations

import json
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

OPENCLAW_REPO_URL = "https://github.com/openclaw/skills.git"


def _env_allows_mutable_sources() -> bool:
    return os.environ.get("OPENJARVIS_ALLOW_MUTABLE_SKILL_SOURCES", "").lower() in {
        "1",
        "true",
        "yes",
    }


class OpenClawResolver(SourceResolver):
    """Resolves skills from the OpenClaw skill index."""

    name = "openclaw"

    def __init__(
        self,
        cache_root: Path | None = None,
        *,
        revision: str | None = None,
        allow_mutable: bool | None = None,
    ) -> None:
        if cache_root is None:
            cache_root = Path("~/.openjarvis/skill-cache/openclaw/").expanduser()
        self._cache_root = Path(cache_root)
        env_revision = os.environ.get("OPENJARVIS_OPENCLAW_REVISION", "").strip()
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
            sync_pinned_checkout(
                self._cache_root,
                OPENCLAW_REPO_URL,
                self._revision,
            )
            return
        if not self._allow_mutable:
            raise SkillSourceSecurityError(
                "OpenClaw sync requires a full immutable revision. Set "
                "OPENJARVIS_OPENCLAW_REVISION or pass revision=. "
                "Mutable sync is low-trust and requires explicit "
                "OPENJARVIS_ALLOW_MUTABLE_SKILL_SOURCES."
            )
        self._sync_mutable()

    def _sync_mutable(self) -> None:
        expected_url = normalize_github_https_url(OPENCLAW_REPO_URL)
        if self._cache_root.exists() and (self._cache_root / ".git").exists():
            origin = subprocess.run(
                ["git", "-C", str(self._cache_root), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if normalize_github_https_url(origin) != expected_url:
                raise SkillSourceSecurityError(
                    "OpenClaw cache origin does not match policy"
                )
            subprocess.run(
                ["git", "-C", str(self._cache_root), "pull", "--ff-only"],
                check=True,
            )
        elif self._cache_root.exists():
            raise SkillSourceSecurityError(
                "OpenClaw cache path exists but is not a Git checkout"
            )
        else:
            self._cache_root.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", expected_url, str(self._cache_root)],
                check=True,
            )

    def list_skills(self) -> List[ResolvedSkill]:
        if self._revision and self._cache_root.exists():
            assert_trusted_checkout(
                self._cache_root,
                OPENCLAW_REPO_URL,
                self._revision,
            )

        skills_root = self._cache_root / "skills"
        if not skills_root.exists():
            return []

        results: List[ResolvedSkill] = []
        commit = self._read_commit()

        for owner_dir in sorted(skills_root.iterdir()):
            if not owner_dir.is_dir():
                continue
            for skill_dir in sorted(owner_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue

                name, description = self._read_preview(
                    skill_md, default_name=skill_dir.name
                )
                sidecar = self._read_sidecar(skill_dir / "_meta.json")
                results.append(
                    ResolvedSkill(
                        name=name,
                        source=self.name,
                        path=skill_dir,
                        category=owner_dir.name,
                        description=description,
                        commit=commit,
                        sidecar_data=sidecar,
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

    def _read_sidecar(self, sidecar_path: Path) -> dict:
        if not sidecar_path.exists():
            return {}
        try:
            return json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

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


__all__ = ["OpenClawResolver", "OPENCLAW_REPO_URL"]
