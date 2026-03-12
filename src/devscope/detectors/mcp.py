"""Detect running MCP (Model Context Protocol) servers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MCPServerInfo:
    port: int
    pid: int | None = None
    config_path: str | None = None
    is_reachable: bool = False


def detect_mcp_servers() -> list[MCPServerInfo]:
    """Return processes matching MCP server patterns with port and config path."""
    # TODO: implement — scan processes for MCP patterns, cross-reference .mcp/ configs
    return []
