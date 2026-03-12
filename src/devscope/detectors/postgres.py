"""Detect local (Homebrew / pg_ctl) and Docker-hosted Postgres instances."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field

import psutil

from devscope.utils.subprocess import run as safe_run


@dataclass
class PostgresInstance:
    source: str          # "local" | "docker"
    port: int
    version: str | None = None
    data_dir: str | None = None
    container_name: str | None = None
    is_reachable: bool = False
    databases: list[str] = field(default_factory=list)


def _check_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _parse_postgres_version(pid: int) -> str | None:
    """Try to read the Postgres version string from the postmaster process."""
    output = safe_run(["postgres", "--version"], timeout=3)
    if output:
        # e.g. "postgres (PostgreSQL) 16.2"
        parts = output.split()
        return parts[-1] if parts else None
    return None


def detect_local_postgres() -> list[PostgresInstance]:
    """Return Homebrew/pg_ctl Postgres instances found via process inspection."""
    instances: list[PostgresInstance] = []
    seen_ports: set[int] = set()

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info["name"] or "").lower()
            if "postgres" not in name:
                continue
            cmdline = proc.info["cmdline"] or []
            # Only consider the postmaster (primary) process
            if not any("postgres" in str(a).lower() for a in cmdline[:2]):
                continue

            port = 5432
            data_dir: str | None = None
            for i, arg in enumerate(cmdline):
                if arg == "-p" and i + 1 < len(cmdline):
                    try:
                        port = int(cmdline[i + 1])
                    except ValueError:
                        pass
                elif arg.startswith("-D") and len(arg) > 2:
                    data_dir = arg[2:]
                elif arg == "-D" and i + 1 < len(cmdline):
                    data_dir = cmdline[i + 1]

            if port in seen_ports:
                continue
            seen_ports.add(port)

            instances.append(PostgresInstance(
                source="local",
                port=port,
                data_dir=data_dir,
                is_reachable=_check_reachable(port),
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return instances


def detect_docker_postgres() -> list[PostgresInstance]:
    """Return Postgres containers found via the Docker SDK."""
    try:
        import docker  # type: ignore[import-untyped]
        client = docker.from_env()
    except Exception:
        return []

    instances: list[PostgresInstance] = []
    try:
        for container in client.containers.list():
            image_tags = " ".join(container.image.tags or []).lower()
            image_id = (container.image.short_id or "").lower()
            if "postgres" not in image_tags and "postgres" not in image_id:
                # Check the image name from container attrs
                image_name = container.attrs.get("Config", {}).get("Image", "").lower()
                if "postgres" not in image_name:
                    continue

            port: int | None = None
            for container_port, host_bindings in (container.ports or {}).items():
                if "5432" in container_port and host_bindings:
                    try:
                        port = int(host_bindings[0]["HostPort"])
                    except (KeyError, ValueError):
                        pass
                    break

            if port is None:
                continue

            instances.append(PostgresInstance(
                source="docker",
                port=port,
                container_name=container.name,
                is_reachable=_check_reachable(port),
            ))
    except Exception:
        pass

    return instances


def detect_all() -> list[PostgresInstance]:
    """Aggregate local and Docker Postgres instances."""
    return detect_local_postgres() + detect_docker_postgres()
