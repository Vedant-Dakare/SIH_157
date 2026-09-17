"""Repository-relative paths that remain stable from any working directory."""

from __future__ import annotations

import os
from pathlib import Path


def repository_root() -> Path:
    """Return the repository root, with an explicit override for deployments."""
    configured = os.environ.get("SATSA_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path(__file__).resolve().parents[3]


ROOT = repository_root()


def from_root(*parts: str) -> Path:
    """Build an absolute path below the repository root."""
    return ROOT.joinpath(*parts)