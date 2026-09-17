#!/usr/bin/env bash
# Build the offline bundle on a CONNECTED machine (TASK 8.1).
#   bash scripts/build_offline_bundle.sh [--include-llm]
# Without --include-llm the GGUF model is excluded (R2: bundle stays small).
set -euo pipefail
INCLUDE_LLM=0
if [ "${1:-}" = "--include-llm" ]; then INCLUDE_LLM=1; fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BUNDLE="sat-sa-offline-bundle.tar.zst"

echo "== 1. downloading wheels =="
mkdir -p packaging/wheels
pip download -d packaging/wheels -r requirements.txt
pip download -d packaging/wheels -r requirements-dev.txt
pip download -d packaging/wheels "sentence-transformers>=2.7" || echo "(embeddings wheels optional)"

echo "== 2. models (hash-verified) =="
mkdir -p models/embeddings models/llm
if [ "$INCLUDE_LLM" = "1" ]; then
  echo "Fetching GGUF + sentence-transformer (see scripts/fetch_models_offline.sh)..."
  bash scripts/fetch_models_offline.sh || true
else
  echo "(skipping GGUF; template/narrative fallbacks ship by default)"
fi
sha256sum models/embeddings/* 2>/dev/null || true
sha256sum models/llm/* 2>/dev/null || true

echo "== 3. packaging bundle =="
tar --zstd -cf "$BUNDLE" \
  packaging/wheels/ models/ src/ configs/ docs/ deliverables/ \
  scripts/install_offline.sh scripts/verify_airgap.sh scripts/seed_demo_data.py \
  requirements.txt requirements-dev.txt pyproject.toml Makefile README.md
sha256sum "$BUNDLE" | tee sat-sa-bundle.sha256
echo "bundle ready: $BUNDLE"
