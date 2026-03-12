"""Pydantic models for ~/.devscope/projects.yaml."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatabaseEntry(BaseModel):
    name: str
    engine: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    docker_container: str | None = None


class MCPServerEntry(BaseModel):
    port: int
    config: str | None = None


class ProjectEntry(BaseModel):
    description: str = ""
    path: str
    ports: list[int] = Field(default_factory=list)
    databases: list[DatabaseEntry] = Field(default_factory=list)
    docker_containers: list[str] = Field(default_factory=list)
    mcp_servers: list[MCPServerEntry] = Field(default_factory=list)
    env_file: str | None = None
    tags: list[str] = Field(default_factory=list)


class ProjectsFile(BaseModel):
    projects: dict[str, ProjectEntry] = Field(default_factory=dict)
