"""Integration: scaffold plus seed-demo must run with LLM disabled and air-gapped."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import yaml


def test_no_llm_pipeline(tmp_path: Path, monkeypatch) -> None:
    """seed-demo completes without importing ai modules or opening remote sockets."""
    with open("configs/llm.yaml", encoding="utf-8") as handle:
        llm_cfg = yaml.safe_load(handle)
    assert llm_cfg.get("enabled") is False

    opened: list[tuple] = []
    real_connect = socket.socket.connect

    def guarded_connect(self, address, *args, **kwargs):
        """Record connects and block non-loopback destinations."""
        opened.append(address)
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError(f"non-loopback socket blocked: {address}")
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    for module in [m for m in list(sys.modules) if m.startswith("satsa.ai")]:
        del sys.modules[module]

    from satsa.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["scaffold"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["seed-demo"])
    assert result.exit_code == 0

    assert not any(m.startswith("satsa.ai") for m in sys.modules)
    assert all(
        (address[0] if isinstance(address, tuple) else str(address))
        in ("127.0.0.1", "localhost", "::1")
        for address in opened
    )
