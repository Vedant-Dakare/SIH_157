#!/usr/bin/env bash
# Fetch model artefacts on a CONNECTED machine, then transfer models/ offline.
# Documents exact model name and hash (R1). Never run on the air-gapped host.
set -euo pipefail
EMB_MODEL="sentence-transformers/all-MiniLM-L6-v2"
EMB_REV="default"
LLM_MODEL="satsa-llm-Q4_K_M.gguf"
LLM_URL="https://example-models.local/satsa/${LLM_MODEL}"
LLM_SHA256="REPLACE_WITH_PUBLISHED_SHA256_BEFORE_USE"
mkdir -p models/embeddings models/llm models/artifacts
echo "Embeddings: ${EMB_MODEL} (22M params, CPU-friendly, revision ${EMB_REV})"
echo "If sentence-transformers is available, pre-download with:"
echo "  python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMB_MODEL}').save('models/embeddings')\""
echo "LLM GGUF: ${LLM_MODEL}"
echo "  source: ${LLM_URL}"
echo "  expected sha256: ${LLM_SHA256}"
if command -v sha256sum >/dev/null 2>&1 && [ -f "models/llm/${LLM_MODEL}" ]; then
  sha256sum "models/llm/${LLM_MODEL}"
fi
echo "Transfer the models/ directory to the air-gapped machine, then run:"
echo "  python -m satsa.ai.narrate --entity cse_bravo"
echo "  bash scripts/verify_airgap.sh"
