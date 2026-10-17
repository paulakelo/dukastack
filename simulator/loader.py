"""DuckDB loader for raw operational retail tables."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.shops (
    shop_id VARCHAR,
    shop_name VARCHAR,
    county VARCHAR,
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id VARCHAR,
    customer_name VARCHAR,
    county VARCHAR,
    loyalty_tier VARCHAR,
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id VARCHAR,
    product_name VARCHAR,
    category VARCHAR,
    unit_price_kes DECIMAL(10, 2),
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id VARCHAR,
    shop_id VARCHAR,
    customer_id VARCHAR,
    order_ts TIMESTAMP,
    order_status VARCHAR,
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_item_id VARCHAR,
    order_id VARCHAR,
    product_id VARCHAR,
    quantity INTEGER,
    discount_kes DECIMAL(10, 2),
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.payments (
    payment_id VARCHAR,
    order_id VARCHAR,
    method VARCHAR,
    amount_kes DECIMAL(10, 2),
    paid_at TIMESTAMP,
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.refunds (
    refund_id VARCHAR,
    order_item_id VARCHAR,
    quantity INTEGER,
    refund_kes DECIMAL(10, 2),
    refunded_at TIMESTAMP,
    updated_at TIMESTAMP,
    _loaded_at TIMESTAMP
);
"""


def get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open or create a DuckDB connection, ensuring the parent directory exists."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize raw schema and tables."""
    conn.execute(SCHEMA_SQL)


def replace_table_data(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    columns: list[str],
    rows: list[list[Any]],
) -> None:
    """Truncate and replace table data."""
    conn.execute(f"DELETE FROM raw.{table_name};")
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO raw.{table_name} ({col_str}) VALUES ({placeholders});"
    conn.executemany(sql, rows)


def append_table_data(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    columns: list[str],
    rows: list[list[Any]],
) -> None:
    """Append rows to a raw table."""
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO raw.{table_name} ({col_str}) VALUES ({placeholders});"
    conn.executemany(sql, rows)


def write_raw_database(
    db_path: str | Path,
    state: dict[str, Any],
    loaded_at: datetime | None = None,
) -> None:
    """
    Write complete simulator state into DuckDB schema raw.
    Replaces operational state (shops, customers, products) and
    appends / replaces transaction state.
    """
    conn = get_connection(db_path)
    try:
        init_schema(conn)
        load_time = loaded_at or datetime.now()

        # 1. Shops (Static)
        shop_rows = [
            [
                s["shop_id"],
                s["shop_name"],
                s["county"],
                s.get("updated_at", load_time),
                load_time,
            ]
            for s in state["shops"]
        ]
        replace_table_data(
            conn,
            "shops",
            ["shop_id", "shop_name", "county", "updated_at", "_loaded_at"],
            shop_rows,
        )

        # 2. Customers (Mutating operational state)
        cust_rows = [
            [
                c["customer_id"],
                c["customer_name"],
                c["county"],
                c["loyalty_tier"],
                c["updated_at"],
                load_time,
            ]
            for c in state["customers"]
        ]
        replace_table_data(
            conn,
            "customers",
            [
                "customer_id",
                "customer_name",
                "county",
                "loyalty_tier",
                "updated_at",
                "_loaded_at",
            ],
            cust_rows,
        )

        # 3. Products (Mutating operational state)
        prod_rows = [
            [
                p["product_id"],
                p["product_name"],
                p["category"],
                Decimal(str(p["unit_price_kes"])),
                p["updated_at"],
                load_time,
            ]
            for p in state["products"]
        ]
        replace_table_data(
            conn,
            "products",
            [
                "product_id",
                "product_name",
                "category",
                "unit_price_kes",
                "updated_at",
                "_loaded_at",
            ],
            prod_rows,
        )

        # 4. Orders
        order_rows = [
            [
                o["order_id"],
                o["shop_id"],
                o["customer_id"],
                o["order_ts"],
                o["order_status"],
                o["updated_at"],
                load_time,
            ]
            for o in state["orders"]
        ]
        replace_table_data(
            conn,
            "orders",
            [
                "order_id",
                "shop_id",
                "customer_id",
                "order_ts",
                "order_status",
                "updated_at",
                "_loaded_at",
            ],
            order_rows,
        )

        # 5. Order items
        item_rows = [
            [
                i["order_item_id"],
                i["order_id"],
                i["product_id"],
                i["quantity"],
                Decimal(str(i["discount_kes"])),
                i["updated_at"],
                load_time,
            ]
            for i in state["order_items"]
        ]
        replace_table_data(
            conn,
            "order_items",
            [
                "order_item_id",
                "order_id",
                "product_id",
                "quantity",
                "discount_kes",
                "updated_at",
                "_loaded_at",
            ],
            item_rows,
        )

        # 6. Payments
        pay_rows = [
            [
                p["payment_id"],
                p["order_id"],
                p["method"],
                Decimal(str(p["amount_kes"])),
                p["paid_at"],
                p["updated_at"],
                load_time,
            ]
            for p in state["payments"]
        ]
        replace_table_data(
            conn,
            "payments",
            [
                "payment_id",
                "order_id",
                "method",
                "amount_kes",
                "paid_at",
                "updated_at",
                "_loaded_at",
            ],
            pay_rows,
        )

        # 7. Refunds
        ref_rows = [
            [
                r["refund_id"],
                r["order_item_id"],
                r["quantity"],
                Decimal(str(r["refund_kes"])),
                r["refunded_at"],
                r["updated_at"],
                load_time,
            ]
            for r in state["refunds"]
        ]
        replace_table_data(
            conn,
            "refunds",
            [
                "refund_id",
                "order_item_id",
                "quantity",
                "refund_kes",
                "refunded_at",
                "updated_at",
                "_loaded_at",
            ],
            ref_rows,
        )
    finally:
        conn.close()
