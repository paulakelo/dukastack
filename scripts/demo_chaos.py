"""Demo chaos injection and recovery script for dukastack.

Injects or removes a known-bad dataset (duplicate sale item) to demonstrate
Dagster asset checks / dbt tests failing and halting downstream mart builds.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "dukastack.duckdb"
CHAOS_FILE = PROJECT_ROOT / "ci" / "chaos_datasets" / "duplicate_sale_item.json"
SENTINEL_TIMESTAMP = "2099-01-01 00:00:00"


def get_conn(retries: int = 5, delay: float = 0.5) -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        print(f"Database {DB_PATH} does not exist. Please run 'make demo' first.")
        sys.exit(1)
    for i in range(retries):
        try:
            return duckdb.connect(str(DB_PATH))
        except duckdb.IOException as e:
            if "Conflicting lock" in str(e) and i < retries - 1:
                time.sleep(delay)
                continue
            raise


def inject_fail():
    """Injects a known-bad duplicate sale item into raw.order_items."""
    if not CHAOS_FILE.exists():
        print(f"Error: Chaos dataset {CHAOS_FILE} not found.")
        sys.exit(1)

    with open(CHAOS_FILE) as f:
        data = json.load(f)

    conn = get_conn()
    try:
        # Ensure idempotency: remove previous sentinel row if present
        conn.execute(
            "DELETE FROM raw.order_items WHERE updated_at = ?",
            [SENTINEL_TIMESTAMP],
        )

        # Inject duplicate order item
        conn.execute(
            """
            INSERT INTO raw.order_items (
                order_item_id, order_id, product_id, quantity, discount_kes, updated_at, _loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
            """,
            [
                data["order_item_id"],
                data["order_id"],
                data["product_id"],
                data["quantity"],
                data["discount_kes"],
                SENTINEL_TIMESTAMP,
            ],
        )
        print(
            f"[DEMO-FAIL] Successfully injected duplicate order item {data['order_item_id']} "
            f"from ci/chaos_datasets/{CHAOS_FILE.name} into raw.order_items."
        )
    finally:
        conn.close()

    print("[DEMO-FAIL] Executing 'dbt build' to demonstrate test failure and blocked marts...")
    cmd = [
        str(PROJECT_ROOT / ".venv" / "bin" / "dbt"),
        "build",
        "--project-dir",
        "dbt",
        "--profiles-dir",
        "dbt",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    print("\n" + "=" * 72)
    print("DEMO FAILURE VERIFICATION:")
    print("  ❌ Expected Data Quality Failure: unique_stg_order_items_order_item_id")
    print("  🛑 Downstream models blocked from materialization:")
    print("     - main_core.fct_order_items (SKIPPED)")
    print("     - main_core.fct_refunds (SKIPPED)")
    print("     - main_marts.mrt_daily_sales (SKIPPED)")
    print("     - main_marts.mrt_product_perf (SKIPPED)")
    print("  🔍 Check in Dagster UI (http://localhost:3000) or dbt docs lineage.")
    print("  👉 Run 'make demo-recover' to remove bad input and restore pipeline.")
    print("=" * 72 + "\n")
    return proc.returncode


def recover_green():
    """Removes the injected duplicate sale item and re-runs dbt build."""
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM raw.order_items WHERE updated_at = ?",
            [SENTINEL_TIMESTAMP],
        )
        print("[DEMO-RECOVER] Removed injected duplicate record(s) from raw.order_items.")
    finally:
        conn.close()

    print("[DEMO-RECOVER] Re-running 'dbt build' to verify warehouse recovery...")
    cmd = [
        str(PROJECT_ROOT / ".venv" / "bin" / "dbt"),
        "build",
        "--project-dir",
        "dbt",
        "--profiles-dir",
        "dbt",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if proc.returncode == 0:
        print("\n" + "=" * 72)
        print("DEMO RECOVERY VERIFICATION:")
        print("  ✅ All staging models, snapshots, and core models built successfully.")
        print("  ✅ All data tests and asset checks PASSED (100% green).")
        print("  ✅ Marts materialization restored:")
        print("     - main_marts.mrt_daily_sales")
        print("     - main_marts.mrt_product_perf")
        print("     - main_marts.mrt_tier_moves")
        print("=" * 72 + "\n")
    return proc.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("fail", "recover"):
        print("Usage: python scripts/demo_chaos.py [fail|recover]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "fail":
        # Exit with 0 so make continues to show the formatted demo banner
        inject_fail()
    elif action == "recover":
        code = recover_green()
        sys.exit(code)
