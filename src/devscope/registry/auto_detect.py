"""Auto-discover projects from the filesystem."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from devscope.registry.schema import DatabaseEntry, MCPServerEntry, ProjectEntry

DEFAULT_SCAN_PATHS = [
    Path.home() / "projects",
    Path.home() / "code",
    Path.home() / "dev",
]

PROJECT_MARKERS = [
    "docker-compose.yml",
    "compose.yaml",
    "pyproject.toml",
    "package.json",
    ".env",
]


def _parse_compose(path: Path, entry: ProjectEntry) -> None:
    """Extract services, ports, volumes from a docker-compose file."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
        for svc_name, svc in (data.get("services") or {}).items():
            entry.docker_containers.append(svc_name)
            for port_spec in svc.get("ports") or []:
                spec = str(port_spec)
                # Formats: "3000:3000", "127.0.0.1:3000:3000", "3000"
                parts = spec.split(":")
                try:
                    host_port = int(parts[-2]) if len(parts) >= 2 else int(parts[0])
                    if host_port not in entry.ports:
                        entry.ports.append(host_port)
                except (ValueError, IndexError):
                    pass
            # Detect DB containers
            image = str(svc.get("image") or "").lower()
            for engine in ("postgres", "mysql", "mongo", "redis"):
                if engine in image:
                    db_port = {"postgres": 5432, "mysql": 3306, "mongo": 27017, "redis": 6379}[engine]
                    entry.databases.append(DatabaseEntry(
                        name=svc_name,
                        engine=engine,
                        port=db_port,
                        docker_container=svc_name,
                    ))
                    break
    except Exception:
        pass


def _parse_env(path: Path, entry: ProjectEntry) -> None:
    """Extract DATABASE_URL, PORT, REDIS_URL etc. from a .env file."""
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            # PORT / APP_PORT / SERVER_PORT
            if re.fullmatch(r"(APP_|SERVER_)?PORT", key):
                try:
                    p = int(val)
                    if p not in entry.ports:
                        entry.ports.append(p)
                except ValueError:
                    pass

            # DATABASE_URL — postgresql://user:pass@host:port/dbname
            if key == "DATABASE_URL" and val:
                m = re.search(r"@[^:]+:(\d+)/(\w+)", val)
                if m:
                    db_port = int(m.group(1))
                    db_name = m.group(2)
                    if not any(d.name == db_name for d in entry.databases):
                        entry.databases.append(DatabaseEntry(
                            name=db_name,
                            engine="postgres",
                            port=db_port,
                        ))

            # MCP ports
            if "MCP" in key.upper() and "PORT" in key.upper():
                try:
                    p = int(val)
                    if not any(m.port == p for m in entry.mcp_servers):
                        entry.mcp_servers.append(MCPServerEntry(port=p))
                except ValueError:
                    pass
    except Exception:
        pass


def discover_projects(scan_paths: list[Path] | None = None) -> dict[str, ProjectEntry]:
    """
    Walk *scan_paths* (or DEFAULT_SCAN_PATHS) and return candidate projects.

    Applies heuristics from spec §4.11:
    - docker-compose.yml / compose.yaml → extract services, ports, volumes
    - .env files → extract DATABASE_URL, PORT, REDIS_URL, MCP ports
    - pyproject.toml / package.json → infer project name and type
    """
    results: dict[str, ProjectEntry] = {}
    paths = scan_paths or DEFAULT_SCAN_PATHS

    for base in paths:
        if not base.exists():
            continue
        for candidate in base.iterdir():
            if not candidate.is_dir():
                continue
            if not any((candidate / m).exists() for m in PROJECT_MARKERS):
                continue

            entry = ProjectEntry(path=str(candidate))

            # docker-compose
            for compose_file in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"):
                compose_path = candidate / compose_file
                if compose_path.exists():
                    _parse_compose(compose_path, entry)
                    break

            # .env
            env_path = candidate / ".env"
            if env_path.exists():
                entry.env_file = ".env"
                _parse_env(env_path, entry)

            # description from pyproject.toml
            pyproject = candidate / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib  # Python 3.11+
                    data = tomllib.loads(pyproject.read_text())
                    desc = data.get("project", {}).get("description", "")
                    if desc:
                        entry.description = desc
                except Exception:
                    pass

            results[candidate.name] = entry

    return results
