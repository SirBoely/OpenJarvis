"""Tests for direct cloud provider routing."""

from __future__ import annotations

import asyncio

import pytest

from openjarvis.server.cloud_router import _stream_google


def test_google_stream_rejects_path_control_in_model_name() -> None:
    stream = _stream_google(
        "gemini-2.5-pro/../../other-endpoint?alt=json",
        [],
        0.7,
        1024,
    )

    with pytest.raises(ValueError, match="Invalid Google model name"):
        asyncio.run(anext(stream))
