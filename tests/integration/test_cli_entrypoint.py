"""Integration test — verify the CLI entry point loads and returns help."""

from __future__ import annotations

from typer.testing import CliRunner

from devscope.cli import app

runner = CliRunner()


def test_help_exits_cleanly() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "devscope" in result.output.lower()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
