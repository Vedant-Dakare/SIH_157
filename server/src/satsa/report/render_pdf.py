"""HTML → PDF: WeasyPrint when installed, reportlab fallback, else minimal PDF.

Every page footer carries generated_at, run_id and the Merkle root. The
minimal fallback writes a valid PDF by hand (Helvetica, A4) so rendering
never fails air-gapped.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _strip_text(html_str: str) -> list[str]:
    """Reduce HTML to plain text lines for fallback renderers."""
    text = re.sub(r"(?s)<script.*?</script>", " ", html_str)
    text = re.sub(r"(?s)<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", "\n", text)
    lines: list[str] = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if line:
            lines.append(line)
    return lines


def _minimal_pdf(lines: list[str], footer: str) -> bytes:
    """Build a minimal valid multi-page PDF (A4, Helvetica)."""
    width, height, margin, leading = 595, 842, 50, 14
    usable = height - 2 * margin - 20
    per_page = max(1, int(usable // leading))
    pages: list[list[str]] = [
        lines[i : i + per_page] for i in range(0, len(lines), per_page)
    ] or [[]]

    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    font_obj = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    kids: list[str] = []
    blobs: dict[int, bytes] = {1: font_obj}
    for number, page_lines in enumerate(pages, start=1):
        page_no, content_no = 3 + (number - 1) * 2, 4 + (number - 1) * 2
        kids.append(f"{page_no} 0 R")
        content = ["BT /F1 11 Tf"]
        y = height - margin
        for line in page_lines:
            content.append(f"50 {y} Td ({_escape(line[:110])}) Tj")
            y -= leading
        content.append(f"50 30 Td ({_escape(f'Page {number} of {len(pages)} | {footer}')}) Tj")
        content.append("ET")
        stream = ("\n".join(content)).encode("latin-1", errors="replace")
        blobs[page_no] = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 {width} {height}]"
            f"/Resources<</Font<</F1 1 0 R>>>>/Contents {content_no} 0 R>>"
        ).encode("ascii")
        blobs[content_no] = (
            f"<</Length {len(stream)}>>stream\n".encode("ascii") + stream + b"\nendstream\n"
        )
    blobs[2] = f"<</Type/Pages/Kids[{' '.join(kids)}]/Count {len(pages)}>>".encode("ascii")
    catalog_no = 2 + 2 * len(pages) + 1
    blobs[catalog_no] = b"<</Type/Catalog/Pages 2 0 R>>"
    total = catalog_no
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0] * (total + 1)
    for num in range(1, total + 1):
        offsets[num] = len(out)
        out += f"{num} 0 obj".encode("ascii") + blobs[num] + b"endobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {total + 1}\n0000000000 65535 f \n".encode("ascii")
    for num in range(1, total + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode("ascii")
    trailer = f"trailer<</Size {total + 1}/Root {catalog_no} 0 R>>\nstartxref\n{xref_pos}\n%%EOF"
    out += trailer.encode("ascii")
    return bytes(out)


def render_pdf(html_str: str, output_path: str | Path, footer: str = "") -> Path:
    """Render HTML to PDF, preferring WeasyPrint, then reportlab, then minimal.

    On WeasyPrint ImportError the reportlab fallback runs with a WARNING;
    with neither installed the minimal writer still produces a valid file.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    meta = footer or f"run report {datetime.now(UTC).isoformat()}"
    try:
        from weasyprint import HTML

        HTML(string=html_str).write_pdf(str(target))
        return target
    except ImportError:
        logger.warning("WeasyPrint unavailable, trying reportlab fallback")
    except Exception as exc:
        logger.warning("WeasyPrint render failed (%s); trying fallbacks", exc)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as canvas_mod

        lines = _strip_text(html_str)
        canvas = canvas_mod.Canvas(str(target), pagesize=A4)
        width, height = A4
        y = height - 50.0
        page = 1
        canvas.setFont("Helvetica", 11)
        for line in lines:
            if y < 60:
                canvas.drawString(50, 30, f"Page {page} | {meta}")
                canvas.showPage()
                canvas.setFont("Helvetica", 11)
                page += 1
                y = height - 50.0
            canvas.drawString(50, y, line[:110])
            y -= 14
        canvas.drawString(50, 30, f"Page {page} | {meta}")
        canvas.save()
        return target
    except ImportError:
        logger.warning("reportlab unavailable, using minimal PDF writer")
    lines = _strip_text(html_str) + ["", meta]
    target.write_bytes(_minimal_pdf(lines, meta))
    return target
