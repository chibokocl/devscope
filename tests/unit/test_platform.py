"""Unit tests for platform utilities."""

from __future__ import annotations

from devscope.utils.platform import is_linux, is_macos, platform_name


def test_platform_name_is_string() -> None:
    assert isinstance(platform_name(), str)


def test_only_one_platform_true() -> None:
    # On any CI machine exactly one (or neither on Windows) should be True
    assert not (is_macos() and is_linux())
