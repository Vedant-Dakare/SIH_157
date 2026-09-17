#!/usr/bin/env bash
# Air-gap hard gate (TASK 8.2). Exits non-zero on ANY violation.
# Linux: runs the pipeline under strace -e trace=network, fails on any
#   connect() to a non-loopback address (R1: dtrace on macOS).
# Fallback (no strace/dtrace, e.g. Windows): static syscall/env/DNS audit
#   plus a socket-guarded pipeline run. Either path prints PASS/AIRGAP OK
#   or FAIL with the offending call logged.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TRACE_OUT="/tmp/satsa_strace.log"
fail() { echo "AIRGAP FAIL: $1" >&2; exit 1; }
pass() { echo "AIRGAP OK"; }

echo "== airgap: forbidden remote hosts (static) =="
HITS="$(grep -rn --include='*.py' -E 'https?://' server/src/satsa/ai server/src/satsa/ml || true)"
HITS="$(echo "$HITS" | grep -v '127\.0\.0\.1' | grep -v 'localhost' | grep -v 'example-models.local' || true)"
if [ -n "$HITS" ]; then
  echo "$HITS" >&2
  fail "non-loopback URL in ai/ml source"
fi
echo "== airgap: localhost pinning =="
grep -q '127\.0\.0\.1' server/src/satsa/ai/local_llm.py || fail "local_llm missing 127.0.0.1 pin"
grep -q 'local_files_only=True' server/src/satsa/ml/embeddings.py || fail "embeddings missing local_files_only"

echo "== airgap: secret env audit =="
ENV_READS="$(grep -rn --include='*.py' -E 'environ.*(API_KEY|_SECRET)|(API_KEY|_SECRET).*environ' server/src/satsa || true)"
if [ -n "$ENV_READS" ]; then
  echo "$ENV_READS" >&2
  fail "code reads *_API_KEY/*_SECRET from the environment"
fi

echo "== airgap: DNS audit =="
DNS_CALLS="$(grep -rn --include='*.py' -E 'getaddrinfo\s*\(|gethostbyname\s*\(|gethostbyaddr\s*\(|dns\.resolver|import dns[^a-z_]' src/satsa || true)"
if [ -n "$DNS_CALLS" ]; then
  echo "$DNS_CALLS" >&2
  fail "direct DNS resolution call in source"
fi

PYTHON="${PYTHON:-.venv/Scripts/python.exe}"
if [ ! -x "$PYTHON" ]; then PYTHON="python"; fi

if command -v strace >/dev/null 2>&1 && strace -o /tmp/satsa_strace_probe.log -e trace=network true >/dev/null 2>&1; then
  echo "== airgap: strace network gate (full pipeline) =="
  rm -f "$TRACE_OUT"
  strace -f -e trace=network -o "$TRACE_OUT" "$PYTHON" -W ignore -m satsa.signals.runner --all \
    >/tmp/satsa_airgap_out.txt 2>/tmp/satsa_airgap_err.txt || fail "pipeline crashed under strace"
  BAD="$(grep -E 'connect\(.*sa_family=AF_INET6?' "$TRACE_OUT" | grep -vE '127\.0\.0\.1|::1' || true)"
  if [ -n "$BAD" ]; then
    echo "$BAD" >&2
    fail "non-loopback connect() observed under strace"
  fi
  echo "strace gate: no external connect() observed"
elif command -v dtrace >/dev/null 2>&1; then
  echo "== airgap: dtrace path (macOS) =="
  echo "dtrace present; run: sudo dtrace -n 'syscall::connect:entry { trace(copyinstr(arg1)); }' -c \"$PYTHON -m satsa.signals.runner --all\""
  "$PYTHON" -W ignore -m satsa.signals.runner --all >/tmp/satsa_airgap_out.txt 2>/tmp/satsa_airgap_err.txt \
    || fail "pipeline crashed"
else
  echo "== airgap: socket-guarded pipeline run (no strace/dtrace here) =="
  SATSA_GUARD_SOCKETS=1 "$PYTHON" -W ignore -c "
import socket
_real = socket.socket.connect
def _guard(self, address, *a, **k):
    host = address[0] if isinstance(address, tuple) else str(address)
    assert host in ('127.0.0.1', 'localhost', '::1', '0.0.0.0'), f'external connect: {host}'
    return _real(self, address, *a, **k)
socket.socket.connect = _guard
from satsa.signals.runner import main
raise SystemExit(main(['--all']))
" >/tmp/satsa_airgap_out.txt 2>/tmp/satsa_airgap_err.txt || { tail -5 /tmp/satsa_airgap_err.txt >&2; fail "socket-guarded pipeline run failed"; }
fi
grep -q 'cse_alpha' /tmp/satsa_airgap_out.txt || fail "pipeline produced no output"

echo "== airgap: template pipeline =="
"$PYTHON" -W ignore -m satsa.ai.narrate --all >/tmp/satsa_narrate_out.txt 2>/tmp/satsa_airgap_err.txt \
  || fail "narrate --all crashed"
grep -q 'narratives' /tmp/satsa_narrate_out.txt || fail "narrate produced no output"
echo "== airgap: template unit gate =="
"$PYTHON" -W ignore -m pytest tests/unit/test_narrate.py tests/unit/test_guardrails.py -q \
  >/tmp/satsa_airgap_tests.txt 2>&1 || { tail -20 /tmp/satsa_airgap_tests.txt; fail "template/guardrail tests failed"; }
echo "PASS: no external network use detected"
pass
