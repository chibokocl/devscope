"""Module 3 — devscope db.

Unified database manager across local + Docker Postgres instances.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage databases across all local and Docker Postgres instances.")


@app.command("list")
def db_list() -> None:
    """List ALL databases across local and Docker Postgres instances."""
    # TODO: implement
    typer.echo("devscope db list — not yet implemented")


@app.command("connect")
def db_connect(name: str = typer.Argument(..., help="Database name to connect to.")) -> None:
    """Open an interactive psql session to the named database."""
    # TODO: implement
    typer.echo(f"devscope db connect {name} — not yet implemented")


@app.command("info")
def db_info(name: str = typer.Argument(..., help="Database name to inspect.")) -> None:
    """Show detailed stats: tables, indexes, size breakdown, active connections."""
    # TODO: implement
    typer.echo(f"devscope db info {name} — not yet implemented")
