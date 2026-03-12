"""Module 2 — devscope conflicts.

Automated conflict detection: port clashes, duplicate DBs, orphaned
containers, dead MCP targets, and more.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Detect conflicts and misconfigurations before they cause errors.")


@app.callback(invoke_without_command=True)
def conflicts(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Interactive mode — resolve each conflict."),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ports: bool = typer.Option(False, "--ports", help="Only check port conflicts."),
    docker: bool = typer.Option(False, "--docker", help="Only check Docker-related issues."),
) -> None:
    """Run all conflict checks, grouped by severity."""
    # TODO: implement
    typer.echo("devscope conflicts — not yet implemented")
