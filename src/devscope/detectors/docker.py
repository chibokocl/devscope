"""Docker SDK integration — containers, volumes, networks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


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


def _get_client():  # type: ignore[return]
    import docker  # type: ignore[import-untyped]
    return docker.from_env()


def is_docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        _get_client().ping()
        return True
    except Exception:
        return False


def get_containers() -> list[ContainerInfo]:
    """Return all containers (running + stopped)."""
    try:
        client = _get_client()
    except Exception:
        return []

    results: list[ContainerInfo] = []
    try:
        for c in client.containers.list(all=True):
            # Port mapping: container_port_str -> host_port int
            ports: dict[str, int] = {}
            for container_port, host_bindings in (c.ports or {}).items():
                if host_bindings:
                    try:
                        ports[container_port] = int(host_bindings[0]["HostPort"])
                    except (KeyError, ValueError):
                        pass

            # Uptime for running containers
            uptime: int | None = None
            if c.status == "running":
                started_at = c.attrs.get("State", {}).get("StartedAt", "")
                if started_at:
                    try:
                        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        uptime = int((datetime.now(timezone.utc) - dt).total_seconds())
                    except (ValueError, TypeError):
                        pass

            networks = list((c.attrs.get("NetworkSettings", {}).get("Networks") or {}).keys())
            project_label = (c.labels or {}).get("com.docker.compose.project")
            image_str = ", ".join(c.image.tags) if c.image.tags else c.image.short_id or ""

            results.append(ContainerInfo(
                name=c.name,
                image=image_str,
                status=c.status,
                ports=ports,
                networks=networks,
                uptime_seconds=uptime,
                project_label=project_label,
            ))
    except Exception:
        pass

    return results


def get_volumes() -> list[VolumeInfo]:
    """Return all named Docker volumes."""
    try:
        client = _get_client()
    except Exception:
        return []

    # Build volume → container name mapping
    vol_containers: dict[str, list[str]] = {}
    try:
        for c in client.containers.list(all=True):
            for mount in c.attrs.get("Mounts", []):
                if mount.get("Type") == "volume":
                    vol_name = mount.get("Name", "")
                    vol_containers.setdefault(vol_name, []).append(c.name)
    except Exception:
        pass

    results: list[VolumeInfo] = []
    try:
        for v in client.volumes.list():
            results.append(VolumeInfo(
                name=v.name,
                containers=vol_containers.get(v.name, []),
            ))
    except Exception:
        pass

    return results


def get_networks() -> list[NetworkInfo]:
    """Return all custom Docker networks (excludes bridge/host/none)."""
    try:
        client = _get_client()
    except Exception:
        return []

    _SKIP = {"bridge", "host", "none"}
    results: list[NetworkInfo] = []
    try:
        for net in client.networks.list():
            if net.name in _SKIP:
                continue
            container_ids = list((net.attrs.get("Containers") or {}).keys())
            container_names: list[str] = []
            for cid in container_ids:
                try:
                    container_names.append(client.containers.get(cid).name)
                except Exception:
                    container_names.append(cid[:12])
            results.append(NetworkInfo(name=net.name, containers=container_names))
    except Exception:
        pass

    return results
