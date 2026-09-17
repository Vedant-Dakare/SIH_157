"""Phase 5 ledger tests (new file, prior phases untouched)."""

from __future__ import annotations

from pathlib import Path

import duckdb


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    """JSONL + DuckDB paths inside tmp."""
    return tmp_path / "ledger.jsonl", tmp_path / "ledger.duckdb"


def _seeded(jsonl: Path, db: Path, n: int = 3) -> None:
    """Append n FINDING events."""
    from satsa.audit.ledger import append_event

    for i in range(n):
        append_event("demo", "FINDING", {"finding_id": f"f{i}"}, jsonl, db)


def _conn(db: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db))


def test_genesis_prev_hash(tmp_path: Path) -> None:
    """First entry links to 64 zeros."""
    from satsa.audit.ledger import append_event

    jsonl, db = _paths(tmp_path)
    first = append_event("demo", "RUN_START", {}, jsonl, db)
    assert first.seq == 0
    assert first.prev_hash == "0" * 64


def test_tamper_breaks_at_exact_seq(tmp_path: Path) -> None:
    """Editing one payload breaks verification at exactly that seq."""
    from satsa.audit.ledger import verify_chain

    jsonl, db = _paths(tmp_path)
    _seeded(jsonl, db, 3)
    conn = _conn(db)
    conn.execute("UPDATE ledger SET payload_json = '{\"finding_id\":\"evil\"}' WHERE seq = 1")
    out = verify_chain(conn)
    conn.close()
    assert out.valid is False
    assert out.first_broken_seq == 1
    assert out.entry_count == 3


def test_delete_breaks_chain(tmp_path: Path) -> None:
    """Removing an entry breaks verification."""
    from satsa.audit.ledger import verify_chain

    jsonl, db = _paths(tmp_path)
    _seeded(jsonl, db, 3)
    conn = _conn(db)
    conn.execute("DELETE FROM ledger WHERE seq = 1")
    out = verify_chain(conn)
    conn.close()
    assert out.valid is False
    assert out.first_broken_seq is not None


def test_reorder_breaks_chain(tmp_path: Path) -> None:
    """Swapping two seq values breaks verification at the earlier seq."""
    from satsa.audit.ledger import verify_chain

    jsonl, db = _paths(tmp_path)
    _seeded(jsonl, db, 3)
    conn = _conn(db)
    conn.execute("UPDATE ledger SET seq = -1 WHERE seq = 1")
    conn.execute("UPDATE ledger SET seq = 1 WHERE seq = 2")
    conn.execute("UPDATE ledger SET seq = 2 WHERE seq = -1")
    out = verify_chain(conn)
    conn.close()
    assert out.valid is False
    assert out.first_broken_seq == 1


def test_merkle_root_changes_on_tamper(tmp_path: Path) -> None:
    """Altering a stored entry hash changes the Merkle root (and breaks the chain)."""
    from satsa.audit.ledger import verify_chain

    jsonl, db = _paths(tmp_path)
    _seeded(jsonl, db, 3)
    conn = _conn(db)
    before = verify_chain(conn).merkle_root
    assert before
    conn.execute("UPDATE ledger SET entry_hash = '" + "ab" * 32 + "' WHERE seq = 2")
    after = verify_chain(conn)
    conn.close()
    assert after.merkle_root != before
    assert after.valid is False
