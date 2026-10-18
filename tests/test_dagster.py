"""Unit tests for Dagster orchestration assets, asset checks, and schedules."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb
from dagster import AssetCheckSeverity

from orchestration.dukastack_dagster.checks import (
    all_asset_checks,
    snap_customers_freshness_check,
)
from orchestration.dukastack_dagster.definitions import defs


def test_dagster_definitions_structure():
    """Validates that Dagster definitions load with all assets, checks, jobs, and schedules."""
    assert defs is not None

    asset_graph = defs.get_asset_graph()
    all_keys = asset_graph.all_asset_keys
    # 7 raw + 7 staging + 2 snapshots + 4 dimensions + 2 facts + 3 marts = 25
    assert len(all_keys) == 25

    # 7 staging row count checks + 2 snapshot freshness checks = 9
    assert len(defs.asset_checks) == 9

    assert "daily_pipeline_job" in [j.name for j in defs.jobs]
    assert len(defs.schedules) >= 1


def test_dagster_asset_checks_pass_on_current_db():
    """Ensures all 9 asset checks pass on a synchronized database."""
    for check in all_asset_checks:
        result = check()
        assert result.passed is True, f"Check {check.check_keys} failed: {result.description}"


def test_dagster_freshness_check_flags_skipped_day(tmp_path: Path, monkeypatch):
    """Verifies that snap_customers_freshness_check warns when a skipped day occurs (Chaos C6)."""
    db_file = tmp_path / "test_lag.duckdb"
    conn = duckdb.connect(str(db_file))

    # Create dummy raw.customers and snapshots.snap_customers with a 48-hour gap
    now = datetime(2026, 9, 15, 8, 0, 0)
    skipped_now = now + timedelta(days=2)  # 48h lag

    conn.execute("CREATE SCHEMA raw")
    conn.execute("CREATE SCHEMA snapshots")
    conn.execute("CREATE TABLE raw.customers (customer_id VARCHAR, updated_at TIMESTAMP)")
    conn.execute(
        "CREATE TABLE snapshots.snap_customers (customer_id VARCHAR, dbt_valid_from TIMESTAMP)"
    )

    conn.execute("INSERT INTO raw.customers VALUES ('CUST-001', ?)", [skipped_now])
    conn.execute("INSERT INTO snapshots.snap_customers VALUES ('CUST-001', ?)", [now])
    conn.close()

    # Monkeypatch DEFAULT_DB_PATH in checks module to point to temporary DB
    monkeypatch.setattr("orchestration.dukastack_dagster.checks.DEFAULT_DB_PATH", db_file)

    result = snap_customers_freshness_check()
    assert result.passed is False
    assert result.severity == AssetCheckSeverity.WARN
    assert "exceeds 24h" in result.description
    assert result.metadata["lag_hours"].value == 48.0
