"""Security regression tests for the external skill import trust boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from openjarvis.skills.importer import SkillImporter
from openjarvis.skills.parser import SkillParser
from openjarvis.skills.sources.base import ResolvedSkill
from openjarvis.skills.tool_translator import ToolTranslator


def _resolved(src_dir: Path) -> ResolvedSkill:
    return ResolvedSkill(
        name="secure-skill",
        source="github",
        path=src_dir,
        category="security",
        description="Security fixture",
        commit="deadbeef",
    )


def _importer(target_root: Path) -> SkillImporter:
    return SkillImporter(
        parser=SkillParser(),
        tool_translator=ToolTranslator(),
        target_root=target_root,
    )


def _skill_root(tmp_path: Path) -> Path:
    src = tmp_path / "source" / "secure-skill"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(
        "---\nname: secure-skill\ndescription: Security fixture\n---\nBody\n",
        encoding="utf-8",
    )
    return src


def test_rejects_symlink_in_always_copied_content(tmp_path: Path) -> None:
    src = _skill_root(tmp_path)
    outside = tmp_path / "private.txt"
    outside.write_text("must-not-cross-trust-boundary", encoding="utf-8")
    references = src / "references"
    references.mkdir()
    link = references / "leak.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    target_root = tmp_path / "installed"
    result = _importer(target_root).import_skill(_resolved(src))

    assert result.success is False
    assert any("symlink" in warning.lower() for warning in result.warnings)
    assert not (target_root / "github" / "secure-skill").exists()


def test_rejects_symlinked_manifest(tmp_path: Path) -> None:
    src = tmp_path / "source" / "secure-skill"
    src.mkdir(parents=True)
    outside = tmp_path / "outside-skill.md"
    outside.write_text(
        "---\nname: secure-skill\ndescription: Outside\n---\nBody\n",
        encoding="utf-8",
    )
    try:
        (src / "SKILL.md").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    target_root = tmp_path / "installed"
    result = _importer(target_root).import_skill(_resolved(src))

    assert result.success is False
    assert any("symlink" in warning.lower() for warning in result.warnings)
    assert not (target_root / "github" / "secure-skill").exists()


def test_rejects_symlink_in_opted_in_scripts(tmp_path: Path) -> None:
    src = _skill_root(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("print('should never be imported')", encoding="utf-8")
    scripts = src / "scripts"
    scripts.mkdir()
    try:
        (scripts / "helper.py").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    target_root = tmp_path / "installed"
    result = _importer(target_root).import_skill(_resolved(src), with_scripts=True)

    assert result.success is False
    assert any("symlink" in warning.lower() for warning in result.warnings)
    assert not (target_root / "github" / "secure-skill").exists()
