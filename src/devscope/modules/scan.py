"""Module 1 — devscope scan.

Full inventory: Postgres instances, Docker containers, occupied ports,
running MCP servers, dev processes, volumes, and networks.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devscope.detectors import docker as docker_det
from devscope.detectors import mcp as mcp_det
from devscope.detectors import ports as ports_det
from devscope.detectors import postgres as pg_det
from devscope.detectors import processes as proc_det
from devscope.output.theme import (
    BULLET_DEAD,
    BULLET_OK,
    PANEL_BORDER,
    STATUS_DIM,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARN,
    TABLE_HEADER,
)

console = Console()
app = typer.Typer(help="Live inventory of every service, port, DB, and container.")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_uptime(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _bullet(ok: bool) -> str:
    return f"[{STATUS_OK}]{BULLET_OK}[/]" if ok else f"[{STATUS_ERROR}]{BULLET_DEAD}[/]"


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_postgres(instances: list[pg_det.PostgresInstance]) -> None:
    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("")       # bullet
    t.add_column("Source")
    t.add_column("Port")
    t.add_column("Status")
    t.add_column("Container / Data Dir")

    for pg in instances:
        status = f"[{STATUS_OK}]reachable[/]" if pg.is_reachable else f"[{STATUS_ERROR}]unreachable[/]"
        detail = pg.container_name or pg.data_dir or "—"
        t.add_row(_bullet(pg.is_reachable), pg.source, str(pg.port), status, detail)

    console.print(Panel(t, title="POSTGRES", border_style=PANEL_BORDER))


def _render_docker(
    containers: list[docker_det.ContainerInfo],
    volumes: list[docker_det.VolumeInfo],
    networks: list[docker_det.NetworkInfo],
) -> None:
    # Containers
    ct = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    ct.add_column("")
    ct.add_column("Name")
    ct.add_column("Image")
    ct.add_column("Status")
    ct.add_column("Ports")
    ct.add_column("Uptime")
    ct.add_column("Project")

    for c in containers:
        is_running = c.status == "running"
        ports_str = "  ".join(f"{cp}→{hp}" for cp, hp in c.ports.items()) or "—"
        project = c.project_label or "—"
        status_color = STATUS_OK if is_running else STATUS_DIM
        ct.add_row(
            _bullet(is_running),
            c.name,
            c.image,
            f"[{status_color}]{c.status}[/]",
            ports_str,
            _fmt_uptime(c.uptime_seconds) if is_running else "—",
            project,
        )

    # Volumes (inline, compact)
    vt = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    vt.add_column("Volume")
    vt.add_column("Used by")
    for v in volumes:
        vt.add_row(v.name, ", ".join(v.containers) or f"[{STATUS_WARN}]none (orphan)[/]")

    # Networks
    nt = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    nt.add_column("Network")
    nt.add_column("Containers")
    for n in networks:
        nt.add_row(n.name, ", ".join(n.containers) or "—")

    from rich.columns import Columns
    console.print(Panel(ct, title="DOCKER CONTAINERS", border_style=PANEL_BORDER))
    if volumes:
        console.print(Panel(vt, title="DOCKER VOLUMES", border_style=PANEL_BORDER))
    if networks:
        console.print(Panel(nt, title="DOCKER NETWORKS", border_style=PANEL_BORDER))


def _render_ports(port_list: list[ports_det.PortInfo]) -> None:
    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("Port", style="bold")
    t.add_column("Process")
    t.add_column("PID")
    t.add_column("Project")

    for p in port_list:
        t.add_row(
            str(p.port),
            p.process_name or "—",
            str(p.pid) if p.pid else "—",
            p.project or "—",
        )

    console.print(Panel(t, title="PORTS", border_style=PANEL_BORDER))


def _render_processes(procs: list[proc_det.ProcessInfo]) -> None:
    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("PID")
    t.add_column("Name")
    t.add_column("CPU%")
    t.add_column("MEM%")
    t.add_column("Working Dir")

    for p in procs:
        t.add_row(str(p.pid), p.name, str(p.cpu_pct), str(p.mem_pct), p.cwd or "—")

    console.print(Panel(t, title="DEV PROCESSES", border_style=PANEL_BORDER))


def _render_mcp(servers: list[mcp_det.MCPServerInfo]) -> None:
    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("")
    t.add_column("Port", style="bold")
    t.add_column("PID")
    t.add_column("Status")
    t.add_column("Config")

    for s in servers:
        status = f"[{STATUS_OK}]reachable[/]" if s.is_reachable else f"[{STATUS_ERROR}]unreachable[/]"
        t.add_row(_bullet(s.is_reachable), str(s.port), str(s.pid) if s.pid else "—", status, s.config_path or "—")

    console.print(Panel(t, title="MCP SERVERS", border_style=PANEL_BORDER))


# ── Command ───────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def scan(
    ctx: typer.Context,
    postgres: bool = typer.Option(False, "--postgres", help="Only show Postgres instances."),
    docker: bool = typer.Option(False, "--docker", help="Only show Docker resources."),
    ports: bool = typer.Option(False, "--ports", help="Only show port usage."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Run a full environment scan (or a filtered subset)."""
    # Determine which sections to show
    show_all = not any([postgres, docker, ports])

    with console.status("[bold cyan]Scanning environment…[/]", spinner="dots"):
        pg_instances = pg_det.detect_all() if (show_all or postgres) else []
        docker_available = docker_det.is_docker_available()
        containers = docker_det.get_containers() if (show_all or docker) and docker_available else []
        volumes = docker_det.get_volumes() if (show_all or docker) and docker_available else []
        networks = docker_det.get_networks() if (show_all or docker) and docker_available else []
        port_list = ports_det.get_listening_ports() if (show_all or ports) else []
        procs = proc_det.get_dev_processes() if show_all else []
        mcp_servers = mcp_det.detect_mcp_servers() if show_all else []

    if json_output:
        data = {
            "postgres": [dataclasses.asdict(p) for p in pg_instances],
            "containers": [dataclasses.asdict(c) for c in containers],
            "volumes": [dataclasses.asdict(v) for v in volumes],
            "networks": [dataclasses.asdict(n) for n in networks],
            "ports": [dataclasses.asdict(p) for p in port_list],
            "processes": [dataclasses.asdict(p) for p in procs],
            "mcp_servers": [dataclasses.asdict(s) for s in mcp_servers],
        }
        typer.echo(json.dumps(data, indent=2))
        return

    if not docker_available and (show_all or docker):
        console.print(f"[{STATUS_WARN}]⚠  Docker daemon not reachable — skipping Docker sections[/]")

    if pg_instances:
        _render_postgres(pg_instances)
    elif show_all or postgres:
        console.print(f"[{STATUS_DIM}]No Postgres instances detected.[/]")

    if show_all or docker:
        if containers:
            _render_docker(containers, volumes, networks)
        elif docker_available:
            console.print(f"[{STATUS_DIM}]No Docker containers found.[/]")

    if port_list:
        _render_ports(port_list)
    elif show_all or ports:
        console.print(f"[{STATUS_DIM}]No listening ports detected.[/]")

    if procs and show_all:
        _render_processes(procs)

    if mcp_servers and show_all:
        _render_mcp(mcp_servers)
