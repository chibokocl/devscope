<a name="readme-top"></a>

<!-- SHIELDS -->
<div align="center">

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![PyPI version][pypi-shield]][pypi-url]
[![Python][python-shield]][python-url]

</div>

<!-- PROJECT LOGO & HEADER -->
<br />
<div align="center">
  <a href="https://github.com/chibokocl/devscope">
    <img src="https://img.shields.io/badge/devscope-0F3460?style=for-the-badge&logoColor=00B4D8&labelColor=1A1A2E" alt="devscope" height="60">
  </a>

  <h3 align="center">devscope</h3>

  <p align="center">
    <strong>One command. Complete visibility. Your entire local dev environment — instantly.</strong>
    <br />
    Inventory, conflict detection, database management, and project registry for developers
    juggling many concurrent projects, Docker containers, Postgres instances, and MCP servers.
    <br />
    <br />
    <a href="https://github.com/chibokocl/devscope/blob/main/docs/"><strong>Explore the docs »</strong></a>
    &nbsp;·&nbsp;
    <a href="https://github.com/chibokocl/devscope/issues/new?labels=bug&template=bug-report.md">Report Bug</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/chibokocl/devscope/issues/new?labels=enhancement&template=feature-request.md">Request Feature</a>
  </p>
</div>

---

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#the-problem">The Problem</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li><a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
      <ul>
        <li><a href="#devscope-scan">devscope scan</a></li>
        <li><a href="#devscope-conflicts">devscope conflicts</a></li>
        <li><a href="#devscope-db">devscope db</a></li>
        <li><a href="#devscope-projects">devscope projects</a></li>
        <li><a href="#devscope-dashboard">devscope dashboard</a></li>
      </ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

---

<!-- ABOUT THE PROJECT -->
## About The Project

```
$ devscope scan

┌─────────────────────────── POSTGRES ──────────────────────────────────┐
│  ● local (brew)       5432   healthy    v16.2    /usr/local/var/...   │
│  ● openclaw_db        5433   healthy    docker   openclaw-postgres    │
│  ● myapi_dev          5434   healthy    docker   myapi-postgres       │
└────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────── DOCKER ────────────────────────────────────┐
│  ● openclaw-api       running   3000→3000   2h 14m   openclaw-net    │
│  ● myapi-backend      running   8000→8000   45m      myapi-net       │
│  ○ old-project-db     exited    —           14d ago  —  (orphan ⚠)   │
└────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────── PORTS ─────────────────────────────────────┐
│  5432  postgres (local)        8080  node (openclaw-api)              │
│  5433  docker/postgres         3000  python (fastapi-dev)             │
│  7000  mcp-server (openclaw)   8000  python (myapi-backend)           │
└────────────────────────────────────────────────────────────────────────┘
  3 databases  ·  2 running containers  ·  1 orphan  ·  6 ports in use
```

**devscope** is a CLI tool and PyPI-distributable Python package that gives developers a complete, real-time picture of their local development environment — across all projects, databases, Docker containers, running services, and port assignments — from a single terminal command.

It is built on the **Infrastructure as Code** principle of *"defining everything as code"* — applied to your local machine rather than the cloud. Just as IaC makes cloud infrastructure observable and reproducible, devscope makes your **local dev stack observable and manageable.**

### The Problem

If you're working across multiple projects simultaneously — each with its own Docker containers, Postgres databases, MCP servers, and port requirements — you've likely hit these pain points:

- `Error: address already in use` — and no idea what's on port 5432
- Multiple Postgres instances (local Homebrew + several Docker containers) with zero unified view
- Orphaned containers and volumes from old projects eating memory and disk
- MCP server configs silently pointing to dead ports
- Duplicate database names across projects causing confusion
- No way to see everything running, and which project owns what

devscope solves all of this in one command.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

### Built With

