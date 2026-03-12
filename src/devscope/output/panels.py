"""Rich panel and layout helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from devscope.output.theme import PANEL_BORDER

console = Console()


def render_panel(content: str, title: str) -> None:
    """Print a titled Rich panel to the terminal."""
    console.print(Panel(content, title=title, border_style=PANEL_BORDER))
