"""Auto-discover projects from the filesystem."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from devscope.registry.schema import DatabaseEntry, MCPServerEntry, ProjectEntry

# Scan home dir root first, then common subdirs
DEFAULT_SCAN_PATHS = [
    Path.home(),
    Path.home() / "projects",
    Path.home() / "code",
    Path.home() / "dev",
    Path.home() / "work",
    Path.home() / "src",
]

PROJECT_MARKERS = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yaml",
    "compose.yml",
    "pyproject.toml",
    "package.json",
    ".env",
    "Makefile",
    "go.mod",
    "Cargo.toml",
]

# Directories to always skip when scanning
_SKIP_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt", "target", ".cargo",
    ".cache", "Library", "Applications", "Music", "Movies", "Pictures",
    "Downloads", "Desktop", "Documents", ".Trash", ".local", ".config",
    ".npm", ".nvm", ".pyenv", ".rbenv", ".asdf", ".oh-my-zsh",
    "go", "snap", ".docker", ".kube", ".aws", ".gcloud",
}

# Suffix patterns that identify frontend / backend halves of a pair
_FE_SUFFIXES = ("-fe", "-frontend", "-ui", "-web", "-client", "-app")
_BE_SUFFIXES = ("-api", "-backend", "-server", "-service", "-be")


def _detect_project_type(candidate: Path) -> str:
    """Infer project type from directory contents."""
    # Next.js
    if (candidate / "next.config.js").exists() or (candidate / "next.config.ts").exists():
        return "nextjs"
    # Vue / Nuxt
    if (candidate / "nuxt.config.ts").exists() or (candidate / "nuxt.config.js").exists():
        return "nuxt"
    # React (CRA / Vite)
    pkg = candidate / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                return "nextjs"
            if "nuxt" in deps:
                return "nuxt"
            if "react" in deps:
                return "react"
            if "vue" in deps:
                return "vue"
            if "svelte" in deps:
                return "svelte"
            if "astro" in deps:
                return "astro"
            # Pure Node
            return "node"
        except Exception:
            pass

    # Python
    if (candidate / "pyproject.toml").exists() or (candidate / "setup.py").exists():
        try:
            text = (candidate / "pyproject.toml").read_text() if (candidate / "pyproject.toml").exists() else ""
            if "fastapi" in text.lower() or "uvicorn" in text.lower():
                return "fastapi"
            if "django" in text.lower():
                return "django"
            if "flask" in text.lower():
                return "flask"
        except Exception:
            pass
        return "python"

    if (candidate / "go.mod").exists():
        return "go"
    if (candidate / "Cargo.toml").exists():
        return "rust"
    if (candidate / "docker-compose.yml").exists() or (candidate / "compose.yaml").exists():
        return "docker"

    return "unknown"


def _parse_compose(path: Path, entry: ProjectEntry) -> None:
    """Extract services, ports, volumes from a docker-compose file."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
        for svc_name, svc in (data.get("services") or {}).items():
            if svc_name not in entry.docker_containers:
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
                    if not any(d.name == svc_name for d in entry.databases):
                        entry.databases.append(DatabaseEntry(
                            name=svc_name,
                            engine=engine,
                            port=db_port,
                            docker_container=svc_name,
                        ))
                    break
    except Exception:
        pass


def _parse_package_json(path: Path, entry: ProjectEntry) -> None:
    """Extract port hints and description from package.json."""
    try:
        data = json.loads(path.read_text())

        if not entry.description:
            entry.description = data.get("description", "")

        scripts = data.get("scripts", {})
        all_scripts = " ".join(scripts.values())

        # Look for explicit PORT=NNNN in scripts
        for m in re.finditer(r"\bPORT=(\d{2,5})\b", all_scripts):
            p = int(m.group(1))
            if p not in entry.ports:
                entry.ports.append(p)

        # next dev -p NNNN  /  vite --port NNNN  /  --port=NNNN
        for m in re.finditer(r"(?:--port[= ]|:)(\d{2,5})\b", all_scripts):
            p = int(m.group(1))
            if p not in entry.ports:
                entry.ports.append(p)

        # Infer defaults from framework presence if no port found
        if not entry.ports:
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                entry.ports.append(3000)
            elif "vite" in deps:
                entry.ports.append(5173)
            elif "react-scripts" in deps:
                entry.ports.append(3000)
            elif "vue" in deps or "@vue/cli-service" in deps:
                entry.ports.append(8080)
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

            # PORT / APP_PORT / SERVER_PORT / NEXT_PUBLIC_PORT / VITE_PORT
            if re.fullmatch(r"(?:APP_|SERVER_|NEXT_PUBLIC_|VITE_)?PORT", key):
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
                    if not any(ms.port == p for ms in entry.mcp_servers):
                        entry.mcp_servers.append(MCPServerEntry(port=p))
                except ValueError:
                    pass
    except Exception:
        pass


