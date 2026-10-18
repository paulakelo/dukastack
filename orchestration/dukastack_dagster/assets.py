"""Dagster software-defined assets for dukastack retail warehouse.

Provides:
- raw_simulator_data: advances POS simulator state and writes to DuckDB raw schema.
- dukastack_dbt_assets: maps dbt models, snapshots, and marts into Dagster assets using dagster-dbt.
"""

import os
import random
import shutil
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetOut,
    MaterializeResult,
    multi_asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from simulator.config import DEFAULT_DB_PATH, DEFAULT_SEED, DEFAULT_STATE_PATH
from simulator.generate import generate_history, load_state, save_state
from simulator.loader import write_raw_database
from simulator.mutate import advance_day

DBT_DIR = Path(__file__).joinpath("..", "..", "..", "dbt").resolve()
dbt_project = DbtProject(project_dir=DBT_DIR)
dbt_project.prepare_if_dev()

RAW_TABLE_NAMES = [
    "customers",
    "products",
    "shops",
    "orders",
    "order_items",
    "payments",
    "refunds",
]


def get_dbt_resource() -> DbtCliResource:
    """Instantiate DbtCliResource pointing to the project and venv dbt binary."""
    dbt_exe = shutil.which("dbt") or os.fspath(Path(sys.executable).parent / "dbt")
    return DbtCliResource(
        project_dir=dbt_project,
        profiles_dir=dbt_project.project_dir,
        dbt_executable=dbt_exe,
    )


@multi_asset(
    outs={
        f"raw_{tbl}": AssetOut(
            key=AssetKey(["raw", tbl]),
            description=f"Raw ingested {tbl} table loaded from POS simulator state.",
        )
        for tbl in RAW_TABLE_NAMES
    },
    group_name="raw",
    compute_kind="python",
)
def raw_simulator_data(context: AssetExecutionContext):
    """Advances simulated POS event clock by 1 day (or initializes state if empty)

    and synchronizes records into the DuckDB 'raw' schema.
    """
    state_path = Path(DEFAULT_STATE_PATH)
    db_path = Path(DEFAULT_DB_PATH)

    if not state_path.exists() or not db_path.exists():
        context.log.info(f"State or DB not found. Initializing 30 days of history at {db_path}...")
        state = generate_history(
            days=30,
            seed=DEFAULT_SEED,
            db_path=db_path,
            state_path=state_path,
        )
    else:
        state = load_state(state_path)
        seed = state.get("seed", DEFAULT_SEED) + state.get("day_index", 0) + 1
        rng = random.Random(seed)
        context.log.info(f"Advancing simulation by 1 day from {state['sim_time']}...")
        advance_day(state, rng)
        save_state(state, state_path=state_path)
        write_raw_database(db_path, state)

    context.log.info(
        f"Simulator state updated at {state['sim_time']}. "
        f"Orders: {len(state['orders'])}, Refunds: {len(state['refunds'])}"
    )

    for tbl in RAW_TABLE_NAMES:
        row_count = len(state.get(tbl, []))
        yield MaterializeResult(
            asset_key=AssetKey(["raw", tbl]),
            metadata={
                "row_count": row_count,
                "sim_time": str(state["sim_time"]),
                "db_path": os.fspath(db_path),
            },
        )


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    select="fqn:dukastack.*",
)
def dukastack_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Materializes dukastack dbt staging views, snapshots, core models, and marts."""
    yield from dbt.cli(["build"], context=context).stream()
