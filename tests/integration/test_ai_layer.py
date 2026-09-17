"""Phase 3 AI-layer integration (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

from pathlib import Path


def test_template_pipeline_all_narratives() -> None:
    """LLM disabled: every flagged finding gets a complete template narrative."""
    from satsa.ai.narrate import narrate_entity

    out = narrate_entity("cse_bravo")
    assert out["entity_id"] == "cse_bravo"
    assert len(out["narratives"]) >= 1
    for narrative in out["narratives"].values():
        for field in (
            "rationale",
            "what_we_observed",
            "why_it_matters",
            "peer_context",
            "confidence_statement",
            "suggested_review_focus",
        ):
            assert isinstance(narrative[field], str)
            assert narrative[field].strip()
        assert narrative["generated_by"] in ("template", "template_after_guardrail_rejection")


def test_no_llm_backend_imported_when_disabled() -> None:
    """Disabled runs never import llama_cpp or contact Ollama."""
    import sys

    assert "llama_cpp" not in sys.modules
    from satsa.ai.narrate import narrate_entity

    narrate_entity("cse_alpha")
    assert "llama_cpp" not in sys.modules


def test_airgap_script_passes() -> None:
    """verify_airgap.sh exits 0 after a full template run."""
    import shutil
    import subprocess

    bash = shutil.which("bash") or shutil.which("sh")
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        bash,
    ]
    exe = next((c for c in candidates if c and Path(c).exists()), None)
    assert exe, "no bash interpreter found"
    proc = subprocess.run(
        [exe, "scripts/verify_airgap.sh"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-2000:]
    assert "AIRGAP OK" in proc.stdout
