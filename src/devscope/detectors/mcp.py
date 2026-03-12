"""Detect running MCP (Model Context Protocol) servers."""

from __future__ import annotations

import socket
from dataclasses import dataclass

import psutil


@dataclass
class MCPServerInfo:
    port: int
    pid: int | None = None
    config_path: str | None = None
    is_reachable: bool = False


def _check_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def detect_mcp_servers() -> list[MCPServerInfo]:
    """Return processes matching MCP server patterns with port and config path."""
    results: list[MCPServerInfo] = []
    seen_ports: set[int] = set()

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"] or []
            cmdline_str = " ".join(cmdline).lower()
            name = (proc.info["name"] or "").lower()

            if "mcp" not in cmdline_str and "mcp" not in name:
                continue

            for conn in proc.net_connections(kind="tcp"):
                if conn.status != "LISTEN" or conn.laddr.port in seen_ports:
                    continue
                port = conn.laddr.port
                seen_ports.add(port)

                config_path: str | None = None
                for part in cmdline:
                    if part.endswith(".json") and "mcp" in part.lower():
                        config_path = part
                        break

                results.append(MCPServerInfo(
                    port=port,
                    pid=proc.info["pid"],
                    config_path=config_path,
                    is_reachable=_check_reachable(port),
                ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return results
