"""Cryptographic primitives: SHA-256 hashing and HMAC signing."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def sha256_str(data: str) -> str:
    """SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8", errors="replace")).hexdigest()


def sha256_file(path: str | Path) -> str:
    """SHA-256 hex digest of a file's bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(data: dict[str, Any]) -> str:
    """Canonical JSON: sorted keys, compact separators, stringified scalars."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def sha256_dict(data: dict[str, Any]) -> str:
    """SHA-256 hex digest of a dict's canonical JSON form."""
    return sha256_str(canonical_json(data))


def hmac_sign(data: str, key: str) -> str:
    """HMAC-SHA256 hex digest of data under key."""
    return hmac.new(
        key.encode("utf-8", errors="replace"),
        data.encode("utf-8", errors="replace"),
        hashlib.sha256,
    ).hexdigest()


def verify_hmac(data: str, key: str, signature: str) -> bool:
    """Constant-time verification of an HMAC signature."""
    expected = hmac_sign(data, key)
    return hmac.compare_digest(expected, signature)
