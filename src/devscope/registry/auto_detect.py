"""Auto-discover projects from the filesystem."""

from __future__ import annotations

from pathlib import Path

from devscope.registry.schema import ProjectEntry

DEFAULT_SCAN_PATHS = [
    Path.home() / "projects",
    Path.home() / "code",
    Path.home() / "dev",
]

# Heuristic markers — presence of any of these triggers project discovery
PROJECT_MARKERS = [
    "docker-compose.yml",
    "compose.yaml",
    "pyproject.toml",
    "package.json",
    ".env",
]


def discover_projects(scan_paths: list[Path] | None = None) -> dict[str, ProjectEntry]:
    """
    Walk *scan_paths* (or DEFAULT_SCAN_PATHS) and return candidate projects.

    Each candidate is a directory that contains at least one PROJECT_MARKER.
    """
    # TODO: implement full heuristics from spec §4.11
    results: dict[str, ProjectEntry] = {}
    paths = scan_paths or DEFAULT_SCAN_PATHS

    for base in paths:
        if not base.exists():
            continue
        for candidate in base.iterdir():
            if not candidate.is_dir():
                continue
            if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
                results[candidate.name] = ProjectEntry(path=str(candidate))

    return results
