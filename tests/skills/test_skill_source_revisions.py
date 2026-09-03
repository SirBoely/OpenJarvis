"""Regression tests for per-source immutable skill revisions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from openjarvis.cli import cli
from openjarvis.cli.skill_cmd import _get_resolver


def test_github_resolvers_keep_distinct_revisions() -> None:
    revision_a = "a" * 40
    revision_b = "b" * 40

    resolver_a = _get_resolver(
        "github",
        url="https://github.com/example/skills-a.git",
        revision=revision_a,
    )
    resolver_b = _get_resolver(
        "github",
        url="https://github.com/example/skills-b.git",
        revision=revision_b,
    )

    assert resolver_a._revision == revision_a
    assert resolver_b._revision == revision_b
    assert resolver_a._revision != resolver_b._revision


def test_configured_sync_routes_each_mapping_revision_independently() -> None:
    revision_a = "a" * 40
    revision_b = "b" * 40
    cfg = SimpleNamespace(
        skills=SimpleNamespace(
            sources=[
                {
                    "source": "github",
                    "url": "https://github.com/example/skills-a.git",
                    "revision": revision_a,
                    "filter": {},
                },
                {
                    "source": "github",
                    "url": "https://github.com/example/skills-b.git",
                    "revision": revision_b,
                    "filter": {},
                },
            ]
        )
    )
    routed: list[tuple[str, str, str]] = []

    class _FakeResolver:
        def sync(self) -> None:
            return None

        def list_skills(self) -> list:
            return []

    def _capture_resolver(source: str, url: str = "", revision: str = ""):
        routed.append((source, url, revision))
        return _FakeResolver()

    with (
        patch("openjarvis.cli.skill_cmd.load_config", return_value=cfg),
        patch("openjarvis.cli.skill_cmd._get_resolver", side_effect=_capture_resolver),
    ):
        result = CliRunner().invoke(cli, ["skill", "sync"])

    assert result.exit_code == 0, result.output
    assert routed == [
        ("github", "https://github.com/example/skills-a.git", revision_a),
        ("github", "https://github.com/example/skills-b.git", revision_b),
    ]


def test_install_cli_forwards_explicit_revision() -> None:
    revision = "c" * 40
    captured: list[tuple[str, str, str]] = []

    class _FakeResolver:
        def sync(self) -> None:
            return None

        def list_skills(self) -> list:
            return []

    def _capture_resolver(source: str, url: str = "", revision: str = ""):
        captured.append((source, url, revision))
        return _FakeResolver()

    with patch(
        "openjarvis.cli.skill_cmd._get_resolver",
        side_effect=_capture_resolver,
    ):
        result = CliRunner().invoke(
            cli,
            [
                "skill",
                "install",
                "github:missing",
                "--url",
                "https://github.com/example/skills.git",
                "--revision",
                revision,
            ],
        )

    assert result.exit_code == 1
    assert captured == [
        ("github", "https://github.com/example/skills.git", revision),
    ]
