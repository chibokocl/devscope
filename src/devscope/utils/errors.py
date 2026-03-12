"""Graceful error handling utilities."""

from __future__ import annotations


class DevScopeError(Exception):
    """Base exception for all devscope errors."""


class DockerUnavailableError(DevScopeError):
    """Raised when the Docker daemon is not reachable."""


class PostgresUnavailableError(DevScopeError):
    """Raised when a Postgres instance cannot be connected to."""


class RegistryNotFoundError(DevScopeError):
    """Raised when the project registry file is missing or unreadable."""
