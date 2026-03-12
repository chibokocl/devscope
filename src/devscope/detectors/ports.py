"""Port scanning via psutil."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass
class PortInfo:
    port: int
    pid: int | None = None
    process_name: str | None = None
    project: str | None = None  # populated later by project registry lookup


def get_listening_ports() -> list[PortInfo]:
    """Return all TCP ports in LISTEN state with owning process info."""
    ports: list[PortInfo] = []
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status != "LISTEN":
                continue
            proc_name: str | None = None
            if conn.pid:
                try:
                    proc_name = psutil.Process(conn.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            ports.append(PortInfo(port=conn.laddr.port, pid=conn.pid, process_name=proc_name))
    except psutil.AccessDenied:
        pass
    return sorted(ports, key=lambda p: p.port)
