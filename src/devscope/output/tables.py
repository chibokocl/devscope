"""Rich table formatters for scan/conflicts/db/projects output."""

from __future__ import annotations

from rich.table import Table

from devscope.output.theme import TABLE_HEADER


def make_table(*columns: str, title: str = "") -> Table:
    """Return a styled Rich Table with the given column headers."""
    table = Table(title=title, header_style=TABLE_HEADER, show_lines=False)
    for col in columns:
        table.add_column(col)
    return table
