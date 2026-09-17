"""Application settings loaded from configs/*.yaml with air-gap guards."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from satsa.errors import SatsaConfigError
from satsa.paths import from_root

_DEFAULT_SALT = "change-me-in-production-please"
_DEFAULT_MANIFEST_KEY = "change-me-in-production-please"
_ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
_URL_HOST_RE = re.compile(r"https?://([^/:?\s#]+)")


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file returning an empty dict when the file is absent."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _iter_string_leaves(value: Any) -> Any:
    """Yield every string leaf in a nested structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_string_leaves(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _iter_string_leaves(item)


def _assert_no_remote_hosts(values: dict[str, Any]) -> None:
    """Raise SatsaConfigError when a remote URL or host is configured."""
    for leaf in _iter_string_leaves(values):
        matches = _URL_HOST_RE.findall(leaf)
        for host in matches:
            candidate = host.strip().lower().strip("[]")
            if candidate not in _ALLOWED_HOSTS:
                raise SatsaConfigError(f"non-loopback host rejected in config: {candidate}")
        lowered = leaf.lower()
        if ("http://" in lowered or "https://" in lowered) and not matches:
            raise SatsaConfigError(f"URL-like value without allowed host rejected: {leaf}")


class YamlFileSettingsSource(PydanticBaseSettingsSource):
    """Load settings from the YAML files under configs/."""

    def __init__(self, settings_cls: type[BaseSettings], config_dir: Path | None = None) -> None:
        """Initialise the source with an optional config directory override."""
        super().__init__(settings_cls)
        self._config_dir = config_dir or from_root("configs")

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """Return an empty tuple; bulk loading is done in __call__."""
        return None, "", False

    def __call__(self) -> dict[str, Any]:
        """Merge configs/*.yaml into a settings dict."""
        base = self._config_dir
        default_cfg = _load_yaml_file(base / "default.yaml")
        signals_cfg = _load_yaml_file(base / "signals.yaml")
        thresholds_cfg = _load_yaml_file(base / "thresholds.yaml")
        peers_cfg = _load_yaml_file(base / "peer_cohorts.yaml")
        llm_cfg = _load_yaml_file(base / "llm.yaml")
        merged: dict[str, Any] = {}
        if default_cfg.get("paths"):
            merged["paths"] = default_cfg["paths"]
        if default_cfg.get("seeds"):
            merged["seeds"] = default_cfg["seeds"]
        if default_cfg.get("chunk_sizes"):
            merged["chunk_sizes"] = default_cfg["chunk_sizes"]
        if default_cfg.get("window_policy"):
            merged["window_policy"] = default_cfg["window_policy"]
        if signals_cfg.get("signals"):
            merged["signal_family_flags"] = signals_cfg["signals"]
        if peers_cfg:
            merged["peer_cohort_definition"] = peers_cfg
        if thresholds_cfg:
            merged["thresholds"] = thresholds_cfg
        if llm_cfg is not None:
            merged["llm_config"] = llm_cfg
        return merged


class Settings(BaseSettings):
    """Central SATSA configuration object."""

    model_config = SettingsConfigDict(
        env_prefix="SATSA_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    paths: dict[str, Any] = Field(default_factory=dict)
    seeds: dict[str, Any] = Field(default_factory=dict)
    chunk_sizes: dict[str, Any] = Field(default_factory=dict)
    window_policy: dict[str, Any] = Field(default_factory=dict)
    signal_family_flags: dict[str, Any] = Field(default_factory=dict)
    peer_cohort_definition: dict[str, Any] = Field(default_factory=dict)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    llm_config: dict[str, Any] = Field(default_factory=lambda: {"enabled": False})
    airgap_assertion: bool = Field(default=True)
    satsa_env: str = Field(default="dev")
    manifest_key: str = Field(default=_DEFAULT_MANIFEST_KEY)
    analyst_salt: str = Field(default=_DEFAULT_SALT)
    log_level: str = Field(default="INFO")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Prefer init/env/dotenv values, fall back to YAML files."""
        return (init_settings, env_settings, dotenv_settings, YamlFileSettingsSource(settings_cls))

    @model_validator(mode="after")
    def _reject_remote_hosts(self) -> Settings:
        """Reject any non-loopback URL or hostname in string fields."""
        _assert_no_remote_hosts(self.model_dump())
        return self

    @model_validator(mode="after")
    def _check_default_keys(self) -> Settings:
        """Warn in dev or raise in production when default secrets are used."""
        is_default_salt = self.analyst_salt == _DEFAULT_SALT
        is_default_key = self.manifest_key == _DEFAULT_MANIFEST_KEY
        if is_default_salt or is_default_key:
            message = "default analyst_salt/manifest_key in use; rotate before production"
            if self.satsa_env == "production":
                raise SatsaConfigError(message)
            warnings.warn(message, UserWarning, stacklevel=2)
        return self


def load_settings(config_dir: str | Path | None = None, **overrides: Any) -> Settings:
    """Load settings from a config directory with optional field overrides."""
    target = from_root("configs") if config_dir is None else Path(config_dir)
    if not target.is_absolute():
        target = from_root(*target.parts)
    source = YamlFileSettingsSource(Settings, config_dir=target)
    merged = source()
    merged.update(overrides)
    return Settings(**merged)
