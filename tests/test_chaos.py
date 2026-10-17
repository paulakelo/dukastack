"""Tests for the dukastack chaos scenario injectors (C1 to C6)."""

from pathlib import Path

import duckdb

from simulator.chaos import (
    inject_c1_retroactive_price_correction,
    inject_c2_late_arriving_refund,
    inject_c3_orphan_order,
    inject_c4_duplicate_customer,
    inject_c5_overpaid_order,
    inject_c6_skipped_day,
)
from simulator.generate import generate_history


def test_chaos_c1_retroactive_price_correction(tmp_path: Path) -> None:
    db = tmp_path / "c1.duckdb"
    generate_history(days=5, seed=42, db_path=db, state_path=tmp_path / "s1.json")

    conn = duckdb.connect(str(db))
    try:
        msg = inject_c1_retroactive_price_correction(conn)
        assert "C1:" in msg
    finally:
        conn.close()


def test_chaos_c2_late_arriving_refund(tmp_path: Path) -> None:
    db = tmp_path / "c2.duckdb"
    generate_history(days=10, seed=42, db_path=db, state_path=tmp_path / "s2.json")

    conn = duckdb.connect(str(db))
    try:
        msg = inject_c2_late_arriving_refund(conn)
        assert "C2:" in msg
        query = "SELECT COUNT(*) FROM raw.refunds WHERE refund_id = 'REF-CHAOS-C2'"
        count = conn.execute(query).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_chaos_c3_orphan_order(tmp_path: Path) -> None:
    db = tmp_path / "c3.duckdb"
    generate_history(days=3, seed=42, db_path=db, state_path=tmp_path / "s3.json")

    conn = duckdb.connect(str(db))
    try:
        msg = inject_c3_orphan_order(conn)
        assert "C3:" in msg
        count = conn.execute(
            "SELECT COUNT(*) FROM raw.orders WHERE customer_id = 'CUST-NONEXISTENT-9999'"
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_chaos_c4_duplicate_customer(tmp_path: Path) -> None:
    db = tmp_path / "c4.duckdb"
    generate_history(days=3, seed=42, db_path=db, state_path=tmp_path / "s4.json")

    conn = duckdb.connect(str(db))
    try:
        msg = inject_c4_duplicate_customer(conn)
        assert "C4:" in msg
        # Assert that at least one customer_id has a count > 1
        dup_count = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT customer_id FROM raw.customers GROUP BY customer_id HAVING count(*) > 1
            )
            """
        ).fetchone()[0]
        assert dup_count >= 1
    finally:
        conn.close()


def test_chaos_c5_overpaid_order(tmp_path: Path) -> None:
    db = tmp_path / "c5.duckdb"
    generate_history(days=3, seed=42, db_path=db, state_path=tmp_path / "s5.json")

    conn = duckdb.connect(str(db))
    try:
        msg = inject_c5_overpaid_order(conn)
        assert "C5:" in msg
        query = "SELECT COUNT(*) FROM raw.payments WHERE payment_id = 'PAY-CHAOS-C5'"
        count = conn.execute(query).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_chaos_c6_skipped_day(tmp_path: Path) -> None:
    db = tmp_path / "c6.duckdb"
    state_file = tmp_path / "s6.json"
    generate_history(days=3, seed=42, db_path=db, state_path=state_file)

    msg = inject_c6_skipped_day(state_path=state_file, db_path=db)
    assert "C6:" in msg
