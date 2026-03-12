"""Read/write ~/.devscope/projects.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from devscope.registry.schema import ProjectsFile

DEVSCOPE_DIR = Path.home() / ".devscope"
PROJECTS_FILE = DEVSCOPE_DIR / "projects.yaml"


def ensure_devscope_dir() -> None:
    """Create ~/.devscope/ and subdirectories if they don't exist."""
    DEVSCOPE_DIR.mkdir(parents=True, exist_ok=True)
    (DEVSCOPE_DIR / "backups").mkdir(exist_ok=True)
    (DEVSCOPE_DIR / "logs").mkdir(exist_ok=True)


def load_projects() -> ProjectsFile:
    """Load the project registry; returns empty registry if file is absent."""
    ensure_devscope_dir()
    if not PROJECTS_FILE.exists():
        return ProjectsFile()
    raw = yaml.safe_load(PROJECTS_FILE.read_text()) or {}
    return ProjectsFile.model_validate(raw)


def save_projects(registry: ProjectsFile) -> None:
    """Persist the project registry to disk."""
    ensure_devscope_dir()
    PROJECTS_FILE.write_text(
        yaml.dump(registry.model_dump(), default_flow_style=False, sort_keys=False)
    )
