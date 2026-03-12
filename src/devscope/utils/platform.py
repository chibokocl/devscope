"""macOS / Linux branching helpers."""

from __future__ import annotations

import platform
import sys


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def platform_name() -> str:
    return platform.system()
