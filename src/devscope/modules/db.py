"""Module 3 — devscope db.

Unified database manager across local + Docker Postgres instances.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field

import psycopg2
import psycopg2.extras
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devscope.detectors.postgres import PostgresInstance, detect_all
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
from devscope.registry.store import load_projects

console = Console()
app = typer.Typer(help="Manage databases across all local and Docker Postgres instances.")


# ── DB introspection helpers ──────────────────────────────────────────────────

@dataclass
class DBMeta:
    name: str
    owner: str
    size_bytes: int
    encoding: str
    table_count: int
    active_connections: int
    instance_port: int
    instance_source: str   # "local" | "docker"
    container_name: str | None = None
    project: str | None = None  # registry project that claims it


def _docker_pg_credentials(container_name: str) -> tuple[str, str]:
    """Try to read POSTGRES_USER / POSTGRES_PASSWORD from a Docker container's env."""
    try:
        import docker  # type: ignore[import-untyped]
        client = docker.from_env()
        container = client.containers.get(container_name)
        env_vars: dict[str, str] = {}
        for entry in (container.attrs.get("Config", {}).get("Env") or []):
            if "=" in entry:
                k, _, v = entry.partition("=")
                env_vars[k] = v
        user = env_vars.get("POSTGRES_USER", "postgres")
        password = env_vars.get("POSTGRES_PASSWORD", "")
        return user, password
    except Exception:
        return "postgres", ""


def _connect(
    port: int,
    dbname: str = "postgres",
    container_name: str | None = None,
) -> "psycopg2.connection":
    user = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))
    password = os.environ.get("PGPASSWORD", "")

    if container_name and not password:
        user, password = _docker_pg_credentials(container_name)

    return psycopg2.connect(
        host="127.0.0.1",
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=3,
    )


