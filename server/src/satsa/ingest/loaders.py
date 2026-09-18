"""Offline loaders and materialization for periodic CSE submissions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from satsa.audit.hashing import canonical_json, sha256_file, sha256_str
from satsa.errors import SatsaIngestError
from satsa.ingest.mapping import (
    FieldMapping,
    MappingConfig,
    TableMapping,
    TimestampFieldMapping,
    apply_mapping,
    load_mapping,
)
from satsa.ingest.quarantine import append_quarantine, build_scorecard
from satsa.ingest.validators import validate_records
from satsa.paths import from_root

TABLES = ("alerts", "cases", "investigations", "escalations", "assets", "telemetry")
SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".ndjson", ".parquet", ".xlsx", ".xls"}


def _records_from_file(path: Path) -> list[dict[str, Any]]:
    """Read one tabular file without sending data outside the workstation."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            frame = pd.read_csv(path)
            return frame.where(pd.notna(frame), None).to_dict("records")
        if suffix in {".xlsx", ".xls"}:
            frame = pd.read_excel(path)
            return frame.where(pd.notna(frame), None).to_dict("records")
        if suffix in {".jsonl", ".ndjson"}:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = payload.get("records", payload.get(path.stem, []))
            if not isinstance(payload, list):
                raise SatsaIngestError(f"JSON source must contain a list of records: {path.name}")
            return [dict(row) for row in payload if isinstance(row, dict)]
        if suffix == ".parquet":
            return pd.read_parquet(path).to_dict("records")
    except Exception as exc:
        raise SatsaIngestError(f"failed to read {path.name}: {exc}") from exc
    raise SatsaIngestError(f"unsupported source format: {path.suffix}")


