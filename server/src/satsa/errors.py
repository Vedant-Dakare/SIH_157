"""Custom exception hierarchy for SATSA."""


class SatsaError(Exception):
    """Base exception for all SATSA errors."""


class SatsaConfigError(SatsaError):
    """Bad or insecure configuration."""


class SatsaIngestError(SatsaError):
    """Unrecoverable ingest failure."""


class SatsaQuarantineError(SatsaError):
    """Quarantine write itself fails."""


class SatsaSignalError(SatsaError):
    """Signal computation fails."""


class SatsaAuditError(SatsaError):
    """Manifest or ledger write fails."""


class LLMUnavailable(SatsaError):
    """No LLM backend reachable."""
