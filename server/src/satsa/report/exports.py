"""Idempotent finding exports: CSV, XLSX (minimal writer fallback), JSON bundle."""

from __future__ import annotations

import csv
import json
import logging
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "finding_id",
    "entity_id",
    "signal_id",
    "value",
    "threshold",
    "severity",
    "confidence",
    "is_flagged",
    "window",
    "evidence_id",
]


def _rows(store: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten findings to export rows (sorted for idempotence)."""
    rows: list[dict[str, Any]] = []
    for finding_id in sorted(store.get("findings", {})):
        finding = store["findings"][finding_id]
        rows.append(
            {
                "finding_id": finding_id,
                "entity_id": finding.get("entity_id", ""),
                "signal_id": finding.get("signal_id", ""),
                "value": finding.get("observed", ""),
                "threshold": finding.get("threshold", ""),
                "severity": finding.get("severity", ""),
                "confidence": finding.get("confidence", ""),
                "is_flagged": finding.get("is_flagged", True),
                "window": finding.get("window", ""),
                "evidence_id": finding.get("evidence_id", ""),
            }
        )
    return rows


def export_findings_csv(
    run_id: str, output_path: str | Path, store: dict[str, Any] | None = None
) -> Path:
    """Write findings CSV (overwrite → idempotent)."""
    from satsa.report.render_html import REPORTS_ROOT, load_store

    store = store or load_store(run_id, REPORTS_ROOT)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(_rows(store))
    return target


def _minimal_xlsx(rows: list[dict[str, Any]], target: Path) -> None:
    """Write a minimal single-sheet .xlsx via zip + hand-built XML."""
    def _cell(ref: str, value: Any, inline: bool = True) -> str:
        text = xml_escape(str(value))
        if inline:
            return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
        return f'<c r="{ref}"><v>{text}</v></c>'

    def _col(n: int) -> str:
        name = ""
        n += 1
        while n:
            n, rem = divmod(n - 1, 26)
            name = chr(65 + rem) + name
        return name

    header = "".join(_cell(f"{_col(i)}1", h) for i, h in enumerate(CSV_COLUMNS))
    sheet_rows = [f'<row r="1">{header}</row>']
    for r_i, row in enumerate(rows, start=2):
        cells = "".join(
            _cell(f"{_col(i)}{r_i}", row.get(col, "")) for i, col in enumerate(CSV_COLUMNS)
        )
        sheet_rows.append(f'<row r="{r_i}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    _XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    _CT = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    _REL = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    _DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    _MAIN = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    _SHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
    _RELS_CT = "application/vnd.openxmlformats-package.relationships+xml"
    parts = {
        "[Content_Types].xml": (
            _XML + _CT
            + f'<Default Extension="rels" ContentType="{_RELS_CT}"/>'
            + '<Default Extension="xml" ContentType="application/xml"/>'
            + f'<Override PartName="/xl/workbook.xml" ContentType="{_MAIN}"/>'
            + f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{_SHEET}"/>'
            + "</Types>"
        ),
        "_rels/.rels": (
            _XML + _REL
            + f'<Relationship Id="rId1" Type="{_DOC}/officeDocument" Target="xl/workbook.xml"/>'
            + "</Relationships>"
        ),
        "xl/workbook.xml": (
            _XML
            + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            + f' xmlns:r="{_DOC}">'
            + '<sheets><sheet name="findings" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            _XML + _REL
            + f'<Relationship Id="rId1" Type="{_DOC}/worksheet" Target="worksheets/sheet1.xml"/>'
            + "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": sheet,
    }
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)


def export_findings_xlsx(
    run_id: str, output_path: str | Path, store: dict[str, Any] | None = None
) -> Path:
    """Write findings XLSX via openpyxl when present, else the minimal writer."""
    from satsa.report.render_html import REPORTS_ROOT, load_store

    store = store or load_store(run_id, REPORTS_ROOT)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows(store)
    try:
        import openpyxl

        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "findings"
        sheet.append(CSV_COLUMNS)
        for row in rows:
            sheet.append([row.get(col, "") for col in CSV_COLUMNS])
        book.save(target)
    except ImportError:
        logger.warning("openpyxl unavailable, using minimal XLSX writer")
        _minimal_xlsx(rows, target)
    return target


def export_findings_json(
    run_id: str, output_path: str | Path, store: dict[str, Any] | None = None
) -> Path:
    """Write the JSON bundle: findings + evidence + reason codes + audit refs."""
    from satsa.report.render_html import REPORTS_ROOT, load_store

    store = store or load_store(run_id, REPORTS_ROOT)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "run_id": run_id,
        "generated_at": store.get("generated_at", ""),
        "merkle_root": store.get("merkle_root", ""),
        "findings": store.get("findings", {}),
        "records": store.get("records", {}),
        "queue": store.get("queue", []),
    }
    target.write_text(
        json.dumps(bundle, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return target