def _list_databases(pg: PostgresInstance) -> list[DBMeta]:
    """Return metadata for every user database on a Postgres instance."""
    results: list[DBMeta] = []
    try:
        conn = _connect(pg.port, container_name=pg.container_name)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT
                d.datname          AS name,
                pg_catalog.pg_get_userbyid(d.datdba) AS owner,
                pg_catalog.pg_database_size(d.datname) AS size_bytes,
                pg_catalog.pg_encoding_to_char(d.encoding) AS encoding,
                (SELECT count(*) FROM pg_stat_activity
                 WHERE datname = d.datname AND state IS NOT NULL) AS active_connections
            FROM pg_catalog.pg_database d
            WHERE d.datistemplate = false
              AND d.datname NOT IN ('postgres', 'template0', 'template1')
            ORDER BY d.datname
        """)
        rows = cur.fetchall()

        for row in rows:
            # Count tables
            try:
                conn2 = _connect(pg.port, dbname=row["name"], container_name=pg.container_name)
                cur2 = conn2.cursor()
                cur2.execute(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
                )
                table_count = cur2.fetchone()[0]
                conn2.close()
            except Exception:
                table_count = 0

            results.append(DBMeta(
                name=row["name"],
                owner=row["owner"],
                size_bytes=row["size_bytes"] or 0,
                encoding=row["encoding"],
                table_count=table_count,
                active_connections=row["active_connections"],
                instance_port=pg.port,
                instance_source=pg.source,
                container_name=pg.container_name,
            ))

        cur.close()
        conn.close()
    except Exception as exc:
        console.print(f"[{STATUS_WARN}]  Could not query Postgres on port {pg.port}: {exc}[/]")
    return results


def _fmt_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {unit}"
        b //= 1024
    return f"{b:.0f} TB"


def _project_for_db(db_name: str, port: int) -> str | None:
    registry = load_projects()
    for proj_name, proj in registry.projects.items():
        for db in proj.databases:
            if db.name == db_name and db.port == port:
                return proj_name
    return None


def _find_db(name: str) -> tuple[DBMeta, list[DBMeta]] | None:
    """Find a database by name across all instances. Returns (match, all_dbs)."""
    all_dbs: list[DBMeta] = []
    for pg in detect_all():
        if pg.is_reachable:
            all_dbs.extend(_list_databases(pg))
    matches = [db for db in all_dbs if db.name == name]
    if not matches:
        return None
    return matches[0], all_dbs


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("list")
def db_list() -> None:
    """List ALL databases across local and Docker Postgres instances."""
    with console.status("[bold cyan]Querying Postgres instances…[/]", spinner="dots"):
        pg_instances = detect_all()
        reachable = [pg for pg in pg_instances if pg.is_reachable]

    if not reachable:
        console.print(f"[{STATUS_WARN}]No reachable Postgres instances found.[/]")
        raise typer.Exit()

    with console.status("[bold cyan]Fetching database list…[/]", spinner="dots"):
        all_dbs: list[DBMeta] = []
        for pg in reachable:
            dbs = _list_databases(pg)
            for db in dbs:
                db.project = _project_for_db(db.name, db.instance_port)
            all_dbs.extend(dbs)

    if not all_dbs:
        console.print(f"[{STATUS_DIM}]No user databases found.[/]")
        raise typer.Exit()

    t = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
    t.add_column("")
    t.add_column("Database")
    t.add_column("Port")
    t.add_column("Source")
    t.add_column("Owner")
    t.add_column("Size")
    t.add_column("Tables")
    t.add_column("Conns")
    t.add_column("Project")

    for db in sorted(all_dbs, key=lambda d: (d.instance_port, d.name)):
        project_str = db.project or f"[{STATUS_WARN}]orphan[/]"
        conn_color = STATUS_ERROR if db.active_connections > 0 else STATUS_DIM
        t.add_row(
            f"[{STATUS_OK}]{BULLET_OK}[/]",
            db.name,
            str(db.instance_port),
            db.instance_source,
            db.owner,
            _fmt_size(db.size_bytes),
            str(db.table_count),
            f"[{conn_color}]{db.active_connections}[/]",
            project_str,
        )

    console.print(Panel(t, title=f"DATABASES  ({len(all_dbs)} found)", border_style=PANEL_BORDER))


@app.command("connect")
def db_connect(name: str = typer.Argument(..., help="Database name to connect to.")) -> None:
    """Open an interactive psql session to the named database."""
    with console.status(f"[bold cyan]Locating '{name}'…[/]", spinner="dots"):
        found = _find_db(name)

    if not found:
        console.print(f"[{STATUS_ERROR}]Database '{name}' not found on any reachable Postgres instance.[/]")
        raise typer.Exit(1)

    db, _ = found
    source_label = db.container_name or f"local:{db.instance_port}"
    console.print(
        f"[{STATUS_OK}]Connecting to[/] [bold]{db.name}[/] "
        f"[{STATUS_DIM}]({source_label} · port {db.instance_port})[/]\n"
    )

    user = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))
    password = os.environ.get("PGPASSWORD", "")
    if db.container_name and not password:
        user, password = _docker_pg_credentials(db.container_name)

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    os.execvpe("psql", [
        "psql",
        "-h", "127.0.0.1",
        "-p", str(db.instance_port),
        "-U", user,
        db.name,
    ], env)


@app.command("info")
def db_info(name: str = typer.Argument(..., help="Database name to inspect.")) -> None:
    """Show detailed stats: tables, indexes, size breakdown, active connections."""
    with console.status(f"[bold cyan]Inspecting '{name}'…[/]", spinner="dots"):
        found = _find_db(name)

    if not found:
        console.print(f"[{STATUS_ERROR}]Database '{name}' not found on any reachable Postgres instance.[/]")
        raise typer.Exit(1)

    db, _ = found

    try:
        conn = _connect(db.instance_port, dbname=db.name, container_name=db.container_name)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Table-level size breakdown
        cur.execute("""
            SELECT
                schemaname || '.' || tablename AS table_name,
                pg_total_relation_size(schemaname || '.' || tablename) AS total_bytes,
                pg_relation_size(schemaname || '.' || tablename) AS data_bytes,
                pg_total_relation_size(schemaname || '.' || tablename)
                  - pg_relation_size(schemaname || '.' || tablename) AS index_bytes,
                (SELECT reltuples::bigint FROM pg_class
                 WHERE oid = (schemaname || '.' || tablename)::regclass) AS row_estimate
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY total_bytes DESC
            LIMIT 20
        """)
        tables = cur.fetchall()

        # Active connections
        cur.execute("""
            SELECT pid, usename, application_name, state, query_start::text,
                   left(query, 60) AS query
            FROM pg_stat_activity
            WHERE datname = %s AND state IS NOT NULL
            ORDER BY query_start DESC
        """, (db.name,))
        conns = cur.fetchall()

        # Index count
        cur.execute("""
            SELECT count(*) FROM pg_indexes
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """)
        index_count = cur.fetchone()["count"]

        cur.close()
        conn.close()
    except Exception as exc:
        console.print(f"[{STATUS_ERROR}]Failed to inspect '{name}': {exc}[/]")
        raise typer.Exit(1)

    # ── Summary panel ──────────────────────────────────────────────────────
    project = db.project or _project_for_db(db.name, db.instance_port) or f"[{STATUS_WARN}]orphan[/]"
    summary_lines = [
        f"  Database  : [bold]{db.name}[/]",
        f"  Port      : {db.instance_port}  ({db.instance_source})",
        f"  Owner     : {db.owner}",
        f"  Encoding  : {db.encoding}",
        f"  Size      : {_fmt_size(db.size_bytes)}",
        f"  Tables    : {db.table_count}   Indexes: {index_count}",
        f"  Connections: {db.active_connections} active",
        f"  Project   : {project}",
    ]
    console.print(Panel("\n".join(summary_lines), title=f"DB INFO · {db.name}", border_style=PANEL_BORDER))

    # ── Tables panel ───────────────────────────────────────────────────────
    if tables:
        tt = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
        tt.add_column("Table")
        tt.add_column("Total", justify="right")
        tt.add_column("Data", justify="right")
        tt.add_column("Indexes", justify="right")
        tt.add_column("~Rows", justify="right")

        for row in tables:
            tt.add_row(
                row["table_name"],
                _fmt_size(row["total_bytes"] or 0),
                _fmt_size(row["data_bytes"] or 0),
                _fmt_size(row["index_bytes"] or 0),
                str(row["row_estimate"] or 0),
            )
        console.print(Panel(tt, title="TOP TABLES BY SIZE", border_style=PANEL_BORDER))

    # ── Active connections panel ───────────────────────────────────────────
    if conns:
        ct = Table(header_style=TABLE_HEADER, show_lines=False, box=None, padding=(0, 1))
        ct.add_column("PID")
        ct.add_column("User")
        ct.add_column("App")
        ct.add_column("State")
        ct.add_column("Query")

        for row in conns:
            ct.add_row(
                str(row["pid"]),
                row["usename"] or "—",
                row["application_name"] or "—",
                row["state"] or "—",
                row["query"] or "—",
            )
        console.print(Panel(ct, title="ACTIVE CONNECTIONS", border_style=PANEL_BORDER))
    else:
        console.print(f"[{STATUS_DIM}]No active connections.[/]")
