"""Module 2 — devscope conflicts.

Automated conflict detection: port clashes, duplicate DBs, orphaned
containers, dead MCP targets, and more.
"""

from __future__ import annotations

import json
import os
import re
import socket
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import psutil
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devscope.detectors import docker as docker_det
from devscope.detectors import mcp as mcp_det
from devscope.detectors import ports as ports_det
from devscope.detectors import postgres as pg_det
from devscope.detectors import processes as proc_det
from devscope.output.theme import CRITICAL, INFO, PANEL_BORDER, STATUS_DIM, TABLE_HEADER, WARNING
from devscope.registry.store import load_projects

console = Console()
app = typer.Typer(help="Detect conflicts and misconfigurations before they cause errors.")


# ── Data model ────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Conflict:
    severity: Severity
    category: str      # e.g. "port", "docker", "database", "mcp", "resource"
    title: str
    detail: str


# ── Check functions ───────────────────────────────────────────────────────────

def _port_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def check_port_conflicts(
    port_list: list[ports_det.PortInfo],
    pg_instances: list[pg_det.PostgresInstance],
) -> list[Conflict]:
    """Flag ports claimed by multiple processes, and duplicate Postgres ports."""
    results: list[Conflict] = []

    # Multiple processes on the same port
    port_map: dict[int, list[str]] = {}
    for p in port_list:
        name = p.process_name or f"pid:{p.pid}"
        port_map.setdefault(p.port, []).append(name)
    for port, procs in port_map.items():
        if len(procs) > 1:
            results.append(Conflict(
                severity=Severity.CRITICAL,
                category="port",
                title=f"Port {port} used by multiple processes",
                detail=", ".join(procs),
            ))

    # Duplicate Postgres ports (local + Docker on same port)
    pg_ports: dict[int, list[str]] = {}
    for pg in pg_instances:
        label = f"{pg.source}({pg.container_name or pg.data_dir or '?'})"
        pg_ports.setdefault(pg.port, []).append(label)
    for port, sources in pg_ports.items():
        if len(sources) > 1:
            results.append(Conflict(
                severity=Severity.CRITICAL,
                category="port",
                title=f"Duplicate Postgres on port {port}",
                detail=", ".join(sources),
            ))

    # Registry-declared port conflicts (two projects claim same port)
    registry = load_projects()
    declared: dict[int, list[str]] = {}
    for proj_name, proj in registry.projects.items():
        for port in proj.ports:
            declared.setdefault(port, []).append(proj_name)
    for port, proj_names in declared.items():
        if len(proj_names) > 1:
            results.append(Conflict(
                severity=Severity.CRITICAL,
                category="port",
                title=f"Registry port conflict on {port}",
                detail=f"Claimed by: {', '.join(proj_names)}",
            ))

    return results


def check_docker_conflicts(
    containers: list[docker_det.ContainerInfo],
    volumes: list[docker_det.VolumeInfo],
) -> list[Conflict]:
    """Flag orphaned containers, volumes without containers, and auto-start failures."""
    results: list[Conflict] = []

    registry = load_projects()
    registered_containers: set[str] = set()
    for proj in registry.projects.values():
        registered_containers.update(proj.docker_containers)

    for c in containers:
        if c.status in ("exited", "dead"):
            is_registered = c.name in registered_containers or c.project_label is not None
            if not is_registered:
                results.append(Conflict(
                    severity=Severity.INFO,
                    category="docker",
                    title=f"Orphaned container: {c.name}",
                    detail=f"Status: {c.status}  Image: {c.image}",
                ))

            # Auto-start failure: restart policy = always but exited
            restart_policy = ""
            # We don't have restart policy in ContainerInfo — skip for now
            # (would need to add it to the dataclass)

    for v in volumes:
        if not v.containers:
            results.append(Conflict(
                severity=Severity.INFO,
                category="docker",
                title=f"Volume with no container: {v.name}",
                detail="Named volume exists but no container references it",
            ))

    return results


def check_mcp_conflicts(
    port_list: list[ports_det.PortInfo],
) -> list[Conflict]:
    """Flag MCP server entries in .env / config pointing to ports with nothing listening."""
    results: list[Conflict] = []
    listening_ports = {p.port for p in port_list}

    registry = load_projects()
    for proj_name, proj in registry.projects.items():
        for mcp in proj.mcp_servers:
            if mcp.port not in listening_ports and not _port_reachable(mcp.port):
                results.append(Conflict(
                    severity=Severity.WARNING,
                    category="mcp",
                    title=f"Dead MCP target in project '{proj_name}'",
                    detail=f"Port {mcp.port} is configured but nothing is listening",
                ))

    # Also scan .env files for MCP-style env vars pointing to dead ports
    home = Path.home()
    for search_root in [home / "projects", home / "code", home / "dev"]:
        if not search_root.exists():
            continue
        for env_file in search_root.rglob(".env"):
            try:
                _check_env_mcp_ports(env_file, listening_ports, results)
            except OSError:
                pass

    return results


def _check_env_mcp_ports(
    env_file: Path,
    listening: set[int],
    results: list[Conflict],
) -> None:
    """Look for MCP_*_PORT vars in a .env file and flag dead ones."""
    for line in env_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "MCP" in line.upper() and "PORT" in line.upper():
            m = re.search(r"=\s*(\d{2,5})", line)
            if m:
                port = int(m.group(1))
                if port not in listening and not _port_reachable(port):
                    results.append(Conflict(
                        severity=Severity.WARNING,
                        category="mcp",
                        title=f"Dead MCP port in {env_file}",
                        detail=f"Port {port} not listening (from: {line[:60]})",
                    ))


