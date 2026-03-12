"""Typer root app — command registration.

All sub-commands are imported from their respective modules and attached
to this app so that the `devscope` entry-point resolves everything from
one place.
"""

from __future__ import annotations

import typer

from devscope import __version__
from devscope.modules import conflicts, db, projects, scan

app = typer.Typer(
    name="devscope",
    help="Local dev environment inventory and management CLI.",
    add_completion=True,
    no_args_is_help=True,
)

# ── Sub-command groups ──────────────────────────────────────────────────────
app.add_typer(scan.app, name="scan")
app.add_typer(conflicts.app, name="conflicts")
app.add_typer(db.app, name="db")
app.add_typer(projects.app, name="projects")


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
) -> None:
    """devscope — see everything running on your machine, instantly."""
    if version:
        typer.echo(f"devscope {__version__}")
        raise typer.Exit()
