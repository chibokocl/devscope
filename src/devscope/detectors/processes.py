"""Detect running dev processes (Node, Python, Go workers, etc.)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cmdline: list[str]
    cwd: str | None = None
    cpu_pct: float = 0.0
    mem_pct: float = 0.0


def get_dev_processes() -> list[ProcessInfo]:
    """Return Node.js, Python, and Go processes that look like dev servers."""
    # TODO: implement using psutil
    return []
