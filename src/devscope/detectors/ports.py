"""Port scanning via lsof / psutil."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortInfo:
    port: int
    pid: int | None = None
    process_name: str | None = None
    project: str | None = None   # populated later by project registry lookup


def get_listening_ports() -> list[PortInfo]:
    """Return all TCP ports in LISTEN state with owning process info."""
    # TODO: implement using psutil.net_connections()
    return []