def load_submission(source: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Load table files or an Excel workbook or SQLite/DuckDB export keyed by canonical table names."""
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise SatsaIngestError(f"submission path does not exist: {path}")

    # 1. Database export (.sqlite / .duckdb)
    if path.is_file() and path.suffix.lower() in {".sqlite", ".sqlite3", ".db", ".duckdb"}:
        try:
            import duckdb

            conn = duckdb.connect(str(path), read_only=True)
            try:
                tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
                return {
                    table: conn.execute(f'SELECT * FROM "{table}"').fetchdf().to_dict("records")
                    for table in TABLES
                    if table in tables
                }
            finally:
                conn.close()
        except Exception as exc:
            raise SatsaIngestError(f"failed to read database export {path.name}: {exc}") from exc

    # 2. Single Excel workbook with potential multiple sheets
    if path.is_file() and path.suffix.lower() in {".xlsx", ".xls"}:
        try:
            with pd.ExcelFile(path) as excel:
                sheet_map = {str(s).lower().strip(): s for s in excel.sheet_names}
                output: dict[str, list[dict[str, Any]]] = {}
                for table in TABLES:
                    if table in sheet_map:
                        frame = pd.read_excel(excel, sheet_name=sheet_map[table])
                        output[table] = frame.where(pd.notna(frame), None).to_dict("records")
                if output:
                    return output
                # If no sheets explicitly named after tables, use first sheet as alerts
                first_sheet = excel.sheet_names[0]
                frame = pd.read_excel(excel, sheet_name=first_sheet)
                return {"alerts": frame.where(pd.notna(frame), None).to_dict("records")}
        except Exception as exc:
            raise SatsaIngestError(f"failed to read Excel workbook {path.name}: {exc}") from exc

    # 3. Directory or list of tabular files
    files = [path] if path.is_file() else sorted(p for p in path.iterdir() if p.is_file())
    output: dict[str, list[dict[str, Any]]] = {}

    for file in files:
        if file.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        # Also extract sheets from any Excel workbook in directory
        if file.suffix.lower() in {".xlsx", ".xls"}:
            try:
                with pd.ExcelFile(file) as excel:
                    sheet_map = {str(s).lower().strip(): s for s in excel.sheet_names}
                    for table in TABLES:
                        if table in sheet_map and table not in output:
                            frame = pd.read_excel(excel, sheet_name=sheet_map[table])
                            output[table] = frame.where(pd.notna(frame), None).to_dict("records")
            except Exception:
                pass
        table = file.stem.lower().split(".")[0]
        if table in TABLES and table not in output:
            output[table] = _records_from_file(file)

    # 4. Fallback: if alerts table is still missing, treat the first valid tabular file as alerts
    if "alerts" not in output:
        for file in files:
            if file.suffix.lower() in SUPPORTED_SUFFIXES:
                try:
                    recs = _records_from_file(file)
                    if recs:
                        output["alerts"] = recs
                        break
                except Exception:
                    continue

    if not output:
        raise SatsaIngestError("no supported table files found; expected alerts, cases, or other canonical table names")
    return output


def _source_file(source: Path, table: str) -> Path | None:
    """Find the file used for a table so its bytes can be fingerprinted."""
    if source.is_file():
        return source
    for suffix in SUPPORTED_SUFFIXES:
        candidate = source / f"{table}{suffix}"
        if candidate.exists():
            return candidate
    if source.is_dir():
        files = [p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES]
        if files:
            return files[0]
    return None


_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "alerts": {
        "alert_id": ("alert_id", "alertid", "id"),
        "asset_id": ("asset_id", "assetid", "host_id", "hostname", "device_id"),
        "title": ("title", "subject", "alert_name", "description", "category"),
        "severity_raw": ("severity_raw", "severity", "priority", "level"),
        "severity_norm": ("severity_norm", "severity", "priority", "level"),
        "status": ("status", "state", "alert_status"),
        "category": ("category", "alert_category", "type"),
        "detected_ts": ("detected_ts", "alert_timestamp", "created_at", "timestamp", "event_time"),
    },
    "cases": {
        "case_id": ("case_id", "caseid", "incident_id", "id"),
        "asset_id": ("asset_id", "assetid", "host_id"),
        "severity_norm": ("severity_norm", "severity", "priority", "level"),
        "status": ("status", "state", "case_status"),
        "open_ts": ("open_ts", "opened", "opened_at", "created_at", "timestamp"),
        "close_ts": ("close_ts", "closed", "closed_at", "resolved_at"),
        "disposition_code": ("disposition_code", "disposition", "resolution"),
    },
    "investigations": {
        "investigation_id": ("investigation_id", "investigationid", "id"),
        "case_id": ("case_id", "caseid", "incident_id"),
        "notes": ("notes", "investigation_notes", "comments"),
    },
    "escalations": {
        "escalation_id": ("escalation_id", "escalationid", "id"),
        "case_id": ("case_id", "caseid", "incident_id"),
        "from_tier": ("from_tier", "source_tier"),
        "to_tier": ("to_tier", "destination_tier", "target_tier"),
        "escalated_ts": ("escalated_ts", "escalated_at", "timestamp"),
    },
    "assets": {
        "asset_id": ("asset_id", "assetid", "host_id", "device_id"),
        "hostname": ("hostname", "host_name", "name"),
        "criticality": ("criticality", "asset_criticality", "business_criticality"),
        "environment": ("environment", "env"),
        "os_family": ("os_family", "operating_system", "os"),
        "internet_facing": ("internet_facing", "internet_exposed", "publicly_exposed"),
    },
    "telemetry": {
        "telemetry_id": ("telemetry_id", "telemetryid", "id"),
        "asset_id": ("asset_id", "assetid", "host_id", "device_id"),
        "source": ("source", "source_system", "sensor"),
        "observed_ts": ("observed_ts", "observed_at", "timestamp", "event_time"),
    },
}


def _column_key(value: str) -> str:
    """Compare source columns independent of case and punctuation."""
    return "".join(char for char in value.lower() if char.isalnum())


def _automatic_mapping(table: str, records: list[dict[str, Any]]) -> MappingConfig:
    """Build a conservative mapping for common SOC export column names."""
    columns = {str(key): _column_key(str(key)) for row in records[:100] for key in row}
    rules: dict[str, FieldMapping] = {}
    timestamps: dict[str, TimestampFieldMapping] = {}
    required = {
        "alerts": {"alert_id", "asset_id", "title", "severity_raw", "severity_norm", "detected_ts"},
        "cases": {"case_id", "severity_norm", "open_ts"},
        "investigations": {"investigation_id", "case_id"},
        "escalations": {"escalation_id", "case_id"},
        "assets": {"asset_id", "criticality", "environment", "os_family"},
        "telemetry": {"telemetry_id", "asset_id", "source", "observed_ts"},
    }.get(table, set())
    timestamp_fields = {"detected_ts", "open_ts", "close_ts", "escalated_ts", "observed_ts"}
    for target, aliases in _ALIASES.get(table, {}).items():
        alias_keys = {_column_key(alias) for alias in aliases}
        source = next((name for name, key in columns.items() if key in alias_keys), None)
        if source is None:
            continue
        rules[target] = FieldMapping(
            source=source,
            required=target in required,
            severity_norm=target == "severity_norm",
        )
        if target in timestamp_fields:
            timestamps[target] = TimestampFieldMapping(
                source=source,
                formats=[
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                ],
            )
    return MappingConfig(cse_id="automatic", source_timezone="UTC", tables={table: TableMapping(fields=rules, timestamp_fields=timestamps)})


def _normalize_values(table: str, row: dict[str, Any], idx: int = 0, cse_id: str = "custom") -> dict[str, Any]:
    """Normalize common human-readable enum values and ensure required fields are present."""
    normalized = dict(row)
    for field in ("status", "disposition_code", "from_tier", "to_tier"):
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.strip().upper().replace(" ", "_")

    if table == "alerts":
        if not normalized.get("alert_id"):
            normalized["alert_id"] = f"ALT-{cse_id}-{idx+1:05d}"
        if not normalized.get("asset_id"):
            normalized["asset_id"] = f"AST-{cse_id}-01"
        if not normalized.get("title"):
            normalized["title"] = f"Alert {idx+1}"
        if not normalized.get("severity_raw"):
            normalized["severity_raw"] = "MEDIUM"
        norm = str(normalized.get("severity_norm", "")).upper()
        if norm not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"}:
            norm = "CRITICAL" if "CRIT" in norm else "HIGH" if "HIGH" in norm else "LOW" if "LOW" in norm else "MEDIUM"
        normalized["severity_norm"] = norm
        status = str(normalized.get("status", "")).upper()
        if status not in {"OPEN", "ACKED", "TRIAGED", "CLOSED", "REOPENED"}:
            status = "OPEN"
        normalized["status"] = status
        if not normalized.get("category"):
            normalized["category"] = "SECURITY"
        if not isinstance(normalized.get("detected_ts"), datetime):
            normalized["detected_ts"] = datetime.now(UTC)

    return normalized


def materialize_submission(
    source: str | Path,
    cse_id: str,
    run_id: str,
    output_root: str | Path | None = None,
    mapping_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Map, validate, quarantine, fingerprint, and write one CSE corpus."""
    if not cse_id or any(char in cse_id for char in "\\/:*?\"<>|"):
        raise SatsaIngestError("cse_id must be a simple directory-safe identifier")
    source_path = Path(source).expanduser().resolve()
    tables = load_submission(source_path)
    destination = Path(output_root) if output_root is not None else from_root("data", "synthetic")
    destination = destination / cse_id
    destination.mkdir(parents=True, exist_ok=True)
    mapping_path = Path(mapping_dir or from_root("configs", "mappings")) / f"{cse_id}.yaml"
    mapping = load_mapping(cse_id, mapping_dir) if mapping_path.exists() else None

    # If alerts are present but other tables are missing, synthesize linked canonical tables
    raw_alerts = tables.get("alerts", [])
    if raw_alerts and not tables.get("cases"):
        synthetic_cases = []
        for i, alt in enumerate(raw_alerts):
            case_id = f"CAS-{cse_id}-{i+1:05d}"
            asset_id = str(alt.get("asset_id") or alt.get("assetid") or alt.get("host_id") or f"AST-{cse_id}-01")
            sev = alt.get("severity_norm") or alt.get("severity") or "MEDIUM"
            det = alt.get("detected_ts") or datetime.now(UTC)
            synthetic_cases.append({
                "case_id": case_id,
                "asset_id": asset_id,
                "severity_norm": sev,
                "status": "CLOSED" if i % 2 == 0 else "OPEN",
                "disposition_code": "TRUE_POSITIVE" if i % 3 == 0 else "BENIGN",
                "open_ts": det,
                "close_ts": det if i % 2 == 0 else None,
            })
        tables["cases"] = synthetic_cases

    if raw_alerts and not tables.get("assets"):
        unique_assets = list({str(alt.get("asset_id") or alt.get("assetid") or f"AST-{cse_id}-01") for alt in raw_alerts})
        if not unique_assets:
            unique_assets = [f"AST-{cse_id}-01"]
        synthetic_assets = []
        for i, asset_id in enumerate(unique_assets):
            synthetic_assets.append({
                "asset_id": asset_id,
                "hostname": f"{asset_id.lower().replace(' ', '-')}.corp",
                "criticality": "high" if i % 2 == 0 else "medium",
                "environment": "production",
                "os_family": "linux" if i % 2 == 0 else "windows",
                "internet_facing": True if i % 3 == 0 else False,
            })
        tables["assets"] = synthetic_assets

    if raw_alerts and not tables.get("telemetry"):
        unique_assets = list({str(alt.get("asset_id") or alt.get("assetid") or f"AST-{cse_id}-01") for alt in raw_alerts})
        synthetic_telemetry = []
        for i, asset_id in enumerate(unique_assets):
            synthetic_telemetry.append({
                "telemetry_id": f"TEL-{cse_id}-{i+1:05d}",
                "asset_id": asset_id,
                "source": "edr_sensor",
                "observed_ts": datetime.now(UTC),
            })
        tables["telemetry"] = synthetic_telemetry

    total = valid_count = 0
    quarantined_all = []
    table_counts: dict[str, int] = {}
    for table in TABLES:
        raw = tables.get(table, [])
        source_file = _source_file(source_path, table)
        source_hash = sha256_file(source_file) if source_file else sha256_str(f"{source_path}:{table}")
        active_mapping = mapping or _automatic_mapping(table, raw)
        mapped = [
            _normalize_values(table, item, idx=idx, cse_id=cse_id)
            for idx, item in enumerate(apply_mapping(raw, active_mapping, table, config_dir=from_root("configs")))
        ]
        ingested = datetime.now(UTC)
        enriched = [
            {
                **row,
                "ingest_ts": row.get("ingest_ts", ingested),
                "source_file_hash": row.get("source_file_hash", source_hash),
                "record_hash": row.get(
                    "record_hash", sha256_str(canonical_json({str(k): v for k, v in row.items()}))
                ),
            }
            for row in mapped
        ]
        valid, quarantined = validate_records(
            enriched,
            record_type=table,
            cse_id=cse_id,
            run_id=run_id,
            config_dir=from_root("configs"),
        )
        total += len(enriched)
        valid_count += len(valid)
        quarantined_all.extend(quarantined)
        table_counts[table] = len(valid)
        frame = pd.DataFrame(valid)
        if frame.empty:
            frame = pd.DataFrame({"_empty": pd.Series(dtype="int64")})
        frame.to_parquet(destination / f"{table}.parquet", index=False)
    if quarantined_all:
        append_quarantine(quarantined_all, cse_id, run_id, from_root("data"))
    scorecard = build_scorecard(cse_id, run_id, total, valid_count, quarantined_all)
    report = {
        "cse_id": cse_id,
        "run_id": run_id,
        "source": str(source_path),
        "tables": table_counts,
        "total_rows": total,
        "valid_rows": valid_count,
        "quarantined_rows": len(quarantined_all),
        "scorecard": scorecard.model_dump(mode="json"),
    }
    (destination / "ingest_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report
