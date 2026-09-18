"""Shared API dependencies: store/warehouse roots, token config, DuckDB access."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from satsa.paths import from_root

STORE_ROOT = from_root("data", "curated", "reports")
WAREHOUSE_ROOT = from_root("data", "warehouse")

API_CONFIG_PATH = from_root("configs", "api.yaml")


def load_api_config(path: str | Path = API_CONFIG_PATH) -> dict[str, Any]:
    """Token settings from configs/api.yaml with env overrides (disabled default)."""
    import yaml

    config: dict[str, Any] = {"token_enabled": False, "token": ""}
    target = Path(path)
    if target.exists():
        try:
            with target.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            config.update({k: data[k] for k in ("token_enabled", "token") if k in data})
        except Exception:
            pass
    if os.environ.get("SATSA_API_TOKEN_ENABLED", "").lower() in ("1", "true", "yes"):
        config["token_enabled"] = True
    if os.environ.get("SATSA_API_TOKEN"):
        config["token"] = os.environ["SATSA_API_TOKEN"]
        config["token_enabled"] = True
    return config


def check_token(headers: dict[str, str], config: dict[str, Any] | None = None) -> bool:
    """Static token check; passes when the gate is disabled."""
    config = config if config is not None else load_api_config()
    if not config.get("token_enabled"):
        return True
    lowered = {str(k).lower(): v for k, v in headers.items()}
    return str(lowered.get("x-api-token", "")) == str(config.get("token", "")) and bool(
        config.get("token")
    )


def get_store(run_id: str, root: str | Path | None = None) -> dict[str, Any] | None:
    """Load a run store, or None when the run is unknown."""
    path = Path(root or STORE_ROOT) / run_id / "run_store.json"
    if not path.exists():
        return None
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def known_runs(root: str | Path | None = None) -> list[str]:
    """Run ids with a materialised store on disk, sorted newest first."""
    base = Path(root or STORE_ROOT)
    if not base.exists():
        return []
    valid = [p.name for p in base.iterdir() if p.is_dir() and (p / "run_store.json").exists()]
    return sorted(valid, key=lambda name: (base / name / "run_store.json").stat().st_mtime, reverse=True)
