"""Module 4 — devscope projects.

Project registry: define your local dev stack as code in
~/.devscope/projects.yaml and track actual vs expected state.
"""

from __future__ import annotations

import os
import socket
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devscope.detectors import docker as docker_det
from devscope.detectors import postgres as pg_det
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
from devscope.registry.auto_detect import DEFAULT_SCAN_PATHS, discover_projects
from devscope.registry.schema import DatabaseEntry, MCPServerEntry, ProjectEntry
from devscope.registry.store import PROJECTS_FILE, load_projects, save_projects

console = Console()
app = typer.Typer(help="Manage the project registry (~/.devscope/projects.yaml).")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _port_alive(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _project_status(name: str, proj: ProjectEntry) -> tuple[str, str]:
    """Return (status_label, style) for a project based on actual machine state."""
    issues: list[str] = []

    path_ok = Path(proj.path).expanduser().exists()
    if not path_ok:
        issues.append("path missing")

    for port in proj.ports:
        if not _port_alive(port):
            issues.append(f"port {port} dead")

    for db in proj.databases:
        if not _port_alive(db.port):
            issues.append(f"db port {db.port} dead")

    if issues:
        return "broken", STATUS_ERROR
    if proj.ports or proj.databases:
        alive_ports = [p for p in proj.ports if _port_alive(p)]
        if alive_ports:
            return "active", STATUS_OK
        return "dormant", STATUS_DIM
    if path_ok:
        return "registered", STATUS_DIM
    return "broken", STATUS_ERROR


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("list")
def projects_list() -> None:
    """List all registered projects with status (active / dormant / broken)."""
    registry = load_projects()

    if not registry.projects:
        console.print(f"[{STATUS_DIM}]No projects registered. Run 'devscope projects add' or 'devscope projects auto-detect'.[/]")
        raise typer.Exit()

    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("")
    t.add_column("Name", style="bold")
    t.add_column("Status")
    t.add_column("Path")
    t.add_column("Ports")
    t.add_column("DBs")
    t.add_column("Containers")
    t.add_column("Tags")

    for name, proj in sorted(registry.projects.items()):
        status_label, style = _project_status(name, proj)
        is_ok = status_label in ("active", "registered")
        ports_str = ", ".join(str(p) for p in proj.ports) or "—"
        dbs_str = ", ".join(d.name for d in proj.databases) or "—"
        containers_str = ", ".join(proj.docker_containers) or "—"
        tags_str = ", ".join(proj.tags) or "—"

        t.add_row(
            f"[{style}]{BULLET_OK if is_ok else BULLET_DEAD}[/]",
            name,
            f"[{style}]{status_label}[/]",
            proj.path,
            ports_str,
            dbs_str,
            containers_str,
            f"[{STATUS_DIM}]{tags_str}[/]",
        )

    console.print(Panel(
        t,
        title=f"PROJECTS  ({len(registry.projects)} registered)",
        border_style=PANEL_BORDER,
    ))


@app.command("add")
def projects_add(
    name: str = typer.Argument(..., help="Project name to register."),
    path: str = typer.Option("", "--path", "-p", help="Path to the project directory."),
    description: str = typer.Option("", "--description", "-d", help="Short description."),
    ports: str = typer.Option("", "--ports", help="Comma-separated port numbers."),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags."),
) -> None:
    """Register a new project interactively or via flags."""
    registry = load_projects()

    if name in registry.projects:
        console.print(f"[{STATUS_WARN}]Project '{name}' already exists. Use 'devscope projects edit {name}' to modify it.[/]")
        raise typer.Exit(1)

    # Interactive prompts for missing fields
    if not path:
        path = typer.prompt(f"Path to '{name}'", default=str(Path.cwd()))
    if not description:
        description = typer.prompt("Description (optional)", default="")

    port_list: list[int] = []
    if ports:
        for p in ports.split(","):
            try:
                port_list.append(int(p.strip()))
            except ValueError:
                pass
    else:
        raw = typer.prompt("Ports (comma-separated, optional)", default="")
        for p in raw.split(","):
            try:
                port_list.append(int(p.strip()))
            except ValueError:
                pass

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    entry = ProjectEntry(
        description=description,
        path=str(Path(path).expanduser()),
        ports=port_list,
        tags=tag_list,
    )

    registry.projects[name] = entry
    save_projects(registry)
    console.print(f"[{STATUS_OK}]✓  Project '{name}' registered in {PROJECTS_FILE}[/]")


@app.command("remove")
def projects_remove(
    name: str = typer.Argument(..., help="Project name to remove."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Remove a project from the registry."""
    registry = load_projects()

    if name not in registry.projects:
        console.print(f"[{STATUS_ERROR}]Project '{name}' not found in registry.[/]")
        raise typer.Exit(1)

    if not yes:
        typer.confirm(f"Remove '{name}' from the registry?", abort=True)

    del registry.projects[name]
    save_projects(registry)
    console.print(f"[{STATUS_OK}]✓  Project '{name}' removed.[/]")


@app.command("status")
def projects_status(name: str = typer.Argument(..., help="Project name to inspect.")) -> None:
    """Show expected vs actual state for a specific project."""
    registry = load_projects()

    if name not in registry.projects:
        console.print(f"[{STATUS_ERROR}]Project '{name}' not found in registry.[/]")
        raise typer.Exit(1)

    proj = registry.projects[name]
    path_obj = Path(proj.path).expanduser()

    rows: list[tuple[str, str, str]] = []

    # Path
    path_ok = path_obj.exists()
    rows.append(("path", proj.path, f"[{STATUS_OK}]exists[/]" if path_ok else f"[{STATUS_ERROR}]missing[/]"))

    # Ports
    for port in proj.ports:
        alive = _port_alive(port)
        rows.append((
            "port",
            str(port),
            f"[{STATUS_OK}]listening[/]" if alive else f"[{STATUS_DIM}]not listening[/]",
        ))

    # Databases
    for db in proj.databases:
        alive = _port_alive(db.port)
        rows.append((
            f"db ({db.engine})",
            f"{db.name} @ port {db.port}",
            f"[{STATUS_OK}]reachable[/]" if alive else f"[{STATUS_ERROR}]unreachable[/]",
        ))

    # Docker containers
    running_containers: set[str] = set()
    if docker_det.is_docker_available():
        running_containers = {c.name for c in docker_det.get_containers() if c.status == "running"}

    for cname in proj.docker_containers:
        running = cname in running_containers
        rows.append((
            "container",
            cname,
            f"[{STATUS_OK}]running[/]" if running else f"[{STATUS_DIM}]not running[/]",
        ))

    # MCP servers
    for mcp in proj.mcp_servers:
        alive = _port_alive(mcp.port)
        rows.append((
            "mcp",
            f"port {mcp.port}" + (f" ({mcp.config})" if mcp.config else ""),
            f"[{STATUS_OK}]listening[/]" if alive else f"[{STATUS_ERROR}]not listening[/]",
        ))

    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("Resource")
    t.add_column("Expected")
    t.add_column("Actual")

    for resource, expected, actual in rows:
        t.add_row(resource, expected, actual)

    summary = f"[bold]{name}[/]"
    if proj.description:
        summary += f"  [{STATUS_DIM}]{proj.description}[/]"
    console.print(Panel(t, title=f"PROJECT STATUS · {name}", border_style=PANEL_BORDER))


@app.command("auto-detect")
def projects_auto_detect(
    yes: bool = typer.Option(False, "--yes", "-y", help="Add all detected projects without prompting."),
    paths: list[str] = typer.Option([], "--path", "-p", help="Extra directories to scan (repeatable)."),
) -> None:
    """Scan the filesystem for projects and suggest additions to the registry."""
    from pathlib import Path as _Path

    scan_paths = list(DEFAULT_SCAN_PATHS)
    for p in paths:
        extra = _Path(p).expanduser()
        if extra not in scan_paths:
            scan_paths.append(extra)

    console.print(f"[{STATUS_DIM}]Scanning: {', '.join(str(p) for p in scan_paths)}[/]\n")

    with console.status("[bold cyan]Discovering projects…[/]", spinner="dots"):
        candidates = discover_projects(scan_paths)

    registry = load_projects()
    new_candidates = {k: v for k, v in candidates.items() if k not in registry.projects}

    if not new_candidates:
        console.print(f"[{STATUS_OK}]No new projects found (all already registered).[/]")
        raise typer.Exit()

    # Preview table
    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("Name")
    t.add_column("Path")
    t.add_column("Ports")
    t.add_column("DBs")
    t.add_column("Containers")
    t.add_column("Tags")

    for name, proj in sorted(new_candidates.items()):
        # Show type tag first, then pair tags, dim the rest
        type_tags = [tg for tg in proj.tags if not tg.startswith("pair:")]
        pair_tags = [tg for tg in proj.tags if tg.startswith("pair:")]
        tags_display = ", ".join(type_tags + pair_tags) or "—"
        t.add_row(
            name,
            proj.path,
            ", ".join(str(p) for p in proj.ports) or "—",
            ", ".join(d.name for d in proj.databases) or "—",
            ", ".join(proj.docker_containers) or "—",
            f"[{STATUS_DIM}]{tags_display}[/]",
        )

    console.print(Panel(t, title=f"DETECTED PROJECTS  ({len(new_candidates)} new)", border_style=PANEL_BORDER))

    if yes or typer.confirm(f"\nAdd all {len(new_candidates)} projects to registry?"):
        registry.projects.update(new_candidates)
        save_projects(registry)
        console.print(f"[{STATUS_OK}]✓  Added {len(new_candidates)} projects to {PROJECTS_FILE}[/]")
    else:
        # Per-project prompts
        added = 0
        for name, proj in sorted(new_candidates.items()):
            if typer.confirm(f"Add '{name}' ({proj.path})?"):
                registry.projects[name] = proj
                added += 1
        if added:
            save_projects(registry)
            console.print(f"[{STATUS_OK}]✓  Added {added} projects.[/]")


@app.command("edit")
def projects_edit(name: str = typer.Argument(..., help="Project name to edit.")) -> None:
    """Open the project entry in $EDITOR."""
    registry = load_projects()

    if name not in registry.projects:
        console.print(f"[{STATUS_ERROR}]Project '{name}' not found.[/]")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))
    console.print(f"[{STATUS_DIM}]Opening {PROJECTS_FILE} in {editor}…[/]")
    subprocess.run([editor, str(PROJECTS_FILE)])


@app.command("validate")
def projects_validate() -> None:
    """Validate all registered projects against current machine state."""
    registry = load_projects()

    if not registry.projects:
        console.print(f"[{STATUS_DIM}]No projects registered.[/]")
        raise typer.Exit()

    with console.status("[bold cyan]Validating projects…[/]", spinner="dots"):
        running_containers: set[str] = set()
        if docker_det.is_docker_available():
            running_containers = {c.name for c in docker_det.get_containers() if c.status == "running"}

    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("")
    t.add_column("Project")
    t.add_column("Status")
    t.add_column("Issues")

    all_ok = True
    for name, proj in sorted(registry.projects.items()):
        issues: list[str] = []

        if not Path(proj.path).expanduser().exists():
            issues.append("path missing")
        for port in proj.ports:
            if not _port_alive(port):
                issues.append(f"port {port} dead")
        for db in proj.databases:
            if not _port_alive(db.port):
                issues.append(f"db:{db.name} unreachable")
        for cname in proj.docker_containers:
            if cname not in running_containers:
                issues.append(f"container '{cname}' not running")
        for mcp in proj.mcp_servers:
            if not _port_alive(mcp.port):
                issues.append(f"mcp port {mcp.port} dead")

        if issues:
            all_ok = False
            t.add_row(
                f"[{STATUS_ERROR}]{BULLET_DEAD}[/]",
                name,
                f"[{STATUS_ERROR}]broken[/]",
                ", ".join(issues),
            )
        else:
            t.add_row(
                f"[{STATUS_OK}]{BULLET_OK}[/]",
                name,
                f"[{STATUS_OK}]ok[/]",
                "—",
            )

    console.print(Panel(t, title="PROJECT VALIDATION", border_style=PANEL_BORDER))
    if all_ok:
        console.print(f"[{STATUS_OK}]✓  All projects validated successfully.[/]")


@app.command("orphans")
def projects_orphans() -> None:
    """Show running services not claimed by any registered project."""
    registry = load_projects()

    with console.status("[bold cyan]Scanning for orphans…[/]", spinner="dots"):
        pg_instances = pg_det.detect_all()
        containers = docker_det.get_containers() if docker_det.is_docker_available() else []

    # Collect all registered container names and DB ports
    registered_containers: set[str] = set()
    registered_db_ports: set[int] = set()
    for proj in registry.projects.values():
        registered_containers.update(proj.docker_containers)
        for db in proj.databases:
            registered_db_ports.add(db.port)

    orphan_containers = [
        c for c in containers
        if c.status == "running"
        and c.name not in registered_containers
        and c.project_label is None
    ]

    orphan_pg = [
        pg for pg in pg_instances
        if pg.is_reachable and pg.port not in registered_db_ports
    ]

    if not orphan_containers and not orphan_pg:
        console.print(f"[{STATUS_OK}]✓  No orphaned services found.[/]")
        return

    if orphan_containers:
        ct = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
        ct.add_column("Container")
        ct.add_column("Image")
        ct.add_column("Uptime")
        ct.add_column("Ports")

        for c in orphan_containers:
            ports_str = "  ".join(f"{cp}→{hp}" for cp, hp in c.ports.items()) or "—"
            uptime = c.uptime_seconds
            h, r = divmod(uptime or 0, 3600)
            uptime_str = f"{h}h {r // 60}m" if uptime else "—"
            ct.add_row(c.name, c.image, uptime_str, ports_str)

        console.print(Panel(ct, title=f"[{STATUS_WARN}]ORPHANED CONTAINERS[/]", border_style=PANEL_BORDER))

    if orphan_pg:
        pt = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
        pt.add_column("Source")
        pt.add_column("Port")
        pt.add_column("Container")

        for pg in orphan_pg:
            pt.add_row(pg.source, str(pg.port), pg.container_name or "—")

        console.print(Panel(pt, title=f"[{STATUS_WARN}]ORPHANED POSTGRES INSTANCES[/]", border_style=PANEL_BORDER))
