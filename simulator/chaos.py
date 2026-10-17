"""Chaos scenario injection engine for dukastack data quality testing (C1 to C6)."""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

from simulator.config import DEFAULT_DB_PATH, DEFAULT_STATE_PATH
from simulator.generate import load_state, save_state
from simulator.loader import get_connection, write_raw_database
from simulator.mutate import advance_day


def inject_c1_retroactive_price_correction(conn: duckdb.DuckDBPyConnection) -> str:
    """
    C1: Retroactive price correction.
    Changes a product's price in raw.products but back-dates updated_at to 20 days ago
    (bypassing timestamp-based snapshot detection).
    """
    row = conn.execute(
        "SELECT product_id, unit_price_kes, updated_at "
        "FROM raw.products ORDER BY product_id LIMIT 1"
    ).fetchone()
    if not row:
        raise ValueError("raw.products is empty.")

    product_id, current_price, updated_at = row
    new_price = current_price + Decimal("50.00")
    backdated_ts = updated_at - timedelta(days=20)

    conn.execute(
        """
        UPDATE raw.products
        SET unit_price_kes = ?, updated_at = ?, _loaded_at = current_timestamp
        WHERE product_id = ?
        """,
        [new_price, backdated_ts, product_id],
    )
    return (
        f"C1: Modified {product_id} price to {new_price} with back-dated updated_at {backdated_ts}"
    )


