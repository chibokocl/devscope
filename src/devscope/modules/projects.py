"""Module 4 — devscope projects.

Project registry: define your local dev stack as code in
~/.devscope/projects.yaml and track actual vs expected state.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage the project registry (~/.devscope/projects.yaml).")


@app.command("list")
def projects_list() -> None:
    """List all registered projects with status (active / dormant / broken)."""
    # TODO: implement
    typer.echo("devscope projects list — not yet implemented")


@app.command("add")
def projects_add(name: str = typer.Argument(..., help="Project name to register.")) -> None:
    """Register a new project interactively or via flags."""
    # TODO: implement
    typer.echo(f"devscope projects add {name} — not yet implemented")


@app.command("remove")
def projects_remove(name: str = typer.Argument(..., help="Project name to remove.")) -> None:
    """Remove a project from the registry."""
    # TODO: implement
    typer.echo(f"devscope projects remove {name} — not yet implemented")


@app.command("status")
def projects_status(name: str = typer.Argument(..., help="Project name to inspect.")) -> None:
    """Show expected vs actual state for a specific project."""
    # TODO: implement
    typer.echo(f"devscope projects status {name} — not yet implemented")


@app.command("auto-detect")
def projects_auto_detect() -> None:
    """Scan the filesystem for projects and suggest additions to the registry."""
    # TODO: implement
    typer.echo("devscope projects auto-detect — not yet implemented")


@app.command("edit")
def projects_edit(name: str = typer.Argument(..., help="Project name to edit.")) -> None:
    """Open the project entry in $EDITOR."""
    # TODO: implement
    typer.echo(f"devscope projects edit {name} — not yet implemented")


@app.command("validate")
def projects_validate() -> None:
    """Validate all registered projects against current machine state."""
    # TODO: implement
    typer.echo("devscope projects validate — not yet implemented")


@app.command("orphans")
def projects_orphans() -> None:
    """Show running services not claimed by any registered project."""
    # TODO: implement
    typer.echo("devscope projects orphans — not yet implemented")
