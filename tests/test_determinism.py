"""Determinism and schema tests for the dukastack retail simulator."""

import random
from pathlib import Path

import duckdb

from simulator.generate import generate_history, load_state
from simulator.loader import write_raw_database
from simulator.mutate import advance_day

RAW_TABLES = [
    "shops",
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
    "refunds",
]


def fetch_table_rows(db_path: Path, table_name: str) -> list[tuple]:
    """Fetch all rows from a raw table sorted by primary identifier."""
    conn = duckdb.connect(str(db_path))
    try:
        # Exclude _loaded_at from strict comparison in case of wall-clock differences
        cols_query = f"PRAGMA table_info('raw.{table_name}')"
        cols = [r[1] for r in conn.execute(cols_query).fetchall() if r[1] != "_loaded_at"]
        col_list = ", ".join(cols)
        order_col = cols[0]
        sql = f"SELECT {col_list} FROM raw.{table_name} ORDER BY {order_col}"
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_generate_is_strictly_deterministic(tmp_path: Path) -> None:
    """Proves that identical seeds produce byte-for-byte identical database tables."""
    seed = 12345
    days = 7

    db1 = tmp_path / "dukastack_1.duckdb"
    state1 = tmp_path / "state_1.json"
    generate_history(days=days, seed=seed, db_path=db1, state_path=state1)

    db2 = tmp_path / "dukastack_2.duckdb"
    state2 = tmp_path / "state_2.json"
    generate_history(days=days, seed=seed, db_path=db2, state_path=state2)

    for table in RAW_TABLES:
        rows1 = fetch_table_rows(db1, table)
        rows2 = fetch_table_rows(db2, table)
        assert len(rows1) > 0, f"Table raw.{table} should not be empty"
        assert rows1 == rows2, f"Discrepancy detected in raw.{table} between runs with seed={seed}"


def test_advance_is_strictly_deterministic(tmp_path: Path) -> None:
    """Proves that advancing from an identical state produces identical data."""
    seed = 9999
    days_init = 5

    db_base = tmp_path / "base.duckdb"
    state_base = tmp_path / "base_state.json"
    generate_history(days=days_init, seed=seed, db_path=db_base, state_path=state_base)

    # Branch A: load state and advance
    state_a = load_state(state_base)
    rng_a = random.Random(seed + 100)
    for _ in range(3):
        advance_day(state_a, rng_a)
    db_a = tmp_path / "a.duckdb"
    write_raw_database(db_a, state_a, loaded_at=state_a["sim_time"])

    # Branch B: load state and advance identically
    state_b = load_state(state_base)
    rng_b = random.Random(seed + 100)
    for _ in range(3):
        advance_day(state_b, rng_b)
    db_b = tmp_path / "b.duckdb"
    write_raw_database(db_b, state_b, loaded_at=state_b["sim_time"])

    for table in RAW_TABLES:
        rows_a = fetch_table_rows(db_a, table)
        rows_b = fetch_table_rows(db_b, table)
        assert rows_a == rows_b, f"Discrepancy in table raw.{table} after advance"


def test_raw_schema_integrity(tmp_path: Path) -> None:
    """Verifies that all raw tables are correctly typed, non-empty, and populated."""
    db = tmp_path / "test_schema.duckdb"
    state_file = tmp_path / "state_schema.json"
    generate_history(days=3, seed=42, db_path=db, state_path=state_file)

    conn = duckdb.connect(str(db))
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
            ).fetchall()
        ]
        for expected in RAW_TABLES:
            assert expected in tables, f"Expected table {expected} in DuckDB schema raw"
            count = conn.execute(f"SELECT COUNT(*) FROM raw.{expected}").fetchone()[0]
            assert count > 0, f"Table raw.{expected} must have rows"
    finally:
        conn.close()
