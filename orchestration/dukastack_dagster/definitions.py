"""Dagster Definitions entrypoint for dukastack.

Integrates:
- Software-defined assets (simulator advance + dbt project).
- Asset checks (row count reconciliation + snapshot freshness).
- Schedules and jobs.
- DbtCliResource.
"""

from dagster import Definitions

from orchestration.dukastack_dagster.assets import (
    dukastack_dbt_assets,
    get_dbt_resource,
    raw_simulator_data,
)
from orchestration.dukastack_dagster.checks import all_asset_checks
from orchestration.dukastack_dagster.schedules import (
    daily_pipeline_job,
    daily_pipeline_schedule,
)

defs = Definitions(
    assets=[raw_simulator_data, dukastack_dbt_assets],
    asset_checks=all_asset_checks,
    jobs=[daily_pipeline_job],
    schedules=[daily_pipeline_schedule],
    resources={
        "dbt": get_dbt_resource(),
    },
)
