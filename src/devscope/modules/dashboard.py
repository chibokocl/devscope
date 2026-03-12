"""Module 5 — devscope dashboard (v0.4+).

Live, auto-refreshing Textual TUI providing a persistent overview of the
entire dev environment.  Ships in v0.4.0 — stub only in v0.1.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Live TUI dashboard (ships in v0.4.0).")


@app.callback(invoke_without_command=True)
def dashboard() -> None:
    """Launch the live Textual dashboard (v0.4+)."""
    typer.echo("devscope dashboard — coming in v0.4.0")
