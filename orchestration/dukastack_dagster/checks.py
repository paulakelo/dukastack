"""Dagster asset checks for data quality, reconciliation, and freshness.

Validates:
- Row-count parity between raw tables and staging views.
- Freshness on snapshots (snap_customers, snap_products) to detect pipeline lag (Chaos C6).
"""

from pathlib import Path

import duckdb
from dagster import (
    AssetCheckResult,
    AssetCheckSeverity,
    AssetKey,
    asset_check,
)

from simulator.config import DEFAULT_DB_PATH

STAGING_MODELS = [
    ("customers", "stg_customers"),
    ("products", "stg_products"),
    ("shops", "stg_shops"),
    ("orders", "stg_orders"),
    ("order_items", "stg_order_items"),
    ("payments", "stg_payments"),
    ("refunds", "stg_refunds"),
]


def _build_row_count_check(raw_name: str, stg_name: str):
    @asset_check(
        asset=AssetKey(["staging", stg_name]),
        name=f"reconcile_{stg_name}_row_count",
        description=f"Reconciles row counts between raw.{raw_name} and staging.{stg_name}",
    )
    def row_count_check() -> AssetCheckResult:
        db_path = Path(DEFAULT_DB_PATH)
        if not db_path.exists():
            return AssetCheckResult(
                passed=False,
                description=f"DuckDB database {db_path} does not exist.",
            )

        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            raw_cnt = conn.execute(f"SELECT COUNT(*) FROM raw.{raw_name}").fetchone()[0]
            stg_cnt = conn.execute(f"SELECT COUNT(*) FROM main_staging.{stg_name}").fetchone()[0]
            passed = raw_cnt == stg_cnt
            description = (
                f"Row counts match: raw.{raw_name}={raw_cnt}, main_staging.{stg_name}={stg_cnt}"
                if passed
                else (
                    f"Row count mismatch: raw.{raw_name}={raw_cnt} "
                    f"vs main_staging.{stg_name}={stg_cnt}"
                )
            )
            return AssetCheckResult(
                passed=passed,
                description=description,
                metadata={
                    "raw_table": f"raw.{raw_name}",
                    "staging_model": f"main_staging.{stg_name}",
                    "raw_count": raw_cnt,
                    "staging_count": stg_cnt,
                },
            )
        finally:
            conn.close()

    row_count_check.__name__ = f"check_{stg_name}_row_count"
    return row_count_check


staging_row_count_checks = [
    _build_row_count_check(raw_name, stg_name) for raw_name, stg_name in STAGING_MODELS
]


@asset_check(
    asset=AssetKey(["snap_customers"]),
    name="snap_customers_freshness",
    description="Validates snapshot freshness against raw.customers to detect skipped days (C6).",
)
def snap_customers_freshness_check() -> AssetCheckResult:
    """Verifies that snapshot valid_from matches the latest source customer mutations."""
    db_path = Path(DEFAULT_DB_PATH)
    if not db_path.exists():
        return AssetCheckResult(
            passed=False, description=f"DuckDB database {db_path} does not exist."
        )

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        raw_max = conn.execute("SELECT MAX(updated_at) FROM raw.customers").fetchone()[0]
        snap_max = conn.execute(
            "SELECT MAX(dbt_valid_from) FROM snapshots.snap_customers"
        ).fetchone()[0]

        if raw_max is None or snap_max is None:
            return AssetCheckResult(
                passed=True,
                description="Insufficient data in raw.customers or snapshots.snap_customers.",
            )

        lag_seconds = (raw_max - snap_max).total_seconds()
        passed = lag_seconds <= 86400  # Within 24 hours / 1 day

        description = (
            f"snap_customers is fresh (lag: {lag_seconds / 3600:.1f}h)."
            if passed
            else (
                f"Snapshot lag exceeds 24h ({lag_seconds / 3600:.1f}h). "
                "A daily run may have been skipped (Chaos C6)."
            )
        )
        return AssetCheckResult(
            passed=passed,
            severity=AssetCheckSeverity.WARN,
            description=description,
            metadata={
                "raw_max_updated_at": str(raw_max),
                "snap_max_valid_from": str(snap_max),
                "lag_hours": lag_seconds / 3600,
            },
        )
    finally:
        conn.close()


@asset_check(
    asset=AssetKey(["snap_products"]),
    name="snap_products_freshness",
    description="Validates snapshot freshness against raw.products to detect pipeline lag.",
)
def snap_products_freshness_check() -> AssetCheckResult:
    """Verifies that product price snapshot stays in sync with catalog changes."""
    db_path = Path(DEFAULT_DB_PATH)
    if not db_path.exists():
        return AssetCheckResult(
            passed=False, description=f"DuckDB database {db_path} does not exist."
        )

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        raw_max = conn.execute("SELECT MAX(updated_at) FROM raw.products").fetchone()[0]
        snap_max = conn.execute(
            "SELECT MAX(dbt_valid_from) FROM snapshots.snap_products"
        ).fetchone()[0]

        if raw_max is None or snap_max is None:
            return AssetCheckResult(
                passed=True,
                description="Insufficient data in raw.products or snapshots.snap_products.",
            )

        lag_seconds = (raw_max - snap_max).total_seconds()
        passed = lag_seconds <= 86400

        description = (
            f"snap_products is fresh (lag: {lag_seconds / 3600:.1f}h)."
            if passed
            else (
                f"Snapshot lag exceeds 24h ({lag_seconds / 3600:.1f}h). "
                "A daily run may have been skipped."
            )
        )
        return AssetCheckResult(
            passed=passed,
            severity=AssetCheckSeverity.WARN,
            description=description,
            metadata={
                "raw_max_updated_at": str(raw_max),
                "snap_max_valid_from": str(snap_max),
                "lag_hours": lag_seconds / 3600,
            },
        )
    finally:
        conn.close()


all_asset_checks = [
    *staging_row_count_checks,
    snap_customers_freshness_check,
    snap_products_freshness_check,
]
