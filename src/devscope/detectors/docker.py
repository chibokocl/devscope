"""Docker SDK integration — containers, volumes, networks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContainerInfo:
    name: str
    image: str
    status: str          # "running" | "exited" | ...
    ports: dict[str, int] = field(default_factory=dict)
    networks: list[str] = field(default_factory=list)
    uptime_seconds: int | None = None
    project_label: str | None = None


@dataclass
class VolumeInfo:
    name: str
    size_bytes: int | None = None
    containers: list[str] = field(default_factory=list)


@dataclass
class NetworkInfo:
    name: str
    containers: list[str] = field(default_factory=list)


def is_docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    # TODO: implement
    return False


def get_containers() -> list[ContainerInfo]:
    """Return all containers (running + stopped)."""
    # TODO: implement using docker-py
    return []


def get_volumes() -> list[VolumeInfo]:
    """Return all named Docker volumes."""
    # TODO: implement
    return []


def get_networks() -> list[NetworkInfo]:
    """Return all custom Docker networks."""
    # TODO: implement
    return []
