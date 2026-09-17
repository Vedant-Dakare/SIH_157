#!/usr/bin/env bash
# UI offline verification (TASK UI-5.5). Exits non-zero on ANY violation.
# Builds the UI, then scans dist/ for external URLs and CDN hostnames.
# Also flags runtime-network-capable packages in node_modules.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ui"
fail() { echo "UI AIRGAP FAIL: $1" >&2; exit 1; }

echo "== ui: production build =="
npm run build >/tmp/satsa_ui_build.log 2>&1 || { tail -20 /tmp/satsa_ui_build.log >&2; fail "ui build failed"; }
[ -d dist ] || fail "dist/ missing after build"

echo "== ui: external URL scan (dist/) =="
URLS="$(grep -rEoh 'https?://[^"'"'"' )]+' dist/ || true)"
URLS="$(echo "$URLS" | grep -v '^data:' | grep -v '127\.0\.0\.1' | grep -v 'localhost' | grep -v 'w3\.org' | grep -v 'fb\.me' | grep -v 'reactjs\.org' || true)"
if [ -n "$URLS" ]; then
  echo "$URLS" | sort -u >&2
  fail "external URL in dist/"
fi

echo "== ui: CDN hostname scan =="
CDN="$(grep -riE 'cdnjs|jsdelivr|unpkg|fonts\.googleapis|google-analytics|hotjar|segment\.io|intercom' dist/ || true)"
if [ -n "$CDN" ]; then
  echo "$CDN" | head -5 >&2
  fail "CDN hostname in dist/"
fi

echo "== ui: runtime network offenders (node_modules audit) =="
OFFENDERS=""
for pkg in playwright puppeteer selenium-webdriver cypress nightwatch; do
  if [ -d "node_modules/$pkg" ]; then
    OFFENDERS="$OFFENDERS $pkg"
  fi
done
if node -e "try{require.resolve('playwright')}catch(e){process.exit(1)}" 2>/dev/null; then
  OFFENDERS="$OFFENDERS playwright(resolvable)"
fi
if [ -n "$OFFENDERS" ]; then
  echo "network-capable test packages present:$OFFENDERS" >&2
  fail "browser-automation packages must not ship"
fi

echo "UI AIRGAP OK"