def inject_c2_late_arriving_refund(conn: duckdb.DuckDBPyConnection) -> str:
    """
    C2: Late-arriving refund.
    Writes a refund today for an order placed 5 days ago.
    """
    row = conn.execute(
        """
        SELECT oi.order_item_id, oi.quantity, o.order_ts
        FROM raw.order_items oi
        JOIN raw.orders o USING (order_id)
        LEFT JOIN raw.refunds r USING (order_item_id)
        WHERE r.refund_id IS NULL
        ORDER BY o.order_ts ASC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        raise ValueError("No eligible order items found for C2 late refund.")

    order_item_id, qty, order_ts = row
    refund_id = "REF-CHAOS-C2"
    now_ts = datetime.now()

    conn.execute(
        """
        INSERT INTO raw.refunds (
            refund_id, order_item_id, quantity, refund_kes, refunded_at, updated_at, _loaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
        """,
        [refund_id, order_item_id, 1, Decimal("150.00"), now_ts, now_ts],
    )
    return (
        f"C2: Injected late refund {refund_id} against order item {order_item_id} "
        f"placed at {order_ts}"
    )


def inject_c3_orphan_order(conn: duckdb.DuckDBPyConnection) -> str:
    """
    C3: Orphan order.
    Creates an order whose customer_id does not exist in raw.customers.
    """
    orphan_customer_id = "CUST-NONEXISTENT-9999"
    order_id = "ORD-CHAOS-C3"
    item_id = "ITM-CHAOS-C3"
    pay_id = "PAY-CHAOS-C3"
    now_ts = datetime.now()

    shop_id = conn.execute("SELECT shop_id FROM raw.shops LIMIT 1").fetchone()[0]
    prod_row = conn.execute(
        "SELECT product_id, unit_price_kes FROM raw.products LIMIT 1"
    ).fetchone()
    prod_id, price = prod_row

    conn.execute(
        """
        INSERT INTO raw.orders (
            order_id, shop_id, customer_id, order_ts, order_status, updated_at, _loaded_at
        ) VALUES (?, ?, ?, ?, 'completed', ?, current_timestamp)
        """,
        [order_id, shop_id, orphan_customer_id, now_ts, now_ts],
    )

    conn.execute(
        """
        INSERT INTO raw.order_items (
            order_item_id, order_id, product_id, quantity, discount_kes, updated_at, _loaded_at
        ) VALUES (?, ?, ?, 1, 0.00, ?, current_timestamp)
        """,
        [item_id, order_id, prod_id, now_ts],
    )

    conn.execute(
        """
        INSERT INTO raw.payments (
            payment_id, order_id, method, amount_kes, paid_at, updated_at, _loaded_at
        ) VALUES (?, ?, 'mpesa', ?, ?, ?, current_timestamp)
        """,
        [pay_id, order_id, price, now_ts, now_ts],
    )

    return (
        f"C3: Created orphan order {order_id} referencing nonexistent customer {orphan_customer_id}"
    )


def inject_c4_duplicate_customer(conn: duckdb.DuckDBPyConnection) -> str:
    """
    C4: Duplicate customer row.
    Inserts a duplicate row with the exact same customer_id and updated_at into raw.customers.
    """
    cust = conn.execute(
        "SELECT customer_id, customer_name, county, loyalty_tier, updated_at "
        "FROM raw.customers LIMIT 1"
    ).fetchone()
    if not cust:
        raise ValueError("raw.customers is empty.")

    cust_id, name, county, tier, updated_at = cust
    conn.execute(
        """
        INSERT INTO raw.customers (
            customer_id, customer_name, county, loyalty_tier, updated_at, _loaded_at
        ) VALUES (?, ?, ?, ?, ?, current_timestamp)
        """,
        [cust_id, name, county, tier, updated_at],
    )
    return f"C4: Injected duplicate row for customer {cust_id}"


def inject_c5_overpaid_order(conn: duckdb.DuckDBPyConnection) -> str:
    """
    C5: Overpaid order.
    Inserts an extra payment into raw.payments causing payments total to exceed order items sum.
    """
    row = conn.execute(
        "SELECT order_id FROM raw.orders WHERE order_status = 'completed' LIMIT 1"
    ).fetchone()
    if not row:
        raise ValueError("No completed order found for C5.")
    order_id = row[0]
    pay_id = "PAY-CHAOS-C5"
    now_ts = datetime.now()

    conn.execute(
        """
        INSERT INTO raw.payments (
            payment_id, order_id, method, amount_kes, paid_at, updated_at, _loaded_at
        ) VALUES (?, ?, 'mpesa', 99999.00, ?, ?, current_timestamp)
        """,
        [pay_id, order_id, now_ts, now_ts],
    )
    return f"C5: Injected overpayment {pay_id} of 99,999 KES on order {order_id}"


def inject_c6_skipped_day(
    state_path: str | Path = DEFAULT_STATE_PATH,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> str:
    """
    C6: Skipped day.
    Advances 2 simulated days consecutively without snapshotting,
    specifically forcing the same customer to change tier on both days.
    """
    state = load_state(state_path)
    rng = random.Random(state.get("seed", 42) + 999)

    target_customer = state["customers"][0]
    cust_id = target_customer["customer_id"]

    # Day 1 advance
    advance_day(state, rng)
    day1_time = state["sim_time"]
    target_customer["loyalty_tier"] = "silver"
    target_customer["updated_at"] = day1_time

    # Day 2 advance immediately
    advance_day(state, rng)
    day2_time = state["sim_time"]
    target_customer["loyalty_tier"] = "gold"
    target_customer["updated_at"] = day2_time

    save_state(state, state_path=state_path)
    write_raw_database(db_path, state, loaded_at=state["sim_time"])

    return (
        f"C6: Advanced 2 days consecutively without snapshot. "
        f"Customer {cust_id} changed tier on both days."
    )


SCENARIO_MAP = {
    "C1": inject_c1_retroactive_price_correction,
    "C2": inject_c2_late_arriving_refund,
    "C3": inject_c3_orphan_order,
    "C4": inject_c4_duplicate_customer,
    "C5": inject_c5_overpaid_order,
}


def run_chaos(
    scenario: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> list[str]:
    """Inject one or all chaos scenarios."""
    results = []
    scenarios_to_run = [scenario.upper()] if scenario else ["C1", "C2", "C3", "C4", "C5", "C6"]

    conn = get_connection(db_path)
    try:
        for s in scenarios_to_run:
            if s in SCENARIO_MAP:
                msg = SCENARIO_MAP[s](conn)
                results.append(msg)
            elif s == "C6":
                msg = inject_c6_skipped_day(state_path=state_path, db_path=db_path)
                results.append(msg)
            else:
                raise ValueError(f"Unknown scenario: {s}. Choose from C1..C6.")
    finally:
        conn.close()

    return results
