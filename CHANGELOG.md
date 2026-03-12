# Changelog

All notable changes to **devscope** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Initial project scaffold: src layout, pyproject.toml, venv, .env, .gitignore
- Stub modules: `scan`, `conflicts`, `db`, `projects`, `dashboard`
- Stub detectors: `postgres`, `docker`, `ports`, `processes`, `mcp`
- Pydantic registry schema and YAML store
- Rich output helpers: `theme`, `tables`, `panels`
- CLI entry point wired via `typer`
- Unit and integration test stubs

---

## [0.1.0] — planned

### Added
- `devscope scan` — full inventory: Postgres, Docker, ports, MCP, processes
- `devscope conflicts` — port conflicts, orphaned containers, dead MCP targets, duplicate DBs
- `devscope db list` — all DBs across local + Docker Postgres with metadata
- `devscope db connect` — open psql session to any detected database
- `devscope db info` — detailed DB stats: tables, size, connections
- `devscope projects list` — show registry + actual vs expected state
- `devscope projects add` — register a project interactively
- `devscope projects auto-detect` — scan filesystem and suggest projects
- `devscope projects status` — per-project health check