def _pair_name(name: str) -> str | None:
    """
    If *name* has a frontend/backend suffix, return the base name (pairable root).
    E.g. "alpha-skyport-fe" → "alpha-skyport", "my-api" → "my" (no, too short — None).
    """
    for suffix in _FE_SUFFIXES + _BE_SUFFIXES:
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            if len(base) >= 2:
                return base
    return None


def discover_projects(scan_paths: list[Path] | None = None) -> dict[str, ProjectEntry]:
    """
    Walk *scan_paths* (or DEFAULT_SCAN_PATHS) and return candidate projects.

    Scans one level deep inside each path. When scanning the home directory
    itself it skips well-known non-project dirs to avoid false positives.

    Heuristics applied:
    - docker-compose.yml / compose.yaml → services, ports, DB containers
    - package.json → framework detection, port hints from scripts
    - .env → DATABASE_URL, PORT, MCP_*_PORT
    - pyproject.toml → description, framework tag
    - Naming patterns (-fe/-frontend/-api/-backend) → pair tagging
    """
    results: dict[str, ProjectEntry] = {}
    paths = scan_paths or DEFAULT_SCAN_PATHS

    seen_paths: set[Path] = set()

    for base in paths:
        if not base.exists():
            continue

        is_home = base == Path.home()

        for candidate in base.iterdir():
            if not candidate.is_dir():
                continue

            # Skip hidden dirs and well-known noise dirs when scanning home
            if is_home and (candidate.name.startswith(".") or candidate.name in _SKIP_DIRS):
                continue

            # Skip if we've already seen this path from a different scan root
            resolved = candidate.resolve()
            if resolved in seen_paths:
                continue

            if not any((candidate / m).exists() for m in PROJECT_MARKERS):
                continue

            seen_paths.add(resolved)

            proj_type = _detect_project_type(candidate)
            entry = ProjectEntry(path=str(candidate))

            # Tag with detected type
            if proj_type != "unknown":
                entry.tags.append(proj_type)

            # Tag frontend/backend pair role
            base_name = _pair_name(candidate.name)
            name_lower = candidate.name.lower()
            if any(name_lower.endswith(s) for s in _FE_SUFFIXES):
                entry.tags.append("frontend")
                if base_name:
                    entry.tags.append(f"pair:{base_name}")
            elif any(name_lower.endswith(s) for s in _BE_SUFFIXES):
                entry.tags.append("backend")
                if base_name:
                    entry.tags.append(f"pair:{base_name}")

            # docker-compose
            for compose_file in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"):
                compose_path = candidate / compose_file
                if compose_path.exists():
                    _parse_compose(compose_path, entry)
                    break

            # package.json
            pkg_path = candidate / "package.json"
            if pkg_path.exists():
                _parse_package_json(pkg_path, entry)

            # .env
            for env_name in (".env", ".env.local", ".env.development"):
                env_path = candidate / env_name
                if env_path.exists():
                    entry.env_file = env_name
                    _parse_env(env_path, entry)
                    break

            # description + tags from pyproject.toml
            pyproject = candidate / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib  # Python 3.11+
                    data = tomllib.loads(pyproject.read_text())
                    proj_data = data.get("project", {})
                    if not entry.description:
                        entry.description = proj_data.get("description", "")
                except Exception:
                    pass

            results[candidate.name] = entry

    return results
