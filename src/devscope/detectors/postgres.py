"""Detect local (Homebrew / pg_ctl) and Docker-hosted Postgres instances."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PostgresInstance:
    source: str          # "local" | "docker"
    port: int
    version: str | None = None
    data_dir: str | None = None
    container_name: str | None = None
    is_reachable: bool = False
    databases: list[str] = field(default_factory=list)


def detect_local_postgres() -> list[PostgresInstance]:
    """Return Homebrew/pg_ctl Postgres instances found via process inspection."""
    # TODO: implement using psutil + subprocess
    return []


def detect_docker_postgres() -> list[PostgresInstance]:
    """Return Postgres containers found via the Docker SDK."""
    # TODO: implement using docker-py
    return []


def detect_all() -> list[PostgresInstance]:
    """Aggregate local and Docker Postgres instances."""
    return detect_local_postgres() + detect_docker_postgres()
