"""Safe subprocess wrappers with graceful error handling."""

from __future__ import annotations

import subprocess
from typing import Optional


def run(
    cmd: list[str],
    timeout: int = 10,
    capture: bool = True,
) -> Optional[str]:
    """
    Run *cmd* and return stdout as a string, or None on failure.

    Never raises — errors are swallowed and returned as None so callers
    can degrade gracefully (design principle P2).
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() if capture else None
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return None