def check_database_conflicts(
    pg_instances: list[pg_det.PostgresInstance],
) -> list[Conflict]:
    """Flag duplicate database names across Postgres instances."""
    results: list[Conflict] = []

    # Collect DB names per instance (we only have names if previously fetched)
    db_name_map: dict[str, list[str]] = {}
    for pg in pg_instances:
        source_label = f"{pg.source}:{pg.port}"
        for db_name in pg.databases:
            db_name_map.setdefault(db_name, []).append(source_label)

    for db_name, sources in db_name_map.items():
        if len(sources) > 1:
            results.append(Conflict(
                severity=Severity.WARNING,
                category="database",
                title=f"Duplicate database name: '{db_name}'",
                detail=f"Found in: {', '.join(sources)}",
            ))

    # .env DATABASE_URL validation
    registry = load_projects()
    listening_pg_ports = {pg.port for pg in pg_instances if pg.is_reachable}
    for proj_name, proj in registry.projects.items():
        env_path = Path(proj.path).expanduser() / (proj.env_file or ".env")
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text(errors="replace").splitlines():
                if not line.strip().startswith("DATABASE_URL"):
                    continue
                m = re.search(r":(\d{2,5})/", line)
                if m:
                    port = int(m.group(1))
                    if port not in listening_pg_ports:
                        results.append(Conflict(
                            severity=Severity.WARNING,
                            category="database",
                            title=f"DATABASE_URL points to unreachable port in '{proj_name}'",
                            detail=f"Port {port} not reachable — check {env_path}",
                        ))
        except OSError:
            pass

    return results


def check_resource_conflicts(procs: list[proc_det.ProcessInfo]) -> list[Conflict]:
    """Flag processes consuming >80% memory."""
    results: list[Conflict] = []
    total_mem = psutil.virtual_memory().total
    for p in procs:
        if p.mem_pct > 80.0:
            mem_gb = (p.mem_pct / 100) * total_mem / (1024 ** 3)
            results.append(Conflict(
                severity=Severity.WARNING,
                category="resource",
                title=f"High memory usage: {p.name} (pid {p.pid})",
                detail=f"{p.mem_pct}% — {mem_gb:.1f} GB",
            ))
    return results


# ── Rendering ─────────────────────────────────────────────────────────────────

_SEVERITY_ICON = {
    Severity.CRITICAL: "🔴",
    Severity.WARNING:  "🟡",
    Severity.INFO:     "🔵",
}

_SEVERITY_STYLE = {
    Severity.CRITICAL: CRITICAL,
    Severity.WARNING:  WARNING,
    Severity.INFO:     INFO,
}


def _render_conflicts(conflicts_list: list[Conflict]) -> None:
    if not conflicts_list:
        console.print(f"[bold green]✓  No conflicts detected.[/]")
        return

    # Group by severity
    grouped: dict[Severity, list[Conflict]] = {s: [] for s in Severity}
    for c in conflicts_list:
        grouped[c.severity].append(c)

    for severity in (Severity.CRITICAL, Severity.WARNING, Severity.INFO):
        items = grouped[severity]
        if not items:
            continue

        t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
        t.add_column("Category")
        t.add_column("Issue")
        t.add_column("Detail")

        style = _SEVERITY_STYLE[severity]
        for c in items:
            t.add_row(
                f"[{style}]{c.category}[/]",
                c.title,
                f"[{STATUS_DIM}]{c.detail}[/]",
            )

        icon = _SEVERITY_ICON[severity]
        console.print(Panel(
            t,
            title=f"{icon}  {severity.value}",
            border_style=style,
        ))


# ── Command ───────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def conflicts(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Interactive mode — resolve each conflict (v0.2)."),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ports: bool = typer.Option(False, "--ports", help="Only check port conflicts."),
    docker: bool = typer.Option(False, "--docker", help="Only check Docker-related issues."),
) -> None:
    """Run all conflict checks, grouped by severity."""
    if fix:
        console.print(f"[{STATUS_DIM}]--fix is available in v0.2[/]")
        raise typer.Exit()

    check_all = not any([ports, docker])

    with console.status("[bold cyan]Running conflict checks…[/]", spinner="dots"):
        pg_instances = pg_det.detect_all()
        docker_available = docker_det.is_docker_available()
        containers = docker_det.get_containers() if docker_available else []
        volumes = docker_det.get_volumes() if docker_available else []
        port_list = ports_det.get_listening_ports()
        procs = proc_det.get_dev_processes() if check_all else []

    all_conflicts: list[Conflict] = []

    if check_all or ports:
        all_conflicts += check_port_conflicts(port_list, pg_instances)

    if check_all or docker:
        all_conflicts += check_docker_conflicts(containers, volumes)

    if check_all:
        all_conflicts += check_mcp_conflicts(port_list)
        all_conflicts += check_database_conflicts(pg_instances)
        all_conflicts += check_resource_conflicts(procs)

    if json_output:
        def _serialize(obj: object) -> object:
            if isinstance(obj, Severity):
                return obj.value
            raise TypeError(f"Not serializable: {type(obj)}")
        typer.echo(json.dumps([asdict(c) for c in all_conflicts], indent=2, default=_serialize))
        return

    _render_conflicts(all_conflicts)

    # Summary line
    n_crit = sum(1 for c in all_conflicts if c.severity == Severity.CRITICAL)
    n_warn = sum(1 for c in all_conflicts if c.severity == Severity.WARNING)
    n_info = sum(1 for c in all_conflicts if c.severity == Severity.INFO)
    if all_conflicts:
        console.print(
            f"\n[{CRITICAL}]{n_crit} critical[/]  "
            f"[{WARNING}]{n_warn} warning[/]  "
            f"[{INFO}]{n_info} info[/]"
        )
