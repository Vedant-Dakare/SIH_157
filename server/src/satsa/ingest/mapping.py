"""YAML-driven field-mapping DSL loader and applicator."""

from __future__ import annotations

import hashlib
import os
import re
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import structlog
import yaml
from pydantic import BaseModel, Field

from satsa.errors import SatsaIngestError

logger = structlog.get_logger(__name__)

_CSV_INJECTION_RE = re.compile(r"^[=\+\-@\t\r]+")


class FieldMapping(BaseModel):
    """Single field rename / transform rule."""

    source: str = Field(min_length=1)
    required: bool = False
    hashed: bool = False
    salt_env: str | None = None
    severity_norm: bool = False


class TimestampFieldMapping(BaseModel):
    """Timestamp parsing rule with multiple accepted formats."""

    source: str = Field(min_length=1)
    formats: list[str] = Field(min_length=1)


class TableMapping(BaseModel):
    """Mapping rules for one logical table."""

    fields: dict[str, FieldMapping] = Field(default_factory=dict)
    timestamp_fields: dict[str, TimestampFieldMapping] = Field(default_factory=dict)


class MappingConfig(BaseModel):
    """Top-level mapping configuration for one CSE."""

    cse_id: str = Field(min_length=1)
    source_timezone: str = Field(default="UTC")
    tables: dict[str, TableMapping] = Field(default_factory=dict)


def _load_severity_table(config_dir: Path) -> dict[str, str]:
    """Load the severity normalisation table from severity_taxonomy.yaml."""
    taxonomy_path = config_dir / "severity_taxonomy.yaml"
    if not taxonomy_path.exists():
        taxonomy_path = Path("configs") / "severity_taxonomy.yaml"
    if not taxonomy_path.exists():
        return {}
    with taxonomy_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    table = data.get("severity_norm", {}) or {}
    return {str(key).upper(): str(val).upper() for key, val in table.items()}


def load_mapping(cse_id: str, mapping_dir: str | Path = "configs/mappings") -> MappingConfig:
    """Load configs/mappings/{cse_id}.yaml into a MappingConfig.

    Args:
        cse_id: CSE identifier used to locate the YAML file.
        mapping_dir: Directory containing per-CSE mapping files.

    Returns:
        Parsed MappingConfig; identity mapping with WARNING when file is absent.
    """
    mapping_path = Path(mapping_dir) / f"{cse_id}.yaml"
    if not mapping_path.exists():
        warnings.warn(
            f"no mapping file for {cse_id}; using identity mapping",
            UserWarning,
            stacklevel=2,
        )
        logger.warning("mapping_missing_identity_fallback", cse_id=cse_id)
        return MappingConfig(cse_id=cse_id, source_timezone="UTC", tables={})
    with mapping_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    try:
        return MappingConfig.model_validate(raw)
    except Exception as exc:
        raise SatsaIngestError(f"invalid mapping file for {cse_id}: {exc}") from exc


def hash_value(value: str, salt_env: str | None) -> str:
    """Hash a value with SHA-256 plus salt from the named environment variable."""
    salt = ""
    if salt_env:
        salt = os.environ.get(salt_env, "")
    payload = f"{value}{salt}".encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def normalise_severity(raw: str, table: dict[str, str]) -> str:
    """Look up severity_norm; return UNKNOWN with WARNING when unmapped."""
    key = str(raw).strip().upper()
    if key in table:
        return table[key]
    warnings.warn(f"unknown severity '{raw}'; mapped to UNKNOWN", UserWarning, stacklevel=3)
    logger.warning("severity_unmapped", raw=raw)
    return "UNKNOWN"


def sanitise_csv_value(value: Any) -> Any:
    """Strip CSV injection prefixes (=, +, -, @) with a WARNING."""
    if not isinstance(value, str):
        return value
    if _CSV_INJECTION_RE.match(value):
        cleaned = _CSV_INJECTION_RE.sub("", value)
        warnings.warn(f"CSV injection pattern stripped: {value!r}", UserWarning, stacklevel=3)
        logger.warning("csv_injection_stripped", original=value)
        return cleaned
    return value


def parse_timestamp(
    raw: str | datetime, formats: list[str], source_tz: str
) -> tuple[datetime, str]:
    """Parse a timestamp with multiple formats and normalise to UTC.

    Returns:
        Tuple of (utc_datetime, original_offset_string).
    """
    if isinstance(raw, datetime):
        candidate = raw
        orig_offset = candidate.strftime("%z") if candidate.tzinfo else ""
        if candidate.tzinfo is None:
            candidate = candidate.replace(tzinfo=ZoneInfo(source_tz))
        return candidate.astimezone(UTC), orig_offset
    last_error: Exception | None = None
    for fmt in formats:
        try:
            candidate = datetime.strptime(str(raw), fmt)
            orig_offset = candidate.strftime("%z") if candidate.tzinfo else ""
            if candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=ZoneInfo(source_tz))
            return candidate.astimezone(UTC), orig_offset
        except Exception as exc:  # noqa: BLE001 - try next format
            last_error = exc
            continue
    raise SatsaIngestError(f"unparseable timestamp {raw!r}: {last_error}")


def apply_mapping(
    records: list[dict[str, Any]],
    mapping: MappingConfig,
    table: str,
    config_dir: str | Path = "configs",
) -> list[dict[str, Any]]:
    """Apply a MappingConfig to raw source records.

    Args:
        records: Raw source dicts.
        mapping: Loaded MappingConfig.
        table: Logical table name within the mapping.
        config_dir: Config directory used to load the severity table.

    Returns:
        List of mapped dicts with UTC timestamps and hashed fields.

    Raises:
        SatsaIngestError: When a required source field is missing.
    """
    table_cfg = mapping.tables.get(table)
    if table_cfg is None:
        warnings.warn(
            f"no mapping table '{table}'; using identity mapping",
            UserWarning,
            stacklevel=2,
        )
        return [dict(row) for row in records]
    severity_table = _load_severity_table(Path(config_dir))
    output: list[dict[str, Any]] = []
    for row in records:
        mapped: dict[str, Any] = {}
        for target, rule in table_cfg.fields.items():
            if rule.source not in row or row[rule.source] is None:
                if rule.required:
                    raise SatsaIngestError(
                        f"missing required field '{rule.source}' for target '{target}'"
                    )
                continue
            value = sanitise_csv_value(row[rule.source])
            if rule.hashed:
                value = hash_value(str(value), rule.salt_env)
            if rule.severity_norm:
                value = normalise_severity(str(value), severity_table)
            mapped[target] = value
        for ts_target, ts_rule in table_cfg.timestamp_fields.items():
            if ts_rule.source not in row or row[ts_rule.source] is None:
                continue
            utc_dt, orig_offset = parse_timestamp(
                row[ts_rule.source], ts_rule.formats, mapping.source_timezone
            )
            mapped[ts_target] = utc_dt
            mapped[f"{ts_target}_orig_offset"] = orig_offset
            if ts_target in table_cfg.fields:
                continue
        for key, value in row.items():
            if key not in mapped and key in [r.source for r in table_cfg.fields.values()]:
                continue
        output.append(mapped)
    return output
