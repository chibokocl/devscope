"""Detect running dev processes (Node, Python, Go workers, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

import psutil

# Process names that indicate a dev server / worker
_DEV_NAMES = {
    "node", "python", "python3", "go", "uvicorn", "gunicorn",
    "flask", "deno", "bun", "ruby", "rails", "puma",
}
_DEV_SUBSTRINGS = ("node", "python", "uvicorn", "gunicorn", "deno", "bun")


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
    results: list[ProcessInfo] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            name = (info["name"] or "").lower()
            if name not in _DEV_NAMES and not any(s in name for s in _DEV_SUBSTRINGS):
                continue
            results.append(ProcessInfo(
                pid=info["pid"],
                name=info["name"] or "",
                cmdline=info["cmdline"] or [],
                cwd=info["cwd"],
                cpu_pct=round(info["cpu_percent"] or 0.0, 1),
                mem_pct=round(info["memory_percent"] or 0.0, 1),
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return results
