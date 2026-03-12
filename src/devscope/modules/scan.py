"""Module 1 — devscope scan.

Full inventory: Postgres instances, Docker containers, occupied ports,
running MCP servers, dev processes, volumes, and networks.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Live inventory of every service, port, DB, and container.")


@app.callback(invoke_without_command=True)
def scan(
    ctx: typer.Context,
    postgres: bool = typer.Option(False, "--postgres", help="Only show Postgres instances."),
    docker: bool = typer.Option(False, "--docker", help="Only show Docker resources."),
    ports: bool = typer.Option(False, "--ports", help="Only show port usage."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Run a full environment scan (or a filtered subset)."""
    # TODO: implement
    typer.echo("devscope scan — not yet implemented")
