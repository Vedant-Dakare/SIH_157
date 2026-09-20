"""SATSA offline API: FastAPI when installed, stdlib fallback otherwise.

Bound to 127.0.0.1 only (asserted at startup). Optional static token gate
(X-API-Token) when enabled. OpenAPI docs at /docs come free with FastAPI.

Usage: python -m satsa.api.main --port 8080
"""

from __future__ import annotations

import argparse
import json
import tempfile
import subprocess
import sys
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from satsa.api import deps
from satsa.api.routes import audit as audit_routes
from satsa.api.routes import entities as entity_routes
from satsa.api.routes import findings as finding_routes
from satsa.api.routes import queue as queue_routes
from satsa.api.routes import runs as run_routes
from satsa.paths import ROOT, from_root

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".duckdb",
    ".xlsx",
    ".xls",
}

API_HOST = "127.0.0.1"
API_VERSION = "phase6"
UI_DIST = from_root("client", "dist")

_API_PREFIXES = ("/health", "/runs", "/entities", "/findings", "/queue", "/audit", "/docs")

_STATIC_TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".map": "application/json",
}


def _now() -> str:
    """Current UTC timestamp for envelopes."""
    return datetime.now(UTC).isoformat()


def _envelope(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Attach run_id + generated_at to every response."""
    return {"run_id": run_id, "generated_at": _now(), **payload}


def _spawn_run(run_id: str) -> None:
    """Fire a pipeline subprocess without blocking the response (A2)."""
    import os

    log_path = from_root("data", "warehouse", "runs", f"{run_id}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab")

    env = dict(os.environ)
    server_src = str(from_root("server", "src"))
    root_src = str(from_root("src"))
    existing_pythonpath = env.get("PYTHONPATH", "")
    paths = [server_src, root_src]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    venv_py = from_root("venv", "Scripts", "python.exe")
    exe = str(venv_py) if venv_py.exists() else sys.executable

    subprocess.Popen(
        [exe, "-m", "satsa.pipeline.orchestrator", "--run-id", run_id, "--force"],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
    )
    log_handle.close()


def _ingest_upload(content_type: str, body: bytes, query: dict[str, str]) -> tuple[int, dict[str, Any]]:
    """Materialize a local multipart submission and run pipeline immediately."""
    from email import policy
    from email.parser import BytesParser

    from satsa.errors import SatsaIngestError
    from satsa.ingest.loaders import materialize_submission

    if len(body) > MAX_UPLOAD_BYTES:
        return 413, {"error": "upload exceeds the 100 MB local limit"}
    cse_id = query.get("cse_id", "").strip()
    run_id = query.get("run_id", "").strip() or f"upload-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    if not cse_id:
        return 400, {"error": "cse_id is required"}
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    with tempfile.TemporaryDirectory(prefix="satsa-upload-", ignore_cleanup_errors=True) as temp_dir:
        written = 0
        for part in message.walk():
            filename = part.get_filename()
            if not filename:
                continue
            cleaned_name = Path(filename).name
            if Path(cleaned_name).suffix.lower() not in UPLOAD_SUFFIXES:
                continue
            target = Path(temp_dir) / cleaned_name
            target.write_bytes(part.get_payload(decode=True) or b"")
            written += 1
        if not written:
            return 400, {"error": "no supported files were uploaded; please select an Excel (.xlsx/.xls), CSV, or JSON file"}
        try:
            report = materialize_submission(temp_dir, cse_id, run_id)
        except (SatsaIngestError, OSError, ValueError) as exc:
            return 422, {"error": str(exc)}

    # Spawn the scoring pipeline in the background so upload returns in <1s
    _spawn_run(run_id)

    return 200, {"run_id": run_id, "status": "processing", "report": report}


def handle_request(
    method: str,
    path: str,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Route one request to (status, JSON body); backend-agnostic core."""
    query = query or {}
    headers = headers or {}
    config = deps.load_api_config()
    if not deps.check_token(headers, config):
        return 401, _envelope(query.get("run_id", ""), {"error": "missing or invalid X-API-Token"})
    parts = [p for p in path.strip("/").split("/") if p]

    if method == "GET" and parts == ["health"]:
        status, payload = run_routes.health()
        return status, _envelope("", payload)
    if method == "GET" and parts == ["runs"]:
        status, payload = run_routes.list_runs()
        return status, _envelope("", payload)
    if method == "GET" and len(parts) == 3 and parts[0] == "runs" and parts[2] == "manifest":
        status, payload = run_routes.run_manifest(parts[1])
        return status, _envelope(parts[1], payload)
    if method == "GET" and len(parts) == 2 and parts[0] == "runs":
        status, payload = run_routes.run_status(parts[1])
        return status, _envelope(parts[1], payload)
    if method == "POST" and parts == ["runs"]:
        requested = str((body or {}).get("run_id", ""))
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        run_id = requested or f"run-{stamp}"
        try:
            from satsa.pipeline.orchestrator import run_pipeline

            run_pipeline(run_id=run_id, force=True)
        except Exception:
            _spawn_run(run_id)
        return 200, _envelope(run_id, {"run_id": run_id, "status": "complete"})
    if method == "POST" and parts == ["ingest"]:
        return 405, _envelope(query.get("run_id", ""), {"error": "multipart upload required"})
    if method == "GET" and parts == ["queue"]:
        store, run_id = entity_routes.resolve_store(query)
        if store is None:
            return 404, _envelope("", {"error": "no runs available"})
        status, payload = queue_routes.review_queue(query, store)
        return status, _envelope(run_id, payload)
    if method == "GET" and parts == ["audit", "verify"]:
        status, payload = audit_routes.verify()
        return status, _envelope(query.get("run_id", ""), payload)
    if method == "GET" and parts == ["audit", "entries"]:
        status, payload = audit_routes.entries(query)
        return status, _envelope(query.get("run_id", ""), payload)
    if parts[:1] == ["entities"]:
        store, run_id = entity_routes.resolve_store(query)
        if store is None:
            return 404, _envelope("", {"error": "no runs available"})
        if method == "GET" and len(parts) == 1:
            status, payload = entity_routes.list_entities(query, store)
            return status, _envelope(run_id, payload)
        if method == "GET" and len(parts) == 2:
            status, payload = entity_routes.entity_detail(parts[1], store)
            return status, _envelope(run_id, payload)
        if method == "GET" and len(parts) == 3 and parts[2] == "findings":
            status, payload = entity_routes.entity_findings(parts[1], store)
            return status, _envelope(run_id, payload)
    if parts[:1] == ["findings"] and len(parts) >= 2:
        store, run_id = entity_routes.resolve_store(query)
        if store is None:
            return 404, _envelope("", {"error": "no runs available"})
        if method == "GET" and len(parts) == 2:
            status, payload = finding_routes.finding_detail(parts[1], store)
            return status, _envelope(run_id, payload)
        if method == "GET" and len(parts) == 3 and parts[2] == "evidence":
            status, payload = finding_routes.finding_evidence(parts[1], store)
            return status, _envelope(run_id, payload)
        if method == "GET" and len(parts) == 3 and parts[2] == "counterfactual":
            status, payload = finding_routes.finding_counterfactual(parts[1], store)
            return status, _envelope(run_id, payload)
    return 404, _envelope(query.get("run_id", ""), {"error": f"unknown route: {method} {path}"})


def build_fastapi_app() -> Any:
    """FastAPI adapter over the shared dispatcher (offline /docs, no CDN)."""
    try:
        from fastapi import FastAPI, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError as exc:
        raise RuntimeError("FastAPI is not installed; use the stdlib server") from exc

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        assert API_HOST in ("127.0.0.1", "localhost"), "API must bind loopback only"
        yield

    app = FastAPI(title="SATSA", version=API_VERSION, docs_url="/docs", redoc_url=None, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def _dispatch(request: Request) -> JSONResponse:
        query = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        try:
            body = await request.json() if request.method == "POST" else None
        except Exception:
            body = None
        status, payload = handle_request(
            request.method, request.url.path, query, dict(request.headers), body
        )
        return JSONResponse(status_code=status, content=payload)

    async def _upload(request: Request) -> JSONResponse:
        query = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if not deps.check_token(dict(request.headers), deps.load_api_config()):
            return JSONResponse(
                status_code=401,
                content=_envelope(query.get("run_id", ""), {"error": "missing or invalid X-API-Token"}),
            )
        try:
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                try:
                    form = await request.form()
                except Exception:
                    # python-multipart is optional; fall back to the stdlib
                    # email parser so uploads keep working without it.
                    body = await request.body()
                    status, payload = _ingest_upload(content_type, body, query)
                    return JSONResponse(status_code=status, content=_envelope(query.get("run_id", ""), payload))
                cse_id = query.get("cse_id", "").strip()
                run_id = query.get("run_id", "").strip() or f"upload-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                if not cse_id:
                    return JSONResponse(status_code=400, content=_envelope(run_id, {"error": "cse_id is required"}))

                from satsa.errors import SatsaIngestError
                from satsa.ingest.loaders import materialize_submission

                with tempfile.TemporaryDirectory(prefix="satsa-upload-", ignore_cleanup_errors=True) as temp_dir:
                    written = 0
                    for field_name in ("files", "file", "submission"):
                        for item in form.getlist(field_name):
                            filename = getattr(item, "filename", None)
                            if not filename:
                                continue
                            cleaned_name = Path(filename).name
                            if Path(cleaned_name).suffix.lower() not in UPLOAD_SUFFIXES:
                                continue
                            content = await item.read()
                            target = Path(temp_dir) / cleaned_name
                            target.write_bytes(content)
                            written += 1
                    if not written:
                        return JSONResponse(
                            status_code=400,
                            content=_envelope(
                                run_id,
                                {"error": "no supported files were uploaded; please select an Excel (.xlsx/.xls), CSV, or JSON file"},
                            ),
                        )
                    try:
                        report = materialize_submission(temp_dir, cse_id, run_id)
                    except (SatsaIngestError, OSError, ValueError) as exc:
                        return JSONResponse(status_code=422, content=_envelope(run_id, {"error": str(exc)}))

                _spawn_run(run_id)
                return JSONResponse(
                    status_code=200,
                    content=_envelope(run_id, {"run_id": run_id, "status": "processing", "report": report}),
                )
            else:
                body = await request.body()
                status, payload = _ingest_upload(content_type, body, query)
                return JSONResponse(status_code=status, content=_envelope(query.get("run_id", ""), payload))
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content=_envelope(query.get("run_id", ""), {"error": f"upload error: {exc}"}),
            )

    for route in (
        "/health",
        "/runs",
        "/runs/{run_id}",
        "/runs/{run_id}/manifest",
        "/entities",
        "/entities/{entity_id}",
        "/entities/{entity_id}/findings",
        "/findings/{finding_id}",
        "/findings/{finding_id}/evidence",
        "/findings/{finding_id}/counterfactual",
        "/queue",
        "/audit/verify",
        "/audit/entries",
    ):
        app.add_route(route, _dispatch, methods=["GET"])
    app.add_route("/runs", _dispatch, methods=["POST"])
    app.add_route("/ingest", _upload, methods=["POST"])
    try:
        from fastapi.staticfiles import StaticFiles

        if UI_DIST.is_dir():
            app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")
    except ImportError:
        pass
    return app


class _Handler(BaseHTTPRequestHandler):
    """Stdlib HTTP adapter over the shared dispatcher (offline fallback)."""

    def _serve_ui(self, raw_path: str) -> bool:
        """Serve ui/dist files (SPA fallback to index.html); False to continue."""
        if not UI_DIST.is_dir():
            return False
        path = urlparse(raw_path).path
        if any(path == prefix or path.startswith(prefix + "/") for prefix in _API_PREFIXES):
            return False
        candidate = (UI_DIST / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(UI_DIST.resolve())
        except ValueError:
            return False
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            candidate = UI_DIST / "index.html"
        if not candidate.is_file():
            return False
        data = candidate.read_bytes()
        content_type = _STATIC_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)
        return True

    def _respond(self, method: str) -> None:
        import json as json_mod

        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        body: dict[str, Any] | None = None
        raw_body = b""
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(min(length, MAX_UPLOAD_BYTES + 1))
                if self.path.split("?", 1)[0].strip("/") == "ingest":
                    parsed_query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                    if not deps.check_token(dict(self.headers), deps.load_api_config()):
                        status, payload = 401, {"error": "missing or invalid X-API-Token"}
                    else:
                        status, payload = _ingest_upload(
                            self.headers.get("Content-Type", ""), raw_body, parsed_query
                        )
                    data = json_mod.dumps(_envelope(parsed_query.get("run_id", ""), payload), default=str).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "*")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                body = json_mod.loads(raw_body or b"{}")
            except (ValueError, OSError):
                body = {}
        status, payload = handle_request(method, parsed.path, query, dict(self.headers), body)
        data = json_mod.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET (UI files first, API second)."""
        if self._serve_ui(self.path):
            return
        self._respond("GET")

    def do_POST(self) -> None:
        """Handle POST."""
        self._respond("POST")

    def log_message(self, *args: object) -> None:
        """Silence request logging."""

    server_version = "SATSA/phase6"


def run_server(port: int = 8080, host: str = API_HOST) -> None:
    """Serve forever on loopback only."""
    assert host in ("127.0.0.1", "localhost"), "API must bind loopback only"
    try:
        import uvicorn

        app = build_fastapi_app()
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except Exception:
        try:
            HTTPServer((host, port), _Handler).serve_forever()
        except KeyboardInterrupt:
            print("SATSA API stopped.")


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --port N (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA offline API (Phase 6)")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    import os

    os.chdir(ROOT)
    print(f"serving SATSA API on http://{API_HOST}:{args.port}/docs")
    run_server(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

