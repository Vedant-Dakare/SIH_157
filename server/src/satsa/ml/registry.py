"""Versioned model registry with hash verification and feature-list gating."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from satsa.errors import SatsaSignalError

REGISTRY_PATH = Path("models/registry.json")


class ModelRecord(BaseModel):
    """One registered model artefact."""

    name: str = Field(min_length=1)
    version: str = Field(default="v1")
    trained_at: str = Field(min_length=1)
    training_data_hash: str = Field(default="")
    feature_list: list[str] = Field(default_factory=list)
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    seed: int = Field(default=42)
    metrics: dict[str, float] = Field(default_factory=dict)
    file_path: str = Field(min_length=1)
    file_hash: str = Field(default="")
    calibrated: bool = Field(default=False)


def _sha256_file(path: Path) -> str:
    """Return SHA-256 of a file, or empty string when missing."""
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    """Return the current UTC time as ISO-8601."""
    return datetime.now(UTC).isoformat()


class ModelRegistry:
    """JSON-backed registry at models/registry.json."""

    def __init__(self, path: str | Path = REGISTRY_PATH) -> None:
        """Initialise with an optional registry path override."""
        self._path = Path(path)

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all raw records (empty list when absent/corrupt)."""
        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return []
        return data if isinstance(data, list) else []

    def _write_all(self, records: list[dict[str, Any]]) -> None:
        """Persist raw records atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def register(
        self,
        name: str,
        feature_list: list[str],
        hyperparams: dict[str, Any] | None = None,
        seed: int = 42,
        metrics: dict[str, float] | None = None,
        file_path: str = "",
        calibrated: bool = False,
        training_data_hash: str = "",
        version: str = "v1",
    ) -> ModelRecord:
        """Register (or replace by name) a model artefact; returns the record."""
        records = self._read_all()
        file_hash = _sha256_file(Path(file_path)) if file_path else ""
        record = ModelRecord(
            name=name,
            version=version,
            trained_at=_utc_now(),
            training_data_hash=training_data_hash,
            feature_list=list(feature_list),
            hyperparams=dict(hyperparams or {}),
            seed=int(seed),
            metrics={k: float(v) for k, v in (metrics or {}).items()},
            file_path=file_path,
            file_hash=file_hash,
            calibrated=bool(calibrated),
        )
        records = [r for r in records if r.get("name") != name]
        records.append(record.model_dump())
        self._write_all(records)
        return record

    def list_models(self) -> list[ModelRecord]:
        """Return all registered models."""
        return [ModelRecord(**raw) for raw in self._read_all()]

    def load(self, name: str, current_features: list[str] | None = None) -> ModelRecord:
        """Load one record, asserting feature-list equality when provided.

        Mismatch raises SatsaSignalError with a clear delta message.
        """
        for raw in self._read_all():
            if raw.get("name") == name:
                record = ModelRecord(**raw)
                if current_features is not None:
                    expected = list(record.feature_list)
                    actual = list(current_features)
                    if expected != actual:
                        missing = [f for f in expected if f not in actual]
                        extra = [f for f in actual if f not in expected]
                        raise SatsaSignalError(
                            f"feature_list mismatch for model {name}: "
                            f"missing={missing} extra={extra}"
                        )
                return record
        raise KeyError(f"model not registered: {name}")

    def verify_hashes(self) -> dict[str, bool]:
        """Verify on-disk SHA-256 of every registered artefact."""
        results: dict[str, bool] = {}
        for raw in self._read_all():
            record = ModelRecord(**raw)
            if not record.file_path:
                results[record.name] = False
                continue
            results[record.name] = _sha256_file(Path(record.file_path)) == record.file_hash
        return results