[![Python][python-shield]][python-url]
[![Typer][typer-shield]][typer-url]
[![Rich][rich-shield]][rich-url]
[![Textual][textual-shield]][textual-url]
[![Docker SDK][docker-shield]][docker-url]
[![Pydantic][pydantic-shield]][pydantic-url]
[![PostgreSQL][postgres-shield]][postgres-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

- **Python 3.11+**
- **macOS** (primary support) or **Linux**
- **Docker Desktop** installed and running *(optional — devscope degrades gracefully if Docker is not available)*
- **PostgreSQL** client tools (`psql`) for `devscope db connect`

Check your Python version:
```sh
python3 --version
# Python 3.11.x or higher required
```

### Installation

**Recommended — install globally with `pipx`** *(isolated, no dependency conflicts)*:

```sh
pipx install devscope
```

**Standard install via pip:**

```sh
pip install devscope
```

**Verify the installation:**

```sh
devscope --version
devscope --help
```

**Development install from source:**

```sh
# 1. Clone the repo
git clone https://github.com/chibokocl/devscope.git
cd devscope

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Sync dependencies and install in editable mode
uv sync
uv run devscope --help
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- USAGE -->
## Usage

### `devscope scan`

Complete inventory of your local dev environment — Postgres instances, Docker containers, occupied ports, MCP servers, and running processes. Color-coded by health status.

```sh
# Full scan — all resource types
devscope scan

# Filter to a specific resource type
devscope scan --postgres
devscope scan --docker
devscope scan --ports

# Machine-readable output for scripting
devscope scan --json
```

---

### `devscope conflicts`

Proactive conflict detection — finds problems **before** they cause errors.

```sh
# Run all conflict checks
devscope conflicts

# Filter by type
devscope conflicts --ports
devscope conflicts --docker

# Machine-readable output
devscope conflicts --json
```

**Example output:**

```
🔴 CRITICAL  Port 5432 claimed by both local postgres and container openclaw-postgres
🟡 WARNING   Container old-project-db (exited 14d ago) is an orphan — not claimed by any project
🔵 INFO      .env in ~/projects/myapi has DATABASE_URL pointing to port 5435 — nothing is listening there
```

---

### `devscope db`

Unified view of every database on your machine — local Homebrew Postgres and every Docker-hosted instance — in one table.

```sh
# List all databases across all Postgres instances
devscope db list

# Detailed stats for a specific database
devscope db info openclaw_db

# Open an interactive psql session
devscope db connect openclaw_db
```

**Example `devscope db list` output:**

```
 Database          Engine      Host        Port   Size     Tables   Project
 ───────────────── ─────────── ─────────── ────── ──────── ──────── ─────────────
 openclaw_db       postgres    localhost   5433   142 MB   18       openclaw
 myapi_dev         postgres    localhost   5434   38 MB    7        myapi
 postgres          postgres    localhost   5432   8 MB     —        (system)
 old_data          postgres    localhost   5432   204 MB   31       ⚠ unregistered
```

---

### `devscope projects`

The **project registry** — define your local dev stack as code in `~/.devscope/projects.yaml`. devscope tracks expected vs actual state for every registered project.

```sh
# List all registered projects with current health
devscope projects list

# Register a new project
devscope projects add openclaw

# Check a specific project's expected vs actual state
devscope projects status openclaw

# Auto-detect projects from the filesystem
# (scans docker-compose.yml, .env, pyproject.toml, package.json)
devscope projects auto-detect

# Validate all registered projects against current machine state
devscope projects validate
```

**Example `~/.devscope/projects.yaml` entry:**

```yaml
projects:
  openclaw:
    description: "AI-powered legal document tool"
    path: ~/projects/openclaw
    ports:
      - 3000   # Next.js frontend
      - 8000   # FastAPI backend
    databases:
      - name: openclaw_db
        engine: postgres
        port: 5433
        docker_container: openclaw-postgres
    docker_containers:
      - openclaw-api
      - openclaw-postgres
    mcp_servers:
      - port: 7000
    tags: [active, ai, legal]
```

---

### `devscope dashboard`

> **Available in v0.4.0**

A live, auto-refreshing full-screen terminal UI built with [Textual](https://github.com/Textualize/textual). Like `htop` — but for your entire dev environment.

```sh
devscope dashboard
```

Shows all projects, running services, active conflicts, and databases — updated every 5 seconds. Navigate with keyboard shortcuts: `r` refresh · `q` quit · `Enter` drill in · `f` filter · `Tab` cycle panels.

---

*For the full command reference, please refer to the [Documentation](https://github.com/chibokocl/devscope/blob/main/docs/).*

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- ROADMAP -->
## Roadmap

| Version | Name | What Ships |
|---------|------|------------|
| **v0.1.0** | Foundations | `scan` · `conflicts` · `db` · `projects` — full visibility in one install |
| v0.2.0 | Management | `db backup/restore` · `conflicts --fix` — manage DBs and resolve conflicts interactively |
| v0.3.0 | Lifecycle | `devscope up/down/restart` — start and stop entire project stacks cleanly |
| v0.4.0 | Live Dashboard | `devscope dashboard` (Textual TUI) — persistent real-time overview |
| v0.5.0 | Export & Publish | `devscope export` JSON/YAML/Markdown · official PyPI public launch |

See the [open issues](https://github.com/chibokocl/devscope/issues) for a full list of proposed features and known issues.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, build, and grow. Any contributions you make are **greatly appreciated**.

If you have a suggestion, please fork the repo and open a pull request. You can also open an issue with the tag `enhancement`. And if devscope has saved you time, give the project a ⭐ — it really helps!

1. Fork the Project
2. Create your Feature Branch
   ```sh
   git checkout -b feature/AmazingFeature
   ```
3. Commit your Changes
   ```sh
   git commit -m 'Add some AmazingFeature'
   ```
4. Push to the Branch
   ```sh
   git push origin feature/AmazingFeature
   ```
5. Open a Pull Request

### Development Setup

```sh
git clone https://github.com/chibokocl/devscope.git
cd devscope
uv sync --all-extras --dev
uv run pytest                   # run tests
uv run ruff check src/          # lint
uv run mypy src/                # type check
uv run devscope scan            # try it live
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- LICENSE -->
## License

Distributed under the MIT License. See [`LICENSE`](https://github.com/chibokocl/devscope/blob/main/LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- CONTACT -->
## Contact

**chibokocl** — [@chibokocl](https://github.com/chibokocl)

Project Link: [https://github.com/chibokocl/devscope](https://github.com/chibokocl/devscope)

PyPI: [https://pypi.org/project/devscope](https://pypi.org/project/devscope)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Resources and inspiration that shaped devscope:

- [Infrastructure as Code, 3rd Edition — Kief Morris (O'Reilly)](https://www.oreilly.com/library/view/infrastructure-as-code/9781098150358/) — the foundational philosophy behind treating local dev environments as manageable, observable infrastructure
- [Typer](https://typer.tiangolo.com/) — the CLI framework that makes building well-typed, self-documenting commands a pleasure
- [Rich](https://github.com/Textualize/rich) — for making terminal output genuinely beautiful
- [Textual](https://github.com/Textualize/textual) — for the live dashboard TUI
- [Docker Python SDK](https://docker-py.readthedocs.io/) — for clean programmatic access to the Docker Engine API
- [Pydantic](https://docs.pydantic.dev/) — for rock-solid config schema validation
- [uv](https://docs.astral.sh/uv/) — the fastest Python package manager; a genuine step forward for the ecosystem
- [shields.io](https://shields.io) — for the README badges
- [Best-README-Template](https://github.com/othneildrew/Best-README-Template) — the template this README is built on

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/chibokocl/devscope.svg?style=for-the-badge
[contributors-url]: https://github.com/chibokocl/devscope/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/chibokocl/devscope.svg?style=for-the-badge
[forks-url]: https://github.com/chibokocl/devscope/network/members

[stars-shield]: https://img.shields.io/github/stars/chibokocl/devscope.svg?style=for-the-badge
[stars-url]: https://github.com/chibokocl/devscope/stargazers

[issues-shield]: https://img.shields.io/github/issues/chibokocl/devscope.svg?style=for-the-badge
[issues-url]: https://github.com/chibokocl/devscope/issues

[license-shield]: https://img.shields.io/github/license/chibokocl/devscope.svg?style=for-the-badge
[license-url]: https://github.com/chibokocl/devscope/blob/main/LICENSE

[pypi-shield]: https://img.shields.io/pypi/v/devscope?style=for-the-badge&color=0F3460
[pypi-url]: https://pypi.org/project/devscope

[python-shield]: https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/

[typer-shield]: https://img.shields.io/badge/Typer-009485?style=for-the-badge&logo=fastapi&logoColor=white
[typer-url]: https://typer.tiangolo.com/

[rich-shield]: https://img.shields.io/badge/Rich-Terminal-1A1A2E?style=for-the-badge
[rich-url]: https://github.com/Textualize/rich

[textual-shield]: https://img.shields.io/badge/Textual-TUI-533483?style=for-the-badge
[textual-url]: https://github.com/Textualize/textual

[docker-shield]: https://img.shields.io/badge/Docker-SDK-2496ED?style=for-the-badge&logo=docker&logoColor=white
[docker-url]: https://docker-py.readthedocs.io/

[pydantic-shield]: https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge
[pydantic-url]: https://docs.pydantic.dev/

[postgres-shield]: https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white
[postgres-url]: https://www.postgresql.org/