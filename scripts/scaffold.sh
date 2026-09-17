#!/usr/bin/env bash
# SATSA project scaffold — idempotent folder tree creation.
# Re-running must not fail or duplicate entries.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Complete folder tree (Master Section F).
DIRS=(
  "configs/mappings"
  "data/synthetic"
  "data/quarantine"
  "data/raw"
  "data/processed"
  "models/embeddings"
  "server/src/satsa/canonical"
  "server/src/satsa/ingest"
  "server/src/satsa/signals"
  "server/src/satsa/ml"
  "server/src/satsa/ai"
  "server/src/satsa/synthetic"
  "server/src/satsa/reporting"
  "scripts"
  "tests/unit"
  "tests/property"
  "tests/integration"
  "docs"
)

# Python packages requiring __init__.py.
PACKAGES=(
  "server/src/satsa"
  "src/satsa/canonical"
  "src/satsa/ingest"
  "src/satsa/signals"
  "src/satsa/ml"
  "src/satsa/ai"
  "src/satsa/synthetic"
  "src/satsa/reporting"
  "tests"
  "tests/unit"
  "tests/property"
  "tests/integration"
)

# Empty data/ and models/ directories requiring .gitkeep.
GITKEEP_DIRS=(
  "data/synthetic"
  "data/quarantine"
  "data/raw"
  "data/processed"
  "models/embeddings"
)

for d in "${DIRS[@]}"; do
  mkdir -p "$d"
done

for p in "${PACKAGES[@]}"; do
  # Idempotent: only create when missing; never truncate existing content.
  if [ ! -f "$p/__init__.py" ]; then
    touch "$p/__init__.py"
  fi
done

for g in "${GITKEEP_DIRS[@]}"; do
  if [ ! -f "$g/.gitkeep" ]; then
    touch "$g/.gitkeep"
  fi
done

echo "scaffold complete: $ROOT_DIR"
