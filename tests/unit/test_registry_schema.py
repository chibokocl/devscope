"""Unit tests for the Pydantic project registry schema."""

from __future__ import annotations

from devscope.registry.schema import DatabaseEntry, ProjectEntry, ProjectsFile


def test_empty_projects_file() -> None:
    registry = ProjectsFile()
    assert registry.projects == {}


def test_project_entry_defaults() -> None:
    entry = ProjectEntry(path="~/projects/myapp")
    assert entry.ports == []
    assert entry.docker_containers == []
    assert entry.tags == []


def test_database_entry_defaults() -> None:
    db = DatabaseEntry(name="myapp_db")
    assert db.engine == "postgres"
    assert db.host == "localhost"
    assert db.port == 5432
